"""
Main SEO Analysis Pipeline
---------------------------
Orchestrates all 5 agents and tracks token usage across every call.
Includes a gap-fill refinement pass when score < 85 after first rewrite.
"""

import time
import uuid
import asyncio
import openai
from datetime import datetime
from models.schemas import (
    SEOAnalysisResponse, ExtractedContent, InputType, ContentType,
    AnalysisTokenUsage, TokenWarningLevel, AgentTokenUsage, SEOScore,
)
from agents.extractor import run_extractor_agent
from agents.scorer import run_scorer_agent
from agents.rewriter import run_rewriter_agent
from agents.validator import run_validator_agent
from agents.url_auditor import run_url_auditor_agent
from services.diff_generator import generate_diff
from services.token_tracker import (
    aggregate_token_usage,
    check_token_budget,
    build_agent_usage,
    calculate_cost,
)
from config import get_settings, OPENAI_MODEL

CURRENT_YEAR = datetime.now().year
GAP_FILL_SCORE_THRESHOLD = 85  # trigger second pass if score is below this


async def run_full_analysis(
    extracted_content: ExtractedContent,
    input_type: InputType,
    target_keyword: str | None = None,
    target_keywords: list[str] | None = None,
    content_type: ContentType | None = None,
    current_url: str | None = None,
    user_tone_prompt: str | None = None,
    user_brief: str = "",
    # Token budget context — passed in from auth layer
    user_tier: str = "starter",
    tokens_used_this_month: int = 0,
) -> SEOAnalysisResponse:
    """
    Run the complete 5-agent SEO analysis pipeline.
    Captures token usage from every agent call.
    Returns full response including token usage and any budget warnings.
    """
    start_time = time.time()
    analysis_id = str(uuid.uuid4())
    all_agent_usages = []   # collect AgentTokenUsage from every agent

    # ── Agent 1: Extract & Classify ──────────────────────────────────────────
    print(f"[{analysis_id[:8]}] Agent 1: Extracting...")
    content_profile, extractor_usage = await run_extractor_agent(
        extracted_content,
        target_keyword=target_keyword,
        target_keywords=target_keywords,
        content_type=content_type,
    )
    all_agent_usages.append(extractor_usage)

    # Build keyword list: user-provided takes priority, then extractor-detected
    detected_keywords: list[str] = content_profile.get("primary_keywords") or []
    if target_keywords:
        for kw in reversed(target_keywords):
            if kw not in detected_keywords:
                detected_keywords.insert(0, kw)
        detected_keywords = detected_keywords[:5]
    elif target_keyword and target_keyword not in detected_keywords:
        detected_keywords.insert(0, target_keyword)

    detected_keyword = detected_keywords[0] if detected_keywords else (target_keyword or "")
    detected_content_type = (
        content_type.value if content_type
        else content_profile.get("content_type", "general")
    )

    # ── Agent 2 + Agent 5 in parallel ────────────────────────────────────────
    print(f"[{analysis_id[:8]}] Agent 2 + 5: Scoring + URL audit (parallel)...")
    (score_before, score_data, scorer_usage), (url_audit, url_usage) = await asyncio.gather(
        run_scorer_agent(content_profile, extracted_content.full_text, detected_content_type),
        run_url_auditor_agent(
            extracted_content.full_text,
            current_url=current_url,
            target_keyword=detected_keyword,
            internal_links=extracted_content.internal_links,
            external_links=extracted_content.external_links,
        )
    )
    all_agent_usages.append(scorer_usage)
    all_agent_usages.append(url_usage)

    print(f"[{analysis_id[:8]}] Score before: {score_before.overall}/100")

    # ── Agent 3: Rewrite ─────────────────────────────────────────────────────
    print(f"[{analysis_id[:8]}] Agent 3: Rewriting...")
    optimized_content, changes_made, rewriter_usage = await run_rewriter_agent(
        original_content=extracted_content.full_text,
        content_type=detected_content_type,
        target_keyword=detected_keyword,
        score_before=score_before.overall,
        issues=score_before.top_issues,
        score_data=score_data,
        target_keywords=detected_keywords,
        user_tone_prompt=user_tone_prompt,
        user_brief=user_brief,
    )
    all_agent_usages.append(rewriter_usage)

    # ── Agent 4: Validate ────────────────────────────────────────────────────
    print(f"[{analysis_id[:8]}] Agent 4: Validating...")
    score_after, validator_usage = await run_validator_agent(
        optimized_content=optimized_content,
        target_keyword=detected_keyword,
        content_type=detected_content_type,
        original_score=score_before.overall,
    )
    all_agent_usages.append(validator_usage)

    print(f"[{analysis_id[:8]}] Score after: {score_after.overall}/100 "
          f"(+{score_after.overall - score_before.overall})")

    # ── Gap-fill refinement pass (if score < threshold) ───────────────────────
    if score_after.overall < GAP_FILL_SCORE_THRESHOLD:
        print(f"[{analysis_id[:8]}] Score {score_after.overall} < {GAP_FILL_SCORE_THRESHOLD} — running gap-fill pass...")
        try:
            optimized_content, gap_fill_usage = await _run_gap_fill_pass(
                content=optimized_content,
                score_after=score_after,
                target_keyword=detected_keyword,
                content_type=detected_content_type,
            )
            all_agent_usages.append(gap_fill_usage)

            # Re-validate after gap-fill
            score_after_v2, validator_v2_usage = await run_validator_agent(
                optimized_content=optimized_content,
                target_keyword=detected_keyword,
                content_type=detected_content_type,
                original_score=score_before.overall,
            )
            all_agent_usages.append(validator_v2_usage)

            if score_after_v2.overall > score_after.overall:
                score_after = score_after_v2
                print(f"[{analysis_id[:8]}] Gap-fill improved score to {score_after.overall}/100")
            else:
                print(f"[{analysis_id[:8]}] Gap-fill made no improvement, keeping original")
        except Exception as gap_err:
            print(f"[{analysis_id[:8]}] Gap-fill pass failed (non-fatal): {gap_err}")

    # ── Aggregate token usage ─────────────────────────────────────────────────
    token_usage = aggregate_token_usage(all_agent_usages)
    print(f"[{analysis_id[:8]}] Tokens used: {token_usage.total_tokens:,} "
          f"(${token_usage.total_cost_usd:.4f})")

    # ── Check budget warning AFTER analysis (for next-request awareness) ─────
    new_total = tokens_used_this_month + token_usage.total_tokens
    warning_level, warning_message = check_token_budget(user_tier, new_total)

    # ── Generate diff ─────────────────────────────────────────────────────────
    diff_chunks = generate_diff(
        original=extracted_content.full_text,
        optimized=optimized_content,
        changes_summary=changes_made,
    )

    processing_time = round(time.time() - start_time, 2)
    print(f"[{analysis_id[:8]}] Done in {processing_time}s")

    return SEOAnalysisResponse(
        analysis_id=analysis_id,
        input_type=input_type,
        content_type=ContentType(detected_content_type),
        target_keyword=detected_keyword,

        score_before=score_before,
        score_after=score_after,

        extracted=extracted_content,
        optimized_content=optimized_content,
        diff_chunks=diff_chunks,
        changes_made=[_build_optimization_change(c) for c in changes_made],

        suggested_title_tag=score_data.get("suggested_title_tag", ""),
        suggested_meta_description=score_data.get("suggested_meta_description", ""),
        suggested_url_slug=score_data.get("suggested_url_slug", ""),

        word_count_original=extracted_content.word_count,
        word_count_optimized=len(optimized_content.split()),

        token_usage=token_usage,
        warning_level=warning_level,
        warning_message=warning_message,

        processing_time_seconds=processing_time,
        agents_used=["extractor", "scorer", "url_auditor", "rewriter", "validator"],
    )


