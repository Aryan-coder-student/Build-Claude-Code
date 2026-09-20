import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import repo
from .config import settings
from .db import init_db, session_scope
from .routers import demo, products, widget
from .worker.pipeline import worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    with session_scope() as session:
        repo.ensure_tenant(session, settings.default_tenant_id, settings.default_tenant_name)
    yield
    worker.shutdown()


app = FastAPI(title="AI Interactive Product Demo Sales Agent", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
app.include_router(products.router)
app.include_router(widget.router)
app.include_router(demo.router)
app.mount("/widget/static", StaticFiles(directory=STATIC / "chat"), name="chat-static")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/widget.js", include_in_schema=False)
def widget_js():
    return FileResponse(STATIC / "widget.js", media_type="application/javascript", headers={"Cache-Control": "no-cache"})


@app.get("/widget/chat", include_in_schema=False)
def widget_chat():
    return FileResponse(STATIC / "chat" / "index.html", headers={"Cache-Control": "no-cache"})
