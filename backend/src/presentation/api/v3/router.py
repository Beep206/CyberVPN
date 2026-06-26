from fastapi import APIRouter

from src.presentation.api.v3.growth_code_sets import router as growth_code_sets_router

api_v3_router = APIRouter(prefix="/api/v3")
api_v3_router.include_router(growth_code_sets_router)
