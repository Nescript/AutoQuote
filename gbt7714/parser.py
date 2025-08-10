"""Simple heuristics parser to normalize loosely formatted GB/T 7714 reference strings.

Supported (initial): Journal [J], Book [M], Electronic resource [EB/OL] / [DB/OL].
Assumptions: input already contains a type marker like [J] / [M] / [EB/OL];
missing spaces / Chinese punctuation tolerated. This is a best-effort parser.
"""
from __future__ import annotations
import re
from typing import List
from .models import Author, JournalArticle, Book, WebResource, BaseEntry, ConferencePaper, BookChapter
from datetime import date

_TYPE_PAT = re.compile(r"\[(J|M|EB/OL|DB/OL|C)\]")

def _split_authors(segment: str) -> List[Author]:
    seg = segment.replace('，', ',')
    parts = [p.strip() for p in re.split(r",|;", seg) if p.strip()]
    authors: List[Author] = []
    for p in parts:
        low = p.lower()
        if low in {"et al.", "et al", "等"}:
            continue
        is_org = bool(re.match(r"^[A-Z0-9&\-_. ]+$", p))  # 全大写或含符号视为机构
        authors.append(Author(last=p, is_organization=is_org))
    return authors


def _parse_apa_authors(segment: str) -> List[Author]:
    """Parse APA style author list: 'Surname, A. B., Surname2, C. D., & Surname3, E.'"""
    seg = segment.replace('&', ',')
    # Remove redundant spaces
    # Pattern captures pairs: Surname, Initials.
    pattern = re.compile(r"\s*([^,]+?),\s*([A-Z][A-Za-z\. ]*)(?:,|$)")
    authors: List[Author] = []
    for m in pattern.finditer(seg):
        surname = m.group(1).strip()
        initials_raw = m.group(2).strip()
        # remove dots, split into letters/parts
        initials_clean = re.sub(r"\.", "", initials_raw)
        initials_parts = [p for p in re.split(r"\s+", initials_clean) if p]
        first = " ".join(initials_parts)
        authors.append(Author(last=surname, first=first))
    if not authors:
        # fallback to basic splitter
        return _split_authors(segment)
    return authors

def _strip_braces(value: str) -> str:
    v = value.strip().strip(',').strip()
    if (v.startswith('{') and v.endswith('}')) or (v.startswith('"') and v.endswith('"')):
        v = v[1:-1].strip()
    return v

def _parse_bibtex_authors(author_field: str) -> List[Author]:
    # Split by ' and ' at top-level (BibTeX standard)
    parts = [p.strip() for p in author_field.replace('\n', ' ').split(' and ') if p.strip()]
    authors: List[Author] = []
    for p in parts:
        # Format variants: 'Last, First Middle' or 'First Middle Last'
        if ',' in p:
            last, first = [x.strip() for x in p.split(',', 1)]
            authors.append(Author(last=last, first=first or None))
        else:
            tokens = p.split()
            if len(tokens) == 1:
                # 单一词，可能是机构或中文
                authors.append(Author(last=tokens[0]))
            else:
                # Assume last token is surname
                last = tokens[-1]
                first = ' '.join(tokens[:-1])
                authors.append(Author(last=last, first=first))
    return authors

