"""GUI for AutoQuote with proper indentation (fixed)."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
import re
from datetime import date
from gbt7714.models import Author, JournalArticle, Book, WebResource, ConferencePaper
from gbt7714.formatters import format_reference
from gbt7714.parser import parse_reference

HELP_AUTHORS = (
    "作者输入说明:\n"
    "- 每行一个作者\n"
    "- 机构作者: 全大写或含 & / 括号自动识别\n"
    "- 英文作者: Surname, Given Names/Initials\n"
    "- 中文作者: 张三 或 张, 三"
)

TYPE_OPTIONS = [
    ("期刊论文", "journal"),
    ("图书", "book"),
    ("网页/在线资源", "web"),
    ("会议论文", "conference"),
]

class AutoQuoteGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("AutoQuote 引用生成器")
        root.geometry("900x620")
        self._build()

    def _build(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True)
        self.tab_parse = ttk.Frame(nb)
        self.tab_manual = ttk.Frame(nb)
        # 解析作为主页面放前面
        nb.add(self.tab_parse, text="解析/标准化")
        nb.add(self.tab_manual, text="字段录入生成")
        self._build_parse_tab()
        self._build_manual_tab()

    # -------- Manual Tab --------
    def _build_manual_tab(self):
        top = ttk.Frame(self.tab_manual)
        top.pack(fill=tk.X, padx=10, pady=6)
        ttk.Label(top, text="引用类型:").pack(side=tk.LEFT)
        self.type_var = tk.StringVar(value=TYPE_OPTIONS[0][1])
        cb = ttk.Combobox(top, state="readonly", values=[t[0] for t in TYPE_OPTIONS], width=14)
        cb.current(0)
        cb.pack(side=tk.LEFT, padx=5)
        cb.bind("<<ComboboxSelected>>", lambda e: self._on_type_changed(cb.current()))
        self.type_combobox = cb
        ttk.Button(top, text="生成→", command=self.generate_reference).pack(side=tk.LEFT, padx=10)
        ttk.Button(top, text="复制结果", command=self.copy_result).pack(side=tk.LEFT)

        paned = tk.PanedWindow(self.tab_manual, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.frm_fields = ttk.Frame(paned)
        paned.add(self.frm_fields)
        right = ttk.Frame(paned)
        paned.add(right)
        self.dynamic_fields: dict[str, tk.Entry] = {}

        # Authors
        authors_box = ttk.LabelFrame(right, text="作者 / 机构 (每行一个)")
        authors_box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.txt_authors = tk.Text(authors_box, height=10)
        self.txt_authors.pack(fill=tk.BOTH, expand=True)
        self.txt_authors.insert("1.0", "张,三\n李,四\nWang, Li\n")
        help_lbl = tk.Label(authors_box, text="?", fg="blue", cursor="question_arrow")
        help_lbl.place(relx=1.0, rely=0.0, anchor="ne")
        help_lbl.bind("<Button-1>", lambda e: messagebox.showinfo("作者帮助", HELP_AUTHORS))

        # Output
        out_box = ttk.LabelFrame(right, text="生成结果")
        out_box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.txt_output = tk.Text(out_box, height=8, wrap=tk.WORD)
        self.txt_output.pack(fill=tk.BOTH, expand=True)

        self._render_fields()

    def _on_type_changed(self, idx: int):
        self.type_var.set(TYPE_OPTIONS[idx][1])
        self._render_fields()

    def _clear_fields(self):
        for c in self.frm_fields.winfo_children():
            c.destroy()
        self.dynamic_fields.clear()

    def _add_field(self, parent, label: str, key: str):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=16, anchor='e').pack(side=tk.LEFT)
        ent = ttk.Entry(row)
        ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.dynamic_fields[key] = ent
        return ent

    def _render_fields(self):
        self._clear_fields()
        t = self.type_var.get()
        box = ttk.LabelFrame(self.frm_fields, text="基础字段")
        box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self._add_field(box, "题名", "title")
        self._add_field(box, "年份", "year")
        if t == 'journal':
            for lab, key in [("期刊名","journal"),("卷","volume"),("期","issue"),("页码","pages"),("DOI","doi")]:
                self._add_field(box, lab, key)
        elif t == 'book':
            for lab, key in [("出版社","publisher"),("出版地","place"),("版次","edition"),("ISBN","isbn")]:
                self._add_field(box, lab, key)
        elif t == 'web':
            for lab, key in [("URL","url"),("发表日期 YYYY-MM-DD","date_published"),("访问日期 YYYY-MM-DD","date_accessed")]:
                self._add_field(box, lab, key)
        elif t == 'conference':
            for lab, key in [("会议名称","conference"),("地点","location"),("出版者","publisher"),("页码","pages"),("DOI","doi")]:
                self._add_field(box, lab, key)

    def _parse_authors_text(self) -> list[Author]:
        raw = self.txt_authors.get("1.0", tk.END).strip()
        if not raw:
            return []
        # 允许用户一行或多行输入；替换常见分隔符为统一逗号
        tmp = raw.replace('\n', '、').replace(';', '、').replace('；', '、')
        # 先按 顿号 / 逗号 / 中文逗号 分裂
        parts = [p.strip() for p in re.split(r'[、，,]+', tmp) if p.strip()]
        authors: list[Author] = []
        buf = []
        for p in parts:
            # 英文格式 "Smith" 或 "Smith J" 可能拆成两个，需要缓冲
            if re.match(r'^[A-Za-z&\-]+$', p) and buf:
                # 可能是名的首字母，附加到前一个
                prev = buf.pop()
                combined = prev + ' ' + p
                buf.append(combined)
            else:
                buf.append(p)
        for token in buf:
            # 机构检测
            if token.isupper() and len(token) > 1:
                authors.append(Author(last=token, is_organization=True))
                continue
            # 英文 "Surname First" 或 "Surname F" -> 拆分
            if re.search(r'[A-Za-z]', token):
                segs = token.split()
                if len(segs) >= 2:
                    last = segs[0]
                    first = ' '.join(segs[1:])
                    authors.append(Author(last=last, first=first))
                    continue
            # 中文姓名：尝试 2 或 3 字，若为2-4字且没有空格，假设第一字为姓
            if re.match(r'^[\u4e00-\u9fa5]{2,4}$', token):
                authors.append(Author(last=token[0], first=token[1:]))
            else:
                authors.append(Author(last=token))
        return authors

    def _parse_date(self, s: str | None):
        if not s: return None
        s = s.strip()
        if not s: return None
        try:
            y,m,d = map(int, s.split('-'))
            return date(y,m,d)
        except Exception:
            return None

    def generate_reference(self):
        try:
            t = self.type_var.get()
            data = {k: v.get().strip() for k,v in self.dynamic_fields.items()}
            authors = self._parse_authors_text()
            year = int(data.get('year')) if data.get('year') else None
            if t == 'journal':
                entry = JournalArticle(title=data.get('title',''), authors=authors, journal=data.get('journal',''), year=year,
                                        volume=data.get('volume') or None, issue=data.get('issue') or None,
                                        pages=data.get('pages') or None, doi=data.get('doi') or None)
            elif t == 'book':
                entry = Book(title=data.get('title',''), authors=authors, publisher=data.get('publisher') or None,
                             place=data.get('place') or None, edition=data.get('edition') or None, year=year,
                             isbn=data.get('isbn') or None)
            elif t == 'web':
                entry = WebResource(title=data.get('title',''), authors=authors, url=data.get('url',''),
                                    date_published=self._parse_date(data.get('date_published')),
                                    date_accessed=self._parse_date(data.get('date_accessed')), year=year)
            elif t == 'conference':
                entry = ConferencePaper(title=data.get('title',''), authors=authors, conference=data.get('conference',''),
                                        location=data.get('location') or None, pages=data.get('pages') or None,
                                        publisher=data.get('publisher') or None, year=year, doi=data.get('doi') or None)
            else:
                raise ValueError('未知类型')
            self._set_output(format_reference(entry))
        except Exception as e:
            messagebox.showerror('生成失败', str(e))

    def _set_output(self, text: str):
        self.txt_output.delete('1.0', tk.END)
        self.txt_output.insert('1.0', text)

    def copy_result(self):
        txt = self.txt_output.get('1.0', tk.END).strip()
        if not txt: return
        self.root.clipboard_clear(); self.root.clipboard_append(txt); self.root.update()
        messagebox.showinfo('已复制', '结果已复制到剪贴板')

    # -------- Parse Tab --------
    def _build_parse_tab(self):
        outer = ttk.Frame(self.tab_parse)
        outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        inp = ttk.LabelFrame(outer, text='原始参考文献字符串 (可含 [J]/[M]/[C]/[EB/OL] / APA / DOI / URL)')
        inp.pack(fill=tk.BOTH, expand=True)
        self.txt_raw = tk.Text(inp, height=7, wrap=tk.WORD)
        self.txt_raw.pack(fill=tk.BOTH, expand=True)
        self.txt_raw.insert('1.0', 'Smith, J., Doe, A. B., & Zhang, W. (2021). A novel method for something. Journal of Interesting Results, 15(2), 123-135. https://doi.org/10.1234/abc.def/5678')

        btns = ttk.Frame(outer); btns.pack(fill=tk.X, pady=5)
        ttk.Button(btns, text='解析并格式化 →', command=self.parse_and_format).pack(side=tk.LEFT)
        ttk.Button(btns, text='清空输入', command=lambda: self.txt_raw.delete('1.0', tk.END)).pack(side=tk.LEFT, padx=5)

        out = ttk.LabelFrame(outer, text='格式化结果 (GB/T)')
        out.pack(fill=tk.BOTH, expand=True)
        self.txt_parse_output = tk.Text(out, height=5, wrap=tk.WORD)
        self.txt_parse_output.pack(fill=tk.BOTH, expand=True)

        key_frame = ttk.Frame(outer)
        key_frame.pack(fill=tk.X, pady=4)
        ttk.Label(key_frame, text='bibitem 键:').pack(side=tk.LEFT)
        self.var_bibkey = tk.StringVar()
        self.ent_bibkey = ttk.Entry(key_frame, textvariable=self.var_bibkey, width=30)
        self.ent_bibkey.pack(side=tk.LEFT, padx=5)
        ttk.Label(key_frame, text='(可手动修改后复制)').pack(side=tk.LEFT)

        bibf = ttk.LabelFrame(outer, text='LaTeX bibitem')
        bibf.pack(fill=tk.BOTH, expand=True, pady=4)
        self.txt_bibitem = tk.Text(bibf, height=6, wrap=tk.WORD)
        self.txt_bibitem.pack(fill=tk.BOTH, expand=True)
        bib_btns = ttk.Frame(outer); bib_btns.pack(fill=tk.X)
        ttk.Button(bib_btns, text='复制 bibitem', command=self.copy_bibitem).pack(side=tk.LEFT)

    def parse_and_format(self):
        raw = self.txt_raw.get('1.0', tk.END).strip()
        if not raw: return
        try:
            entry = parse_reference(raw)
            res = format_reference(entry)
            self.txt_parse_output.delete('1.0', tk.END)
            self.txt_parse_output.insert('1.0', res)
            # 同步生成 bibitem
            bib = self._build_bibitem(entry, res)
            self.txt_bibitem.delete('1.0', tk.END)
            self.txt_bibitem.insert('1.0', bib)
        except Exception as e:
            messagebox.showerror('解析失败', str(e))

    # -------- Bibitem 生成 --------
    def _latex_escape(self, text: str) -> str:
        repl = {
            '\\': r'\\',
            '{': r'\{',
            '}': r'\}',
            '#': r'\#',
            '$': r'\$',
            '%': r'\%',
            '&': r'\&',
            '_': r'\_',
            '^': r'\^{}',
            '~': r'\~{}',
        }
        return ''.join(repl.get(c, c) for c in text)

    def _generate_key(self, entry) -> str:
        # 优先用第一作者+年份
        year = getattr(entry, 'year', None)
        if getattr(entry, 'authors', None):
            a = entry.authors[0]
            base = a.last + (a.first or '')
            base = re.sub(r'[^A-Za-z0-9\u4e00-\u9fa5]', '', base)
            if len(entry.authors) > 1:
                if any(re.match(r'^[\u4e00-\u9fa5]+$', (x.last + (x.first or ''))) for x in entry.authors):
                    base += '等'
                else:
                    base += 'EtAl'
            if year:
                return f"{base}{year}"
            return base
        # 无作者：取题名前 6 个有效中文/字母
        title = getattr(entry, 'title', '')
        chars = re.findall(r'[A-Za-z0-9\u4e00-\u9fa5]', title)
        key = ''.join(chars[:8]) or 'ref'
        return key

    def _build_bibitem(self, entry, formatted: str) -> str:
        key = self._generate_key(entry)
        url = getattr(entry, 'url', None)
        doi = getattr(entry, 'doi', None)
        second = None
        if url:
            second = f"\\url{{{self._latex_escape(url)}}}"
        elif doi:
            second = f"DOI: {self._latex_escape(doi)}"
        body = self._latex_escape(formatted)
        # 去除可能已有的前置序号 [1] / 1. / 1) / (1)
        body = re.sub(r'^\s*(\[(\d+)\]|\(?\d+\)?[\.)])\s*', '', body)
        if body.endswith('.'):
            body = body[:-1]
        if second:
            return f"\\bibitem{{{key}}}\n    {body}. \\\\ \n    {second}"
        return f"\\bibitem{{{key}}}\n    {body}."

    def copy_bibitem(self):
        txt = self.txt_bibitem.get('1.0', tk.END).strip()
        if not txt: return
        self.root.clipboard_clear(); self.root.clipboard_append(txt); self.root.update()
        messagebox.showinfo('已复制', 'bibitem 已复制到剪贴板')


def main():
    root = tk.Tk()
    AutoQuoteGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
