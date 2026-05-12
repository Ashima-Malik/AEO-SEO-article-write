"""
Analysis Router
----------------
Endpoints:
POST /analyze/document  - Upload and analyze a .docx file
POST /analyze/url       - Analyze content from a URL
POST /analyze/text      - Analyze pasted text/markdown
GET  /analyze/{id}      - Get a previous analysis by ID
GET  /analyze/history   - Get user's analysis history
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response
from typing import Optional
from datetime import datetime, timezone
import json

from models.schemas import (
    AnalyzeURLRequest, AnalyzeTextRequest,
    InputType, ContentType, SEOAnalysisResponse,
    BulkAnalyzeRequest, BulkAnalyzeResponse,
)
from services.document import extract_from_docx, extract_from_text, extract_from_url
from services.pipeline import run_full_analysis
from services.bulk_pipeline import run_bulk_pipeline
from services.auth import get_current_user, check_usage_limit, increment_usage, save_analysis_to_db, save_token_usage, increment_user_tokens
from services.docx_writer import markdown_to_docx
from config import get_settings

router = APIRouter(prefix="/analyze", tags=["analysis"])

# ── Dev-mode in-memory cache ───────────────────────────────────────────────────
# Replaces Supabase when APP_ENV=development so the full
# POST → redirect → GET flow works without a database.

_dev_analysis_cache: dict = {}   # analysis_id → model_dump(mode="json")
_dev_history: list = []          # slim history rows, newest first


def _dev_cache_result(result: SEOAnalysisResponse, input_type: str) -> None:
    """Store full result + a slim history row in the in-memory dev cache."""
    data = result.model_dump(mode="json")
    _dev_analysis_cache[result.analysis_id] = data
    _dev_history.insert(0, {
        "id": result.analysis_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_type": input_type,
        "content_type": result.content_type.value if hasattr(result.content_type, "value") else str(result.content_type),
        "target_keyword": result.target_keyword,
        "score_before": result.score_before.overall,
        "score_after": result.score_after.overall,
        "status": "completed",
    })


@router.post("/document", response_model=SEOAnalysisResponse)
async def analyze_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_keyword: Optional[str] = Form(None),
    content_type: Optional[str] = Form(None),
    user_tone_prompt: Optional[str] = Form(None),
    user: dict = Depends(check_usage_limit)
):
    """Upload a .docx or .txt file for SEO analysis."""

    # Validate file type
    allowed_types = [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
    ]
    if file.content_type not in allowed_types and not file.filename.endswith((".docx", ".txt", ".md")):
        raise HTTPException(
            status_code=400,
            detail="Only .docx, .txt, and .md files are supported"
        )

    file_bytes = await file.read()

    # Extract content
    if file.filename.endswith(".docx"):
        extracted = extract_from_docx(file_bytes)
    else:
        extracted = extract_from_text(file_bytes.decode("utf-8"), filename=file.filename)

    # Parse content type if provided
    ct = None
    if content_type:
        try:
            ct = ContentType(content_type)
        except ValueError:
            pass

    # Run analysis pipeline
    result = await run_full_analysis(
        extracted_content=extracted,
        input_type=InputType.DOCUMENT,
        target_keyword=target_keyword,
        content_type=ct,
        user_tone_prompt=user_tone_prompt,
        user_tier=user.get("tier", "starter"),
        tokens_used_this_month=user.get("tokens_used_this_month", 0),
    )

    _dev_cache_result(result, "document")
    background_tasks.add_task(increment_usage, user["id"])
    background_tasks.add_task(save_analysis_to_db, user["id"], result, "document")
    background_tasks.add_task(save_token_usage, user["id"], result.analysis_id, result.token_usage)
    return result


@router.post("/url", response_model=SEOAnalysisResponse)
async def analyze_url(
    background_tasks: BackgroundTasks,
    request: AnalyzeURLRequest,
    user: dict = Depends(check_usage_limit)
):
    """Fetch and analyze content from a public URL."""
    try:
        extracted = await extract_from_url(request.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    ct = None
    if request.content_type:
        ct = request.content_type

    result = await run_full_analysis(
        extracted_content=extracted,
        input_type=InputType.URL,
        target_keyword=request.target_keyword,
        target_keywords=request.target_keywords,
        content_type=ct,
        current_url=request.url,
        user_tone_prompt=request.user_tone_prompt,
        user_brief=request.user_brief or "",
        user_tier=user.get("tier", "starter"),
        tokens_used_this_month=user.get("tokens_used_this_month", 0),
    )

    _dev_cache_result(result, "url")
    background_tasks.add_task(increment_usage, user["id"])
    background_tasks.add_task(save_analysis_to_db, user["id"], result, "url")
    background_tasks.add_task(save_token_usage, user["id"], result.analysis_id, result.token_usage)
    return result


@router.post("/text", response_model=SEOAnalysisResponse)
async def analyze_text(
    background_tasks: BackgroundTasks,
    request: AnalyzeTextRequest,
    user: dict = Depends(check_usage_limit)
):
    """Analyze pasted plain text or markdown content."""
    if len(request.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Content too short — please provide at least 50 characters")

    extracted = extract_from_text(request.text, filename=request.filename)

    ct = None
    if request.content_type:
        ct = request.content_type

    result = await run_full_analysis(
        extracted_content=extracted,
        input_type=InputType.TEXT,
        target_keyword=request.target_keyword,
        target_keywords=request.target_keywords,
        content_type=ct,
        user_tone_prompt=request.user_tone_prompt,
        user_brief=request.user_brief or "",
        user_tier=user.get("tier", "starter"),
        tokens_used_this_month=user.get("tokens_used_this_month", 0),
    )

    _dev_cache_result(result, "text")
    background_tasks.add_task(increment_usage, user["id"])
    background_tasks.add_task(save_analysis_to_db, user["id"], result, "text")
    background_tasks.add_task(save_token_usage, user["id"], result.analysis_id, result.token_usage)
    return result


@router.post("/bulk", response_model=BulkAnalyzeResponse)
async def analyze_bulk(
    request: BulkAnalyzeRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """
    Analyze 2-10 URLs in one request. Returns score + top issues for each URL.

    - **urls**: 2-10 URLs to analyze (sequential to respect rate limits)
    - **target_keyword**: optional keyword applied to all URLs
    - **content_type**: optional content type applied to all URLs

    Token usage is tracked per URL and aggregated. Ideal for agency workflows.
    """
    if len(request.urls) < 2:
        raise HTTPException(status_code=422, detail="Provide at least 2 URLs for bulk analysis.")
    if len(request.urls) > 10:
        raise HTTPException(status_code=422, detail="Maximum 10 URLs per bulk request.")

    result = await run_bulk_pipeline(request)
    background_tasks.add_task(increment_user_tokens, user["id"], result.aggregate_token_usage)
    return result


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: str, user: dict = Depends(get_current_user)):
    """Retrieve a previous analysis by ID (in-memory, current session only)."""
    if analysis_id not in _dev_analysis_cache:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _dev_analysis_cache[analysis_id]


@router.get("/history/all")
async def get_analysis_history(
    page: int = 1,
    per_page: int = 20,
    user: dict = Depends(get_current_user)
):
    """Get paginated analysis history (in-memory, current session only)."""
    offset = (page - 1) * per_page
    return {
        "analyses": _dev_history[offset: offset + per_page],
        "page": page,
        "per_page": per_page,
    }


@router.get("/{analysis_id}/download")
async def download_optimized_docx(
    analysis_id: str,
    user: dict = Depends(get_current_user)
):
    """Download the optimized content as a .docx file."""
    if analysis_id not in _dev_analysis_cache:
        raise HTTPException(status_code=404, detail="Analysis not found")
    cached = _dev_analysis_cache[analysis_id]
    optimized_content = cached.get("optimized_content", "")
    keyword = cached.get("target_keyword", "optimized")
    safe_filename = keyword.replace(" ", "_").lower()[:30]
    docx_bytes = markdown_to_docx(optimized_content, filename=safe_filename)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}_seo_optimized.docx"'},
    )