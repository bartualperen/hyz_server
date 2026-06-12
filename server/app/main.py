import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .database import init_db
from .middleware import RequestLogMiddleware
from .routers import (
    auth,
    classes,
    dashboard,
    frames,
    media,
    prediction,
    session,
    translation,
)
from .seed import run_seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.media_root_path.mkdir(parents=True, exist_ok=True)
    init_db()
    run_seed()
    yield


app = FastAPI(
    title="TEKNOFEST Local Evaluation Server",
    description="Havacılıkta Yapay Zeka istemcisinin bağlanabileceği yerel değerlendirme sunucusu.",
    version="0.1.0",
    lifespan=lifespan,
)

# İstek/yanıt loglama (saf ASGI middleware)
app.add_middleware(RequestLogMiddleware)

# İstemci protokolü (gerçek TEKNOFEST sözleşmesi)
app.include_router(auth.router)
app.include_router(frames.router)
app.include_router(translation.router)
app.include_router(prediction.router)
app.include_router(classes.router)
app.include_router(session.router)
app.include_router(media.router)

# Yönetim paneli
app.include_router(dashboard.router)
