"""API v1 router."""
from fastapi import APIRouter

api_router = APIRouter(prefix="/v1")


@api_router.get("/status", tags=["Status"])
async def get_api_status():
    return {"api_version": "v1", "status": "active"}
