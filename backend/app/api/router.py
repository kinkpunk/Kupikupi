from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.health import router as health_router
from app.api.v1.users import router as users_router

api_router = APIRouter()
api_router.include_router(admin_router, tags=["Admin"])
api_router.include_router(auth_router, tags=["Auth"])
api_router.include_router(catalog_router, tags=["Catalog"])
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(users_router, tags=["Users"])
