"""
AI Writer Pipeline
------------------
Orchestrates:
  1. Competitor Analyzer — fetch + analyze competitor URLs
  2. AI Writer — generate the new article using competitor gaps
Tracks token usage across both agents.
"""

import time
import uuid

from models.schemas import (
    AIWriterRequest,
    AIWriterResponse,
    CompetitorAnalysisResult,
    ContentType,
    AnalysisTokenUsage,
)
from agents.competitor_analyzer import run_competitor_analyzer_agent
from agents.ai_writer import run_ai_writer_agent
from services.token_tracker import aggregate_token_usage

_EMPTY_COMPETITOR_ANALYSIS = CompetitorAnalysisResult(
    articles_analyzed=[],
    common_strengths=[],
    common_weaknesses=[],
    content_gaps=[],
    differentiation_angle="",
    recommended_structure="",
    long_tail_opportunities=[],
)


async def run_writer_pipeline(request: AIWriterRequest) -> AIWriterResponse:
    """
    Run the full AI Writer pipeline.
    1. Competitor analysis (skipped if no URLs provided)
    2. Write the new article
    Returns AIWriterResponse.
    """
    start_time = time.time()
    writer_id = str(uuid.uuid4())
    all_agent_usages = []

    content_type = request.content_type or ContentType.ARTICLE

    # ── Step 1: Competitor Analysis (optional) ────────────────────────────────
    valid_urls = [u for u in request.competitor_urls if u.strip()]
    if valid_urls:
        print(f"[Writer {writer_id[:8]}] Analyzing {len(valid_urls)} competitor URL(s)...")
        competitor_analysis, competitor_usage = await run_competitor_analyzer_agent(
            competitor_urls=valid_urls,
            topic_prompt=request.topic_prompt,
        )
        all_agent_usages.append(competitor_usage)
        print(f"[Writer {writer_id[:8]}] Competitors analyzed. Gaps: {len(competitor_analysis.content_gaps)}")
    else:
        print(f"[Writer {writer_id[:8]}] No competitor URLs — writing from topic only.")
        competitor_analysis = _EMPTY_COMPETITOR_ANALYSIS

    # ── Step 2: Resolve keywords ──────────────────────────────────────────────
    target_keywords = request.target_keywords or competitor_analysis.long_tail_opportunities[:3] or []

    # ── Step 3: Write the Article ─────────────────────────────────────────────
    print(f"[Writer {writer_id[:8]}] Writing article...")
    written_content, metadata, writer_usage = await run_ai_writer_agent(
        topic_prompt=request.topic_prompt,
        target_keywords=target_keywords,
        content_type=content_type.value,
        competitor_analysis=competitor_analysis,
        user_tone_prompt=request.user_tone_prompt,
    )
    all_agent_usages.append(writer_usage)

    token_usage = aggregate_token_usage(all_agent_usages)
    print(f"[Writer {writer_id[:8]}] Done. Tokens: {token_usage.total_tokens:,} (${token_usage.total_cost_usd:.4f})")

    agents_used = ["ai_writer"] if not valid_urls else ["competitor_analyzer", "ai_writer"]

    return AIWriterResponse(
        writer_id=writer_id,
        topic_prompt=request.topic_prompt,
        content_type=content_type,
        target_keywords=target_keywords,
        competitor_analysis=competitor_analysis,
        written_content=written_content,
        suggested_title_tag=metadata.get("suggested_title_tag", ""),
        suggested_meta_description=metadata.get("suggested_meta_description", ""),
        suggested_url_slug=metadata.get("suggested_url_slug", ""),
        token_usage=token_usage,
        processing_time_seconds=round(time.time() - start_time, 2),
        agents_used=agents_used,
    )
