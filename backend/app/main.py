import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.reports import router as reports_router
from app.api.route import geocode_router, router as route_router
from app.core.config import settings
from app.core.database import check_health, get_connection
from app.core.http import shutdown_http_client, startup_http_client
from app.services import accident_service

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_http_client()
    get_connection()  # 起動時にDB接続・スキーマ作成・reports.json移行を行う
    accident_service.get_index()  # 起動時に事故データをグリッドインデックスへロード
    logger.info("アプリケーションを起動しました")
    try:
        yield
    finally:
        await shutdown_http_client()
        logger.info("アプリケーションを停止しました")


app = FastAPI(title="通学路危険動線解析システム API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("未処理の例外が発生しました: %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "サーバー内部でエラーが発生しました"})


app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.include_router(reports_router)
app.include_router(geocode_router)
app.include_router(route_router)


@app.get("/health")
def health() -> dict[str, str]:
    if not check_health():
        return JSONResponse(status_code=503, content={"status": "error", "detail": "DB接続に失敗しました"})
    return {"status": "ok"}
