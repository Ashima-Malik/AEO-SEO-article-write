"""
Auth (no-op public version)
-----------------------------
Supabase auth removed — app is publicly accessible.
get_current_user always returns a public user.
All token-tracking background tasks are no-ops (no DB to write to).
"""

from fastapi import Depends, Header
from typing import Optional
from config import get_settings, TIER_LIMITS
from services.token_tracker import check_token_budget, get_budget_summary


PUBLIC_USER = {
    "id": "public",
    "email": "public@rankready.app",
    "tier": "agency",
    "analyses_used": 0,
    "tokens_used_this_month": 0,
    "estimated_cost_usd": 0.0,
}


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    return PUBLIC_USER


async def check_usage_limit(user: dict = Depends(get_current_user)) -> dict:
    return user


async def increment_usage(user_id: str) -> None:
    pass


async def save_token_usage(user_id: str, analysis_id: str, token_usage) -> None:
    pass


async def increment_user_tokens(user_id: str, token_usage) -> None:
    pass


async def save_analysis_to_db(user_id: str, analysis_response, input_type: str) -> str:
    return analysis_response.analysis_id
