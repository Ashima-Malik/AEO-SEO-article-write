"""
Audit Router
------------
POST /audit        — Technical + on-page SEO audit for any URL
GET  /audit/report — Return print-ready HTML report for an audit
"""

import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse

from models.schemas import AuditRequest, AuditResponse
from services.site_auditor import (
    fetch_page, build_audit_sections,
    compute_overall_score, score_to_grade, collect_critical_issues,
)
from agents.audit_recommender import run_audit_recommender
from services.token_tracker import aggregate_token_usage
from services.auth import get_current_user, increment_user_tokens

router = APIRouter(prefix="/audit", tags=["site-audit"])


@router.post("", response_model=AuditResponse)
async def audit_site(
    request: AuditRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """
    Run a full technical + on-page SEO audit on any URL.

    Checks 20 signals across 3 sections:
    - **On-Page SEO**: title tag, meta description, H1, heading structure, word count
    - **Technical**: HTTPS, canonical, viewport, schema markup, robots meta, favicon
    - **Content & Links**: images/alt text, internal links, external links, Open Graph

    Returns structured results + AI-generated top 3 priority recommendations (token usage tracked).
    """
    start_time = time.time()
    audit_id = str(uuid.uuid4())

    try:
        soup, _, status_code = await fetch_page(request.url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not fetch URL: {str(e)}")

    if status_code >= 400:
        raise HTTPException(status_code=422, detail=f"URL returned HTTP {status_code}")

    # Pure HTML analysis — no tokens
    sections = build_audit_sections(soup, request.url, request.target_keyword)
    overall_score = compute_overall_score(sections)
    grade = score_to_grade(overall_score)
    critical_issues = collect_critical_issues(sections)

    # One small AI call for top 3 recommendations — tokens tracked
    recommendations, recommender_usage = await run_audit_recommender(
        url=request.url,
        overall_score=overall_score,
        critical_issues=critical_issues,
        sections=sections,
    )
    token_usage = aggregate_token_usage([recommender_usage])

    processing_time = round(time.time() - start_time, 2)
    print(f"[Audit] {request.url} → {overall_score}/100 ({grade}) "
          f"in {processing_time}s — {token_usage.total_tokens} tokens")

    # Increment user's monthly token total in background
    background_tasks.add_task(increment_user_tokens, user["id"], token_usage)

    return AuditResponse(
        audit_id=audit_id,
        url=request.url,
        overall_score=overall_score,
        grade=grade,
        sections=sections,
        critical_issues=critical_issues,
        top_recommendations=recommendations,
        token_usage=token_usage,
        processing_time_seconds=processing_time,
    )
