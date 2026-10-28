from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1.router import api_v1_router
from backend.app.config import get_settings
from backend.app.core.errors import AppException
from backend.app.core.logging import configure_logging
from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.engine.scheduler import MonitoringScheduler

settings = get_settings()
scheduler: MonitoringScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables created if SQLite dev mode
    configure_logging(level="DEBUG" if settings.DEBUG else "INFO")
    Base.metadata.create_all(bind=engine)

    global scheduler
    if settings.ENVIRONMENT != "test":
        scheduler = MonitoringScheduler(session_factory=SessionLocal)
        scheduler.start()

    yield

    # Shutdown
    if scheduler:
        await scheduler.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Production-grade API observability, reliability, and automated evaluation platform.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handler for application errors
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.get("/", tags=["Root"])
    def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "docs_url": "/docs",
        }

    @app.get("/health", tags=["Root"])
    def health():
        return {
            "status": "ok",
            "version": settings.VERSION,
            "service": "SignalGuard",
        }

    app.include_router(api_v1_router)
    return app


app = create_app()
