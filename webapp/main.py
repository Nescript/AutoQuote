import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from gbt7714.parser import parse_reference
from gbt7714.formatters import format_reference

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


class ParseResult(BaseModel):
    raw: str
    success: bool
    type: Optional[str] = None
    gbt: Optional[str] = None
    bibitem: Optional[str] = None
    error: Optional[str] = None


def parse_line(raw: str) -> ParseResult:
    """Parse a single line, return result without retaining entry (API oriented)."""
    raw_strip = raw.strip()
    if not raw_strip:
        return ParseResult(raw=raw, success=False, error="Empty line")
    try:
        entry = parse_reference(raw_strip)
        gbt = format_reference(entry)
        entry_type = entry.__class__.__name__
        return ParseResult(raw=raw_strip, success=True, type=entry_type, gbt=gbt)
    except Exception as e:  # noqa: BLE001
        return ParseResult(raw=raw_strip, success=False, error=str(e))


def parse_line_entry(raw: str) -> Tuple[ParseResult, Optional[object]]:
    """Parse line and also return the entry object for bibitem generation."""
    raw_strip = raw.strip()
    if not raw_strip:
        return ParseResult(raw=raw, success=False, error="空行 (忽略)"), None
    try:
        entry = parse_reference(raw_strip)
        gbt = format_reference(entry)
        entry_type = entry.__class__.__name__
        return ParseResult(raw=raw_strip, success=True, type=entry_type, gbt=gbt), entry
    except Exception as e:  # noqa: BLE001
        return ParseResult(raw=raw_strip, success=False, error=_friendly_error(str(e))), None


def batch_parse(text: str) -> List[ParseResult]:
    lines = [l for l in text.splitlines() if l.strip()]
    return [parse_line(l) for l in lines]


def batch_parse_entry(text: str) -> List[Tuple[ParseResult, Optional[object]]]:
    lines = [l for l in text.splitlines() if l.strip()]
    return [parse_line_entry(l) for l in lines]


# -------- bibitem generation (mirrors GUI logic) --------
def _latex_escape(text: str) -> str:
    repl = {
        '\\': r'\\', '{': r'\{', '}': r'\}', '#': r'\#', '$': r'\$', '%': r'\%', '&': r'\&',
        '_': r'\_', '^': r'\^{}', '~': r'\~{}',
    }
    return ''.join(repl.get(c, c) for c in text)


def _generate_key(entry) -> str:
    year = getattr(entry, 'year', None)
    if getattr(entry, 'authors', None):
        a = entry.authors[0]
        base = (a.last or '') + (a.first or '')
        base = re.sub(r'[^A-Za-z0-9\u4e00-\u9fa5]', '', base) or 'ref'
        if len(entry.authors) > 1:
            if any(re.match(r'^[\u4e00-\u9fa5]+$', (x.last + (x.first or ''))) for x in entry.authors):
                base += '等'
            else:
                base += 'EtAl'
        if year:
            return f"{base}{year}"
        return base
    title = getattr(entry, 'title', '')
    chars = re.findall(r'[A-Za-z0-9\u4e00-\u9fa5]', title)
    return ''.join(chars[:8]) or 'ref'


def build_bibitem(entry, formatted: str) -> str:
    key = _generate_key(entry)
    url = getattr(entry, 'url', None)
    doi = getattr(entry, 'doi', None)
    second = None
    if url:
        second = f"\\url{{{_latex_escape(url)}}}"
    elif doi:
        second = f"DOI: {_latex_escape(doi)}"
    body = _latex_escape(formatted)
    body = re.sub(r'^\s*(\[(\d+)\]|\(?\d+\)?[\.)])\s*', '', body)
    if body.endswith('.'):
        body = body[:-1]
    if second:
        return f"\\bibitem{{{key}}}\n    {body}. \\ \n    {second}"
    return f"\\bibitem{{{key}}}\n    {body}."


# -------- friendly errors --------
_ERROR_MAP = {
    'Empty line': '空行 (忽略)'
}


def _friendly_error(msg: str) -> str:
    for k, v in _ERROR_MAP.items():
        if k in msg:
            return v
    # Generic fallback
    if 'unrecognized' in msg.lower():
        return '未识别的参考文献格式'
    return '解析失败: ' + msg.split('\n')[0][:120]


def create_app() -> FastAPI:
    app = FastAPI(title="AutoQuote GBT7714 Web")

    # Mount static
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):  # noqa: D401
        return templates.TemplateResponse(
            "index.html", {"request": request, "results": None, "input_text": ""}
        )

    @app.post("/parse", response_class=HTMLResponse)
    async def parse_form(request: Request, references: str = Form(...), mode: str = Form('gbt')):
        pairs = batch_parse_entry(references)
        results: List[ParseResult] = []
        for pr, entry in pairs:
            if pr.success and mode == 'bibitem' and entry is not None:
                pr.bibitem = build_bibitem(entry, pr.gbt or '')
            results.append(pr)
        # Stats
        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "results": results,
                "input_text": references,
                "output_mode": mode,
                "success_count": success_count,
                "fail_count": fail_count,
            },
        )

    # JSON APIs
    class BatchRequest(BaseModel):
        lines: List[str]

    @app.post("/api/parse")
    async def api_parse(payload: BatchRequest):
        joined = "\n".join(payload.lines)
        return JSONResponse([r.model_dump() for r in batch_parse(joined)])

    @app.post("/api/parse-text")
    async def api_parse_text(text: str = Form(...)):
        return JSONResponse([r.model_dump() for r in batch_parse(text)])

    return app


app = create_app()


def main():  # pragma: no cover
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("webapp.main:app", host=host, port=port, reload=os.environ.get("RELOAD") == "1")


if __name__ == "__main__":  # pragma: no cover
    main()
