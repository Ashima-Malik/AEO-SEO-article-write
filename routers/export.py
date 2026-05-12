"""
Export Router
-------------
POST /export/report   — Generate print-ready HTML report from analysis data
POST /export/audit    — Generate print-ready HTML report from audit data

The HTML is designed to be print-ready:
- Frontend calls window.print() or browser print dialog
- Or use jsPDF/html2canvas on the frontend for PDF download
- No LLM calls — zero token cost
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List

from models.schemas import AuditSection
from services.report_generator import generate_analysis_report, generate_audit_report
from services.auth import get_current_user

router = APIRouter(prefix="/export", tags=["export"])


class AnalysisReportRequest(BaseModel):
    title: str
    url: str
    score_before: int
    score_after: int
    rating: str
    top_issues: List[str] = []
    quick_wins: List[str] = []
    optimized_content: str = ""
    changes_made: List[dict] = []
    suggested_title_tag: str = ""
    suggested_meta_description: str = ""
    suggested_url_slug: str = ""


class AuditReportRequest(BaseModel):
    url: str
    overall_score: int
    grade: str
    sections: List[dict]           # serialized AuditSection list
    top_recommendations: List[str]


@router.post("/report", response_class=HTMLResponse)
async def export_analysis_report(
    request: AnalysisReportRequest,
    user: dict = Depends(get_current_user),
):
    """
    Generate a print-ready HTML report from SEO analysis data.

    Pass the fields from any `/analyze/*` response.
    Returns HTML — open in browser and use Ctrl+P / window.print() to save as PDF.
    Zero token cost.
    """
    html = generate_analysis_report(
        title=request.title,
        url=request.url,
        score_before=request.score_before,
        score_after=request.score_after,
        rating=request.rating,
        top_issues=request.top_issues,
        quick_wins=request.quick_wins,
        optimized_content=request.optimized_content,
        changes_made=request.changes_made,
        suggested_title_tag=request.suggested_title_tag,
        suggested_meta_description=request.suggested_meta_description,
        suggested_url_slug=request.suggested_url_slug,
    )
    return HTMLResponse(content=html, media_type="text/html")


@router.post("/audit", response_class=HTMLResponse)
async def export_audit_report(
    request: AuditReportRequest,
    user: dict = Depends(get_current_user),
):
    """
    Generate a print-ready HTML report from a site audit.

    Pass the fields from a `/audit` response.
    Returns HTML — open in browser and use Ctrl+P to save as PDF.
    Zero token cost.
    """
    # Re-hydrate AuditSection objects from raw dicts
    from models.schemas import AuditSection, AuditCheck
    sections = []
    for s in request.sections:
        checks = [
            AuditCheck(
                name=c.get("name", ""),
                passed=c.get("passed", True),
                severity=c.get("severity", "info"),
                value=c.get("value"),
                recommendation=c.get("recommendation"),
            )
            for c in s.get("checks", [])
        ]
        sections.append(AuditSection(
            name=s.get("name", ""),
            score=s.get("score", 0),
            checks=checks,
        ))

    html = generate_audit_report(
        url=request.url,
        overall_score=request.overall_score,
        grade=request.grade,
        sections=sections,
        top_recommendations=request.top_recommendations,
    )
    return HTMLResponse(content=html, media_type="text/html")
