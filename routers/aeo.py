"""
AEO (Answer Engine Optimization) Router
-----------------------------------------
Endpoints for all AEO agents:
  POST /aeo/citation-audit   — check if domain is cited by ChatGPT
  POST /aeo/score            — AEO readiness score (8-criteria rubric)
  POST /aeo/fact-density     — factual density audit
  POST /aeo/entity-map       — named entity extraction + coverage gaps
  POST /aeo/citable-claims   — generate citable claims + FAQ pairs
  POST /aeo/query-plan       — keyword query plan with trend data
  POST /aeo/full-audit       — run all 5 content agents in parallel
"""

import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from services.document import extract_from_url

from agents.aeo_citation_auditor import run_aeo_citation_auditor
from agents.aeo_scorer import run_aeo_scorer
from agents.fact_density_auditor import run_fact_density_auditor
from agents.entity_mapper import run_entity_mapper
from agents.citable_claims_agent import run_citable_claims_agent
from agents.query_planner import run_query_planner

router = APIRouter(prefix="/aeo", tags=["AEO"])


# ─── Request Models ────────────────────────────────────────────────────────────

class CitationAuditRequest(BaseModel):
    url: str
    keywords: list[str]

class AEOScoreRequest(BaseModel):
    content: str
    content_profile: dict | None = None

class FactDensityRequest(BaseModel):
    content: str

class EntityMapRequest(BaseModel):
    content: str
    topic: str

class CitableClaimsRequest(BaseModel):
    content: str
    topic: str
    keywords: list[str] | None = None

class QueryPlanRequest(BaseModel):
    topic: str
    keywords: list[str] | None = None

class FullAEOAuditRequest(BaseModel):
    content: str
    topic: str
    keywords: list[str] | None = None
    url: str | None = None


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/citation-audit")
async def citation_audit(req: CitationAuditRequest):
    """Check if domain appears in ChatGPT citations for given keywords."""
    if not req.keywords:
        raise HTTPException(status_code=400, detail="At least one keyword required.")
    result, usage = await run_aeo_citation_auditor(req.url, req.keywords)
    return {**result, "usage": usage.model_dump()}


@router.post("/score")
async def aeo_score(req: AEOScoreRequest):
    """Score content on 8-criteria AEO readiness rubric."""
    if len(req.content.strip()) < 100:
        raise HTTPException(status_code=400, detail="Content too short (min 100 chars).")
    result, usage = await run_aeo_scorer(req.content, req.content_profile)
    return {**result, "usage": usage.model_dump()}


@router.post("/fact-density")
async def fact_density(req: FactDensityRequest):
    """Audit factual density and detect vague claims."""
    if len(req.content.strip()) < 100:
        raise HTTPException(status_code=400, detail="Content too short (min 100 chars).")
    result, usage = await run_fact_density_auditor(req.content)
    return {**result, "usage": usage.model_dump()}


@router.post("/entity-map")
async def entity_map(req: EntityMapRequest):
    """Extract named entities and identify coverage gaps."""
    if len(req.content.strip()) < 100:
        raise HTTPException(status_code=400, detail="Content too short (min 100 chars).")
    result, usage = await run_entity_mapper(req.content, req.topic)
    return {**result, "usage": usage.model_dump()}


@router.post("/citable-claims")
async def citable_claims(req: CitableClaimsRequest):
    """Generate standalone citable claims and FAQ pairs."""
    if len(req.content.strip()) < 100:
        raise HTTPException(status_code=400, detail="Content too short (min 100 chars).")
    result, usage = await run_citable_claims_agent(req.content, req.topic, req.keywords)
    return {**result, "usage": usage.model_dump()}


@router.post("/query-plan")
async def query_plan(req: QueryPlanRequest):
    """Generate AEO-optimized query plan with trend data."""
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required.")
    result, usage = await run_query_planner(req.topic, req.keywords)
    return {**result, "usage": usage.model_dump()}


@router.post("/full-audit")
async def full_aeo_audit(req: FullAEOAuditRequest):
    """
    Run all 5 content AEO agents in parallel.
    If content is a URL placeholder, fetches the page first.
    """
    content = req.content.strip()

    # If frontend sent a URL placeholder instead of real content, fetch it
    if content.startswith("[URL:") and req.url:
        try:
            extracted = await extract_from_url(req.url)
            content = extracted.full_text
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not fetch URL: {e}")

    if len(content) < 100:
        raise HTTPException(status_code=400, detail="Content too short (min 100 chars).")

    tasks = [
        run_aeo_scorer(content),
        run_fact_density_auditor(content),
        run_entity_mapper(content, req.topic),
        run_citable_claims_agent(content, req.topic, req.keywords),
        run_query_planner(req.topic, req.keywords),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    def _safe(r, default=None):
        if isinstance(r, Exception):
            return default or {}, None
        return r

    aeo_score_res,    aeo_usage     = _safe(results[0], ({}, None))
    fact_density_res, fact_usage    = _safe(results[1], ({}, None))
    entity_map_res,   entity_usage  = _safe(results[2], ({}, None))
    claims_res,       claims_usage  = _safe(results[3], ({}, None))
    query_plan_res,   query_usage   = _safe(results[4], ({}, None))

    citation_res  = None
    citation_usage = None
    if req.url and req.keywords:
        try:
            citation_res, citation_usage = await run_aeo_citation_auditor(req.url, req.keywords)
        except Exception as e:
            print(f"[FullAEOAudit] Citation audit failed: {e}")

    usages = [u for u in [aeo_usage, fact_usage, entity_usage, claims_usage, query_usage, citation_usage] if u]
    total_cost = sum(u.cost_usd for u in usages)
    total_in   = sum(u.input_tokens for u in usages)
    total_out  = sum(u.output_tokens for u in usages)

    return {
        "topic":            req.topic,
        "aeo_score":        aeo_score_res,
        "fact_density":     fact_density_res,
        "entity_map":       entity_map_res,
        "citable_claims":   claims_res,
        "query_plan":       query_plan_res,
        "citation_audit":   citation_res,
        "total_usage": {
            "input_tokens":  total_in,
            "output_tokens": total_out,
            "cost_usd":      round(total_cost, 6),
            "agents_run":    len(usages),
        },
    }
