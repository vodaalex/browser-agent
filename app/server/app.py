from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.log import logger, setup_logging
from app.browser.manager import BrowserManager
from app.server.ws import websocket_endpoint

# Application-wide browser instance
browser = BrowserManager()

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    await browser.start()
    yield
    await browser.stop()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def index():
        return FileResponse(str(STATIC_DIR / "index.html"))

    @app.get("/favicon.ico")
    async def favicon():
        return Response(status_code=204)


    app.websocket("/ws")(websocket_endpoint)

    return app


app = create_app()