def _parse_bibtex(raw: str) -> BaseEntry:
    text = raw.strip()
    m = re.match(r'@([A-Za-z]+)\s*\{\s*([^,]+)\s*,(.*)\}\s*$', text, re.DOTALL)
    if not m:
        raise ValueError('BibTeX 格式不正确')
    entry_type = m.group(1).lower()
    body = m.group(3).strip()
    # 解析字段：按逗号分割（忽略嵌套大括号内的逗号）
    fields: dict[str, str] = {}
    buf = ''
    depth = 0
    for ch in body:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth = max(0, depth-1)
        if ch == ',' and depth == 0:
            if '=' in buf:
                k,v = buf.split('=',1)
                fields[k.strip().lower()] = _strip_braces(v)
            buf = ''
        else:
            buf += ch
    if buf.strip() and '=' in buf:
        k,v = buf.split('=',1)
        fields[k.strip().lower()] = _strip_braces(v)

    title = fields.get('title','').strip()
    authors_field = fields.get('author','')
    authors = _parse_bibtex_authors(authors_field) if authors_field else []
    year = None
    try:
        if 'year' in fields:
            year = int(re.findall(r'\d{4}', fields['year'])[0])
    except Exception:
        pass
    if entry_type in {'article'}:
        journal = fields.get('journal') or fields.get('journaltitle') or ''
        volume = fields.get('volume')
        issue = fields.get('number') or fields.get('issue')
        pages = fields.get('pages')
        doi = fields.get('doi')
        return JournalArticle(title=title, authors=authors, journal=journal, year=year, volume=volume, issue=issue, pages=pages, doi=doi)
    if entry_type in {'book'}:
        publisher = fields.get('publisher')
        place = fields.get('address')
        edition = fields.get('edition')
        return Book(title=title, authors=authors, publisher=publisher, place=place, edition=edition, year=year)
    if entry_type in {'inproceedings','conference'}:
        conf = fields.get('booktitle') or fields.get('conference') or ''
        pages = fields.get('pages')
        doi = fields.get('doi')
        location = fields.get('address')
        publisher = fields.get('publisher')
        return ConferencePaper(title=title, authors=authors, conference=conf, pages=pages, doi=doi, location=location, publisher=publisher, year=year)
    if entry_type in {'misc','online','web'}:
        url = fields.get('url','')
        return WebResource(title=title, authors=authors, url=url, year=year)
    # fallback to misc as web
    url = fields.get('url','')
    return WebResource(title=title, authors=authors, url=url, year=year)

