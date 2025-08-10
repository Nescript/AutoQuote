import os
from pathlib import Path
from typing import List, Optional

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
    error: Optional[str] = None


def parse_line(raw: str) -> ParseResult:
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


def batch_parse(text: str) -> List[ParseResult]:
    lines = [l for l in text.splitlines() if l.strip()]
    return [parse_line(l) for l in lines]


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
    async def parse_form(request: Request, references: str = Form(...)):
        results = batch_parse(references)
        return templates.TemplateResponse(
            "index.html", {"request": request, "results": results, "input_text": references}
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
