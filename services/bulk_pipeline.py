"""
Bulk Analysis Pipeline
-----------------------
Runs full SEO analysis on 2-10 URLs sequentially.
Tracks token usage per URL and aggregates across all.
Returns BulkAnalyzeResponse.
"""

import time
import uuid
import asyncio

from models.schemas import (
    BulkAnalyzeRequest, BulkAnalyzeResponse,
    BulkURLResult, AnalysisTokenUsage, ContentType,
)
from services.document import extract_from_url
from agents.extractor import run_extractor_agent
from agents.scorer import run_scorer_agent
from services.token_tracker import aggregate_token_usage, build_agent_usage
from models.schemas import AgentTokenUsage


async def _analyze_single_url(
    url: str,
    target_keyword: str | None,
    content_type: ContentType | None,
) -> BulkURLResult:
    """Run extractor + scorer on one URL. Returns BulkURLResult."""
    try:
        extracted = await extract_from_url(url)

        profile, extractor_usage = await run_extractor_agent(
            extracted,
            target_keyword=target_keyword,
            content_type=content_type,
        )

        ct = content_type.value if content_type else profile.get("content_type", "general")
        score, _, scorer_usage = await run_scorer_agent(profile, extracted.full_text, ct)

        token_usage = aggregate_token_usage([extractor_usage, scorer_usage])

        return BulkURLResult(
            url=url,
            status="success",
            overall_score=score.overall,
            rating=score.rating,
            rating_emoji=score.rating_emoji,
            top_issues=score.top_issues[:3],
            quick_wins=score.quick_wins[:2],
            token_usage=token_usage,
        )
    except Exception as e:
        print(f"[BulkPipeline] Failed for {url}: {e}")
        # Return zero-cost usage for failed URLs
        zero_usage = aggregate_token_usage([])
        return BulkURLResult(
            url=url,
            status="failed",
            error=str(e),
            token_usage=zero_usage,
        )


async def run_bulk_pipeline(request: BulkAnalyzeRequest) -> BulkAnalyzeResponse:
    """
    Analyze 2-10 URLs sequentially (to avoid rate limits).
    Tracks token usage per URL and aggregates total.
    """
    start_time = time.time()
    bulk_id = str(uuid.uuid4())

    print(f"[Bulk {bulk_id[:8]}] Starting bulk analysis of {len(request.urls)} URLs...")

    results: list[BulkURLResult] = []
    all_per_url_usages: list[AnalysisTokenUsage] = []

    # Sequential — avoids hitting OpenAI rate limits on bursts
    for i, url in enumerate(request.urls):
        print(f"[Bulk {bulk_id[:8]}] {i+1}/{len(request.urls)}: {url}")
        result = await _analyze_single_url(url, request.target_keyword, request.content_type)
        results.append(result)
        if result.token_usage:
            all_per_url_usages.append(result.token_usage)

    # Aggregate token usage across all URLs into one AnalysisTokenUsage
    total_input = sum(u.total_input_tokens for u in all_per_url_usages)
    total_output = sum(u.total_output_tokens for u in all_per_url_usages)
    total_tokens = total_input + total_output

    from config import INPUT_COST_PER_TOKEN, OUTPUT_COST_PER_TOKEN
    total_cost = (total_input * INPUT_COST_PER_TOKEN) + (total_output * OUTPUT_COST_PER_TOKEN)

    aggregate_usage = AnalysisTokenUsage(
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost, 6),
        per_agent=[],   # per-agent breakdown not meaningful for bulk
    )

    successful = sum(1 for r in results if r.status == "success")
    failed = sum(1 for r in results if r.status == "failed")
    processing_time = round(time.time() - start_time, 2)

    print(f"[Bulk {bulk_id[:8]}] Done: {successful} success, {failed} failed — "
          f"{total_tokens:,} tokens (${total_cost:.4f}) in {processing_time}s")

    return BulkAnalyzeResponse(
        bulk_id=bulk_id,
        total_urls=len(request.urls),
        successful=successful,
        failed=failed,
        results=results,
        aggregate_token_usage=aggregate_usage,
        processing_time_seconds=processing_time,
    )
