"""
Compare Router
--------------
Endpoints:
POST /compare  - Analyze your site vs a competitor, return scores + chart-ready data
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from models.schemas import CompareRequest, CompareResponse
from services.compare_pipeline import run_compare_pipeline
from services.auth import get_current_user, increment_user_tokens

router = APIRouter(prefix="/compare", tags=["competitor-comparison"])


@router.post("", response_model=CompareResponse)
async def compare_sites(
    request: CompareRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """
    Compare your website against a competitor's website.

    Runs the full SEO analysis pipeline on both URLs in parallel, then
    produces a structured comparison with:
    - Side-by-side SEO scores (100-point rubric)
    - Visualization data (radar chart, bar chart, gap table) — chart-ready JSON
    - AI-generated insights: your strengths, weaknesses, content gaps, opportunities
    - Prioritized next steps with estimated SEO impact

    - **your_url**: Your website page to analyze
    - **competitor_url**: The competitor page to compare against
    """
    if not request.your_url or not request.competitor_url:
        raise HTTPException(status_code=422, detail="Both your_url and competitor_url are required.")

    if request.your_url == request.competitor_url:
        raise HTTPException(status_code=422, detail="your_url and competitor_url must be different.")

    try:
        result = await run_compare_pipeline(request)
        background_tasks.add_task(increment_user_tokens, user["id"], result.token_usage)
        return result
    except Exception as e:
        print(f"[CompareRouter] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")
