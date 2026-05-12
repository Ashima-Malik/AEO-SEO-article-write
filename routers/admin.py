"""
Admin Router — disabled (no DB configured)
"""
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/rules")
async def get_rules():
    return {"message": "Admin disabled in public mode."}
