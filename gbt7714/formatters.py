from __future__ import annotations
from typing import List
from .models import BaseEntry, JournalArticle, Book, WebResource, Author, ConferencePaper
from datetime import date

MAX_AUTHORS = 3

def format_authors(authors: List[Author], language: str) -> str:
    if not authors:
        return "[无作者]"
    formatted = [a.format_name() for a in authors]
    if len(authors) > MAX_AUTHORS:
        main = ", ".join(formatted[:MAX_AUTHORS])
        # 判定是否全部为中文（无 ASCII 字母）
        has_latin = any(any('A' <= c.upper() <= 'Z' for c in name) for name in formatted[:MAX_AUTHORS])
        suffix = 'et al.' if has_latin else '等'
        return f"{main}, {suffix}"
    return ", ".join(formatted)


def sanitize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    doi = doi.strip()
    if doi.lower().startswith('https://doi.org/'):
        doi = doi.split('doi.org/', 1)[1]
    return doi


def format_reference(entry: BaseEntry) -> str:
    if isinstance(entry, JournalArticle):
        return format_journal(entry)
    if isinstance(entry, Book):
        return format_book(entry)
    if isinstance(entry, WebResource):
        return format_web(entry)
    if isinstance(entry, ConferencePaper):
        return format_conference(entry)
    raise TypeError(f"Unsupported entry type: {entry.type}")


def format_journal(a: JournalArticle) -> str:
    """Format journal article per GB/T 7714 simplified pattern:
    Authors. Title[J]. Journal, Year, Volume(Issue): Pages. DOI: xxx
    Spaces after commas/colons ensured; omit elements if missing.
    """
    authors = format_authors(a.authors, a.language)
    year = a.year or 'n.d.'
    # Base: Authors. Title[J]. Journal,
    author_seg = authors if authors.endswith('.') else authors + '.'
    ref = f"{author_seg} {a.title}[J]. {a.journal}, {year}"
    if a.volume and a.issue:
        ref += f", {a.volume}({a.issue})"
    elif a.volume:
        ref += f", {a.volume}"
    elif a.issue:
        ref += f", ({a.issue})"
    if a.pages:
        ref += f": {a.pages}"
    if a.doi:
        doi = sanitize_doi(a.doi)
        if doi:
            ref += f". DOI: {doi}"
    return ref


def format_book(b: Book) -> str:
    authors = format_authors(b.authors, b.language)
    year = b.year or 'n.d.'
    edition = ''
    if b.edition:
        if b.language == 'zh':
            edition = f"{b.edition}版"
        else:
            edition = f"{b.edition} ed."
    place_pub = f"{b.place}: {b.publisher}" if b.place and b.publisher else (b.publisher or b.place or '')
    author_seg = authors if authors.endswith('.') else authors + '.'
    ref = f"{author_seg} {b.title}[M]."
    if edition:
        ref += f" {edition}." if not edition.endswith('.') else f" {edition}"
    if place_pub:
        ref += f" {place_pub}, {year}."
    else:
        ref += f" {year}."
    return ref.strip()


def format_date(d: date | None) -> str:
    if not d:
        return ''
    return d.strftime('%Y-%m-%d')


def format_web(w: WebResource) -> str:
    """Format electronic resource (EB/OL) simplified:
    Authors/Org. Title[EB/OL]. (PublishDate) [AccessDate]. URL.
    If publish date missing, omit parentheses part.
    """
    authors = format_authors(w.authors, w.language)
    pub_date = format_date(w.date_published)
    acc_date = format_date(w.date_accessed)
    author_seg = authors if authors.endswith('.') else authors + '.'
    ref = f"{author_seg} {w.title}[EB/OL]."
    if pub_date:
        ref += f" ({pub_date})"
    if acc_date:
        ref += f" [{acc_date}]"
    ref += f". {w.url}."
    return ref


def format_conference(c: ConferencePaper) -> str:
    authors = format_authors(c.authors, c.language)
    year = c.year or 'n.d.'
    author_seg = authors if authors.endswith('.') else authors + '.'
    ref = f"{author_seg} {c.title}[C] // {c.conference}."
    segs = []
    if c.location:
        segs.append(c.location)
    if c.publisher:
        segs.append(c.publisher)
    if segs:
        ref += f" {'; '.join(segs)}, {year}"
    else:
        ref += f" {year}"
    if c.pages:
        ref += f": {c.pages}"
    if c.doi:
        ref += f". DOI: {c.doi}"
    return ref
