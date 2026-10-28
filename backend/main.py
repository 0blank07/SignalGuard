"""SignalGuard entry point for uvicorn and ASGI servers."""
from backend.app.main import app, create_app

__all__ = ["app", "create_app"]
