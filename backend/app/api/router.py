from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.health import router as health_router
from app.api.v1.offers import router as offers_router
from app.api.v1.shopping_requests import router as shopping_requests_router
from app.api.v1.users import router as users_router
from app.api.v1.watchlists import router as watchlists_router

api_router = APIRouter()
api_router.include_router(admin_router, tags=["Admin"])
api_router.include_router(auth_router, tags=["Auth"])
api_router.include_router(catalog_router, tags=["Catalog"])
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(offers_router, tags=["Offers"])
api_router.include_router(shopping_requests_router, tags=["Shopping Requests"])
api_router.include_router(users_router, tags=["Users"])
api_router.include_router(watchlists_router, tags=["Watchlists"])
