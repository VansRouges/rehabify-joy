from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.patients import router as patients_router
from app.config import get_settings
from app.db.database import init_db
from app.services.session import close_redis

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.sync_db_on_startup:
        await init_db()
    yield
    await close_redis()


app = FastAPI(
    title="Joy API",
    description="Rehabify Joy AI — backend service",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(patients_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
