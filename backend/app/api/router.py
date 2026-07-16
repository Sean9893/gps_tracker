from fastapi import APIRouter

from app.api.routes_device import router as device_router
from app.api.routes_geofence import router as geofence_router
from app.api.routes_gps import router as gps_router
from app.api.routes_health import router as health_router

api_router = APIRouter()
api_router.include_router(gps_router, prefix="/api/gps", tags=["gps"])
api_router.include_router(device_router, prefix="/api/device", tags=["device"])
api_router.include_router(geofence_router, prefix="/api/geofence", tags=["geofence"])
api_router.include_router(health_router, prefix="/api/health", tags=["health"])

