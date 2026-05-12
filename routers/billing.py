"""
Billing Router — disabled (Stripe removed, app is publicly free)
"""
from fastapi import APIRouter

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/status")
async def billing_status():
    return {"plan": "public", "status": "free", "message": "No billing configured."}
