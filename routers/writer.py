"""
AI Writer Router
-----------------
Endpoints:
POST /writer/create  - Analyze competitor URLs and write a new SEO article
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List

from models.schemas import AIWriterRequest, AIWriterResponse
from services.writer_pipeline import run_writer_pipeline
from services.auth import get_current_user, increment_user_tokens

router = APIRouter(prefix="/writer", tags=["ai-writer"])


@router.post("/create", response_model=AIWriterResponse)
async def create_article(
    request: AIWriterRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """
    Analyze 1-5 competitor article URLs and write a new, superior SEO article.

    - **competitor_urls**: List of 1 to 5 URLs to analyze (will be fetched and compared)
    - **topic_prompt**: Describe what you want to write about (concept stays the same, treatment is better)
    - **target_keywords**: Optional list of up to 5 target keywords
    - **content_type**: article | bio | product_page | general (defaults to article)
    - **user_tone_prompt**: Optional tone/style instructions for the writer
    """
    # Validate URL count
    if not request.competitor_urls:
        raise HTTPException(status_code=422, detail="At least one competitor URL is required.")
    if len(request.competitor_urls) > 5:
        raise HTTPException(status_code=422, detail="Maximum 5 competitor URLs allowed per request.")

    # Validate topic prompt
    if not request.topic_prompt or not request.topic_prompt.strip():
        raise HTTPException(status_code=422, detail="topic_prompt cannot be empty.")

    try:
        response = await run_writer_pipeline(request)
        background_tasks.add_task(increment_user_tokens, user["id"], response.token_usage)
        return response
    except Exception as e:
        print(f"[WriterRouter] Error: {e}")
        raise HTTPException(status_code=500, detail=f"AI Writer failed: {str(e)}")
