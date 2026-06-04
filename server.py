"""Standalone Deadman deployment entrypoint."""
from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.api import create_app as create_deadman_app

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
STUDIO_STATIC = BASE_DIR / "studio"

app = FastAPI(title="Deadman")
deadman_app = create_deadman_app()

for exception_type, handler in deadman_app.exception_handlers.items():
    app.add_exception_handler(exception_type, handler)
app.include_router(deadman_app.router)


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    if FRONTEND_DIST.exists():
        return '<meta http-equiv="refresh" content="0; url=/demo/?branch3_player=1">'
    return (
        "<h1>Deadman</h1>"
        "<p>Run the frontend dev server or build frontend/dist to enable the demo shell.</p>"
    )


if STUDIO_STATIC.exists():
    @app.get("/studio")
    async def studio_redirect():
        return RedirectResponse(url="/studio/")

    app.mount("/studio", StaticFiles(directory=str(STUDIO_STATIC), html=True), name="deadman-studio")


if FRONTEND_DIST.exists():
    @app.get("/demo/{path:path}")
    async def demo_static(path: str):
        fp = FRONTEND_DIST / path
        if fp.exists() and fp.is_file():
            return FileResponse(str(fp))
        return FileResponse(str(FRONTEND_DIST / "index.html"), media_type="text/html")

    @app.get("/demo")
    async def demo_index():
        return FileResponse(str(FRONTEND_DIST / "index.html"), media_type="text/html")


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host=host, port=port, reload=False)

