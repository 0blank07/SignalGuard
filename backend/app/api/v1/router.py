from fastapi import APIRouter

from backend.app.api.v1.checks import router as checks_router
from backend.app.api.v1.endpoints import router as endpoints_router
from backend.app.api.v1.incidents import router as incidents_router
from backend.app.api.v1.metrics import router as metrics_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(endpoints_router)
api_v1_router.include_router(checks_router)
api_v1_router.include_router(incidents_router)
api_v1_router.include_router(metrics_router)