def _build_optimization_change(raw_change: dict):
    from models.schemas import OptimizationChange
    return OptimizationChange(
        location=raw_change.get("location", ""),
        original=raw_change.get("original", ""),
        optimized=raw_change.get("optimized", ""),
        rule=raw_change.get("rule", ""),
        impact=raw_change.get("impact", "medium"),
    )


async def _run_gap_fill_pass(
    content: str,
    score_after: SEOScore,
    target_keyword: str,
    content_type: str,
) -> tuple[str, AgentTokenUsage]:
    """
    Targeted gap-fill: fixes only the specific criteria that scored below maximum.
    Called when the validator score < GAP_FILL_SCORE_THRESHOLD (85).
    Returns (patched_content, AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    # Build list of failing criteria with their fix instructions
    failing = []
    for criterion in (score_after.criteria or []):
        score = getattr(criterion, "score", None) or criterion.get("score", 5) if isinstance(criterion, dict) else getattr(criterion, "score", 5)
        max_score = getattr(criterion, "max_score", None) or criterion.get("max_score", 5) if isinstance(criterion, dict) else getattr(criterion, "max_score", 5)
        name = getattr(criterion, "name", "") if not isinstance(criterion, dict) else criterion.get("name", "")
        fix = getattr(criterion, "fix", "") if not isinstance(criterion, dict) else criterion.get("fix", "")
        if score < max_score and fix:
            failing.append(f"- [{name}] {fix}")

    if not failing:
        # Nothing specific to fix — try to improve from top issues
        failing = [f"- {issue}" for issue in (score_after.top_issues or [])[:5]]

    failing_str = "\n".join(failing) if failing else "- Add more detail and depth to each section"

    gap_fill_prompt = f"""You are an expert SEO editor doing a targeted fix pass on an article.

The article scored {score_after.overall}/100 after optimization. Fix ONLY the specific issues listed below.
Do NOT rewrite the whole article — make surgical, targeted improvements.

TARGET KEYWORD: {target_keyword}
CONTENT TYPE: {content_type}

SPECIFIC GAPS TO FIX (address every single one):
{failing_str}

ADDITIONAL CHECKS:
- If there is no FAQ section with 5 H3 questions (40-60 word answers each), ADD it before the author bio
- If the H1 does not contain "{target_keyword}" in the first 3 words, fix the H1
- If "{target_keyword}" is not in the first 100 words, add it naturally to the opening paragraph
- If there are fewer than 3 [INTERNAL LINK: ...] placeholders, add them
- If there is no ## About the Author section, add a 4-sentence author bio with credential signal
- If any H2 section has fewer than 3 paragraphs, expand it with specific details and examples

ARTICLE TO FIX:
{content}

Return the COMPLETE fixed article in clean markdown. Keep all sections that are already good.
Only expand or add — do not remove existing content."""

    def _gap_fill_sync():
        # Use Responses API with web_search_preview so the editor can look up
        # current facts or stats when expanding thin sections.
        return client.responses.create(
            model=OPENAI_MODEL,
            instructions=(
                "You are a precise SEO editor. Fix only the specific issues listed. "
                "Return the complete improved article. Never remove sections that are already correct."
            ),
            input=gap_fill_prompt,
            tools=[{"type": "web_search_preview"}],
            max_output_tokens=12000,
            temperature=0.5,
        )

    response = await asyncio.to_thread(_gap_fill_sync)
    usage = build_agent_usage("gap_fill", response)
    patched = (response.output_text or "").strip()
    return patched, usage