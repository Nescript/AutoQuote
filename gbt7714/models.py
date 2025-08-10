from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import date

CitationType = Literal[
    "journal", "book", "web", "thesis", "conference", "report"
]

class Author(BaseModel):
    last: str = Field(..., description="姓（或英文姓氏）")
    first: Optional[str] = Field(None, description="名（或英文名首字母）")
    is_organization: bool = Field(False, description="是否为机构作者")

    def _is_latin(self) -> bool:
        return any('A' <= c.upper() <= 'Z' for c in self.last)

    def format_name(self) -> str:
        """Return a name formatted per GB/T 7714 (Chinese reference list context).

        规则简化：
        - 机构名原样返回
        - 中文姓名（检测为含有中文字符且 _is_latin False）：姓与名直接拼接，不加空格
        - 拉丁字母姓名：Surname 首字母大写其余小写；名按空格/连字符切分取首字母，全部大写，无点，之间空格
          例如 first="Bo Liang" -> "Liang B L"
        - 复合姓按空格拆分分别首字母大写后再组合
        """
        if self.is_organization:
            return self.last
        if not self._is_latin():
            # 中文：直接姓+名（若 first 为拼音亦可用户自行控制）
            return f"{self.last}{self.first or ''}" if self.first else self.last
        # 拉丁姓名
        # 处理姓
        surname_parts = [p.capitalize() for p in self.last.replace('-', ' ').split() if p]
        surname = ' '.join(surname_parts)
        if not self.first:
            return surname
        initials = [seg[0].upper() for seg in self.first.replace('-', ' ').split() if seg]
        return f"{surname} {' '.join(initials)}" if initials else surname

class BaseEntry(BaseModel):
    type: CitationType
    title: str
    authors: List[Author] = []
    year: Optional[int] = None
    language: Literal["zh", "en"] = "zh"

    class Config:
        arbitrary_types_allowed = True

class JournalArticle(BaseEntry):
    type: Literal["journal"] = "journal"
    journal: str
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None

class Book(BaseEntry):
    type: Literal["book"] = "book"
    publisher: Optional[str] = None
    place: Optional[str] = None
    edition: Optional[str] = None
    isbn: Optional[str] = None

class WebResource(BaseEntry):
    type: Literal["web"] = "web"
    url: str
    date_published: Optional[date] = None
    date_accessed: Optional[date] = None
    org: Optional[str] = None

class ConferencePaper(BaseEntry):
    type: Literal["conference"] = "conference"
    conference: str
    location: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None

class BookChapter(BaseEntry):
    """Book chapter / section inside an edited book.

    Represented in GB/T as: Authors. Chapter Title[M] // Book Title. Place: Publisher, Year: Pages
    """
    type: Literal["book"] = "book"  # reuse book marker [M]
    book_title: str
    place: Optional[str] = None
    publisher: Optional[str] = None
    pages: Optional[str] = None