def parse_reference(raw: str) -> BaseEntry:
    # BibTeX detection
    if raw.lstrip().startswith('@'):
        return _parse_bibtex(raw)
    text = raw.strip()
    m = _TYPE_PAT.search(text)
    if not m:
        # 先匹配 APA 期刊模式：Authors. (Year). Title. Journal, Volume(Issue), pages. [DOI/URL]
        apa_journal = re.match(r"(?P<authors>.+?)\s*\((?P<year>\d{4})\)\.\s*(?P<title>.+?)\.\s*(?P<journal>[^,]+),\s*(?P<volissue>[^,]+),\s*(?P<pages>[^\.]+)\.\s*(?P<tail>.*)$", text)
        if apa_journal:
            authors = _parse_apa_authors(apa_journal.group('authors'))
            year = int(apa_journal.group('year'))
            title = apa_journal.group('title').strip()
            journal = apa_journal.group('journal').strip()
            volissue = apa_journal.group('volissue').strip()
            pages = apa_journal.group('pages').strip()
            tail = apa_journal.group('tail').strip()
            volume=None; issue=None; doi=None
            vi_match = re.match(r"(?P<vol>\d+)(?:\((?P<iss>[^)]+)\))?", volissue)
            if vi_match:
                volume = vi_match.group('vol')
                issue = vi_match.group('iss')
            doi_match = re.search(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", tail)
            if not doi_match:
                doi_match = re.search(r"https?://doi\.org/(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", tail)
            if doi_match:
                doi = doi_match.group(1)
            return JournalArticle(title=title, authors=authors, journal=journal, year=year, volume=volume, issue=issue, pages=pages, doi=doi)
        # 书籍章节：Authors. (Year[, Month]). Title. In Book Title (pp. X-Y). Place: Publisher.
        apa_chapter = re.match(r"(?P<authors>.+?)\s*\((?P<year>\d{4})(?:,[^)]*)?\)\.\s*(?P<title>.+?)\.\s*In\s+(?P<book>.+?)\s*\(pp\.\s*(?P<pages>[0-9\-–]+)\)\.\s*(?P<place>[^:]+):\s*(?P<publisher>[^.]+)\.?$", text, re.IGNORECASE)
        if apa_chapter:
            authors = _parse_apa_authors(apa_chapter.group('authors'))
            year = int(apa_chapter.group('year'))
            title = apa_chapter.group('title').strip().rstrip('.')
            book_title = apa_chapter.group('book').strip().rstrip('.')
            pages = apa_chapter.group('pages')
            place = apa_chapter.group('place').strip()
            publisher = apa_chapter.group('publisher').strip()
            return BookChapter(title=title, authors=authors, book_title=book_title, pages=pages, place=place, publisher=publisher, year=year)
        # 再匹配 APA 会议模式：Authors. (Year). Title. Conference.
        apa_conf = re.match(r"(?P<authors>.+?)\s*\((?P<year>\d{4})\)\.\s*(?P<title>.+?)\.\s*(?P<conf>[^.]+?)\.?$", text)
        if apa_conf:
            authors = _parse_apa_authors(apa_conf.group('authors'))
            year = int(apa_conf.group('year'))
            title = apa_conf.group('title').strip()
            conf = apa_conf.group('conf').strip()
            return ConferencePaper(title=title, authors=authors, conference=conf, year=year)
        # APA 会议扩展格式：Authors. (Year, Month). Title. In Conference Name (pp. X-Y). Publisher.
        apa_conf_ext = re.match(r"(?P<authors>.+?)\s*\((?P<year>\d{4})(?:,\s*[A-Za-z]+)?\)\.\s*(?P<title>.+?)\.\s*In\s+(?P<conf>.+?)\s*\(pp\.\s*(?P<pages>[0-9\-–]+)\)\.\s*(?P<publisher>[^.]+)\.?$", text, re.IGNORECASE)
        if apa_conf_ext:
            authors = _parse_apa_authors(apa_conf_ext.group('authors'))
            year = int(apa_conf_ext.group('year'))
            title = apa_conf_ext.group('title').strip()
            conf = apa_conf_ext.group('conf').strip().rstrip('.')
            pages = apa_conf_ext.group('pages')
            publisher = apa_conf_ext.group('publisher').strip()
            return ConferencePaper(title=title, authors=authors, conference=conf, pages=pages, publisher=publisher, year=year)
        # 兼容 NIPS/NeurIPS / 末尾 (Year) 形式：Authors. "Title." JournalName Volume (Year).
        legacy_nips = re.match(r"(?P<authors>.+?)\.\s*\"?(?P<title>[^\".]+)\"?\.\s*(?P<journal>.+?)\s+(?P<volume>\d+)\s*\((?P<year>\d{4})\)\.?$", text, re.IGNORECASE)
        if legacy_nips:
            authors_raw = legacy_nips.group('authors').strip()
            # 允许尾部 et al.
            authors_raw = re.sub(r"[,;\s]*(et al\.?|等)$", "", authors_raw, flags=re.IGNORECASE)
            authors = _parse_apa_authors(authors_raw)
            title = legacy_nips.group('title').strip()
            journal = legacy_nips.group('journal').strip().rstrip(',')
            volume = legacy_nips.group('volume')
            year = int(legacy_nips.group('year'))
            return JournalArticle(title=title, authors=authors, journal=journal, year=year, volume=volume)
        raise ValueError("未识别的类型标识（需要包含 [J]/[M]/[EB/OL]/[DB/OL]/[C] 或符合 APA 模式）")
    marker = m.group(1)

    pre_title_match = re.search(r"^(?P<authors>.+?)\.\s*(?P<rest>.+)$", text)
    if not pre_title_match:
        raise ValueError("无法解析作者与题名分界（缺少句点）")
    authors_raw = pre_title_match.group('authors')
    rest = pre_title_match.group('rest')
    authors = _split_authors(authors_raw)

    if marker == 'J':
        title_match = re.search(rf"(?P<title>.+?)\[J\]\.?\s*(?P<tail>.+)", rest)
        if not title_match:
            raise ValueError("期刊条目题名部分解析失败")
        title = title_match.group('title').strip()
        tail = title_match.group('tail')
        journal = None; year=None; volume=None; issue=None; pages=None; doi=None
        doi_match = re.search(r"DOI:\s*([^\s]+)", tail, re.IGNORECASE)
        if doi_match:
            doi = doi_match.group(1).rstrip('.')
        pages_match = re.search(r":\s*([0-9eE\-–]+)\b", tail)
        if pages_match:
            pages = pages_match.group(1)
        main_match = re.search(r"^(?P<journal>[^,\.]+),\s*(?P<year>\d{4})(?:,\s*(?P<volissue>[^:\.]+))?", tail)
        if main_match:
            journal = main_match.group('journal').strip()
            year = int(main_match.group('year'))
            volissue = main_match.group('volissue')
            if volissue:
                vi_match = re.match(r"(?P<vol>[^()]+)\((?P<iss>[^)]+)\)", volissue.strip())
                if vi_match:
                    volume = vi_match.group('vol').strip()
                    issue = vi_match.group('iss').strip()
                else:
                    volume = volissue.strip()
        return JournalArticle(title=title, authors=authors, journal=journal or 'NA', year=year, volume=volume, issue=issue, pages=pages, doi=doi)

    if marker == 'M':
        title_match = re.search(r"(?P<title>.+?)\[M\]\.?\s*(?P<tail>.+)", rest)
        if not title_match:
            raise ValueError("图书题名解析失败")
        title = title_match.group('title').strip()
        tail = title_match.group('tail')
        place=None; publisher=None; year=None
        pub_match = re.search(r"(?P<place>[^:]+):\s*(?P<publisher>[^,\.]+),\s*(?P<year>\d{4})", tail)
        if pub_match:
            place = pub_match.group('place').strip()
            publisher = pub_match.group('publisher').strip()
            year = int(pub_match.group('year'))
        return Book(title=title, authors=authors, place=place, publisher=publisher, year=year)

    if marker in ('EB/OL', 'DB/OL'):
        title_match = re.search(rf"(?P<title>.+?)\[{marker}\]\.?\s*(?P<tail>.+)", rest)
        if not title_match:
            raise ValueError("电子资源题名解析失败")
        title = title_match.group('title').strip()
        tail = title_match.group('tail')
        pub_date=None; acc_date=None; url=None
        pub_m = re.search(r"\((\d{4}-\d{2}-\d{2})\)", tail)
        if pub_m:
            try:
                y,mn,d = map(int, pub_m.group(1).split('-'))
                pub_date = date(y,mn,d)
            except ValueError:
                pass
        acc_m = re.search(r"\[(\d{4}-\d{2}-\d{2})\]", tail)
        if acc_m:
            try:
                y,mn,d = map(int, acc_m.group(1).split('-'))
                acc_date = date(y,mn,d)
            except ValueError:
                pass
        url_m = re.search(r"(https?://[^\s\.]+[^\s]*)", tail)
        if url_m:
            url = url_m.group(1).rstrip('.')
        return WebResource(title=title, authors=authors, url=url or '', date_published=pub_date, date_accessed=acc_date)

    if marker == 'C':
        # Treat as conference paper with explicit [C]
        title_match = re.search(r"(?P<title>.+?)\[C\]\.?\s*//\s*(?P<rest>.+)", rest)
        if not title_match:
            raise ValueError("会议论文题名解析失败 (需要 // 分隔)")
        title = title_match.group('title').strip()
        rest_tail = title_match.group('rest')
        # pattern: Conference Name. Location: Publisher, Year: pages
        conf = rest_tail.split('.')[0].strip()
        loc=None; publisher=None; year=None; pages=None
        pub_sec = rest_tail[len(conf):].lstrip('. ').strip()
        # location: publisher, year: pages
        pub_match = re.search(r"(?P<loc>[^:]+):\s*(?P<publisher>[^,]+),\s*(?P<year>\d{4})(?::\s*(?P<pages>[0-9\-–]+))?", pub_sec)
        if pub_match:
            loc = pub_match.group('loc').strip()
            publisher = pub_match.group('publisher').strip()
            year = int(pub_match.group('year'))
            pages = pub_match.group('pages')
        return ConferencePaper(title=title, authors=authors, conference=conf, location=loc, publisher=publisher, year=year, pages=pages)

    raise ValueError(f"暂不支持的类型: {marker}")

__all__ = ["parse_reference"]
