"""
Compare Pipeline
-----------------
Orchestrates the full site-vs-competitor comparison:
  1. Fetch + extract both URLs in parallel          (reuses extract_from_url)
  2. Run extractor + scorer on both in parallel     (reuses existing agents)
  3. Run comparison agent                           (new agent)
  4. Build chart-ready visualization data           (pure Python)
Returns CompareResponse.
"""

import asyncio
import time
import uuid

from models.schemas import (
    CompareRequest, CompareResponse,
    SiteSnapshot, ComparisonInsights, VisualizationData,
    RadarChartData, BarChartData, ScoreGapItem,
    SEOScore, AnalysisTokenUsage,
)
from services.document import extract_from_url
from agents.extractor import run_extractor_agent
from agents.scorer import run_scorer_agent
from agents.comparison_agent import run_comparison_agent
from services.token_tracker import aggregate_token_usage


# ── Pillar → criteria name mapping (matches scorer.py criteria names exactly) ─

_PILLARS = {
    "Keyword Relevance": ["Keyword in H1", "Keyword in First 100 Words", "Keyword in URL Slug"],
    "Content Structure": ["H2/H3 Heading Frequency", "Inverted Pyramid Structure"],
    "E-E-A-T":           ["E-E-A-T Signals"],
    "Technical SEO":     ["Title Tag (≤60 chars)", "Meta Description (150-160 chars)"],
    "Visuals":           ["Visual/Diagram Quality"],
    "Content Complete.": ["FAQ Section", "Author Bio"],
    "Link Ecosystem":    ["Internal Links (min 2)", "External Authority Links"],
}

# Max points per pillar (sum of criteria max_scores)
_PILLAR_MAX = {
    "Keyword Relevance": 15,
    "Content Structure": 25,
    "E-E-A-T":           15,
    "Technical SEO":     10,
    "Visuals":           10,
    "Content Complete.": 15,
    "Link Ecosystem":    10,
}


# ── Visualization builders ─────────────────────────────────────────────────────

def _criteria_score_map(score: SEOScore) -> dict[str, tuple[int, int, str]]:
    """Return {name: (score, max_score, severity)} for quick lookup."""
    return {c.name: (c.score, c.max_score, c.severity) for c in score.criteria}


def _build_radar(your_score: SEOScore, comp_score: SEOScore) -> RadarChartData:
    your_map = _criteria_score_map(your_score)
    comp_map = _criteria_score_map(comp_score)

    dimensions = []
    your_scores = []
    comp_scores = []

    for pillar, criteria_names in _PILLARS.items():
        pillar_max = _PILLAR_MAX[pillar]

        your_raw = sum(your_map.get(name, (0, 0, ""))[0] for name in criteria_names)
        comp_raw = sum(comp_map.get(name, (0, 0, ""))[0] for name in criteria_names)

        dimensions.append(pillar)
        your_scores.append(round(your_raw / pillar_max * 100, 1))
        comp_scores.append(round(comp_raw / pillar_max * 100, 1))

    return RadarChartData(
        dimensions=dimensions,
        your_scores=your_scores,
        competitor_scores=comp_scores,
    )


def _build_bar(your_score: SEOScore, comp_score: SEOScore) -> BarChartData:
    comp_map = _criteria_score_map(comp_score)

    labels, your_scores, comp_scores, max_scores = [], [], [], []

    for c in your_score.criteria:
        comp_val = comp_map.get(c.name, (0, c.max_score, ""))[0]
        # Shorten long label names for bar chart display
        label = (c.name
                 .replace("Keyword in ", "KW in ")
                 .replace(" (≤60 chars)", "")
                 .replace(" (150-160 chars)", "")
                 .replace("(min 2)", "")
                 .strip())
        labels.append(label)
        your_scores.append(c.score)
        comp_scores.append(comp_val)
        max_scores.append(c.max_score)

    return BarChartData(labels=labels, your_scores=your_scores,
                        competitor_scores=comp_scores, max_scores=max_scores)


def _build_gap_table(your_score: SEOScore, comp_score: SEOScore) -> list[ScoreGapItem]:
    comp_map = _criteria_score_map(comp_score)
    gaps = []

    for c in your_score.criteria:
        comp_val, _, severity = comp_map.get(c.name, (0, c.max_score, c.severity))
        gap = comp_val - c.score  # positive = competitor is ahead
        gaps.append(ScoreGapItem(
            criterion=c.name,
            your_score=c.score,
            competitor_score=comp_val,
            max_score=c.max_score,
            gap=gap,
            severity=c.severity,
        ))

    # Sort: biggest gap (competitor ahead) first — these are your worst areas
    return sorted(gaps, key=lambda x: x.gap, reverse=True)


def _build_keyword_overlap(your_profile: dict, comp_profile: dict) -> tuple[list, list, list]:
    your_kws = set(kw.lower() for kw in (your_profile.get("primary_keywords") or [])
                   + (your_profile.get("semantic_keywords") or []))
    comp_kws = set(kw.lower() for kw in (comp_profile.get("primary_keywords") or [])
                   + (comp_profile.get("semantic_keywords") or []))

    overlap = sorted(your_kws & comp_kws)
    your_unique = sorted(your_kws - comp_kws)
    comp_unique = sorted(comp_kws - your_kws)
    return overlap, your_unique, comp_unique


def _build_visualization(
    your_profile: dict, your_score: SEOScore,
    comp_profile: dict, comp_score: SEOScore,
) -> VisualizationData:
    radar = _build_radar(your_score, comp_score)
    bar = _build_bar(your_score, comp_score)
    score_gaps = _build_gap_table(your_score, comp_score)
    overlap, your_unique, comp_unique = _build_keyword_overlap(your_profile, comp_profile)

    eeat_comparison = {
        "your": {
            "experience": your_score.eeat.experience_score,
            "expertise": your_score.eeat.expertise_score,
            "authority": your_score.eeat.authority_score,
            "trust": your_score.eeat.trust_score,
        },
        "competitor": {
            "experience": comp_score.eeat.experience_score,
            "expertise": comp_score.eeat.expertise_score,
            "authority": comp_score.eeat.authority_score,
            "trust": comp_score.eeat.trust_score,
        },
    }

    return VisualizationData(
        radar=radar,
        bar=bar,
        score_gaps=score_gaps,
        your_overall=your_score.overall,
        competitor_overall=comp_score.overall,
        score_delta=your_score.overall - comp_score.overall,
        keyword_overlap=overlap,
        your_unique_keywords=your_unique,
        competitor_unique_keywords=comp_unique,
        eeat_comparison=eeat_comparison,
    )


def _build_snapshot(url: str, profile: dict, score: SEOScore) -> SiteSnapshot:
    return SiteSnapshot(
        url=url,
        title=profile.get("title_tag") or profile.get("h1") or url,
        overall_score=score.overall,
        rating=score.rating,
        rating_emoji=score.rating_emoji,
        word_count=profile.get("word_count", 0),
        primary_keywords=profile.get("primary_keywords", [])[:5],
        content_type=profile.get("content_type", "general"),
        has_faq=bool(profile.get("has_faq", False)),
        has_author_bio=bool(profile.get("has_author_bio", False)),
        internal_link_count=profile.get("internal_link_count", 0),
        external_link_count=profile.get("external_link_count", 0),
    )


# ── Main pipeline ──────────────────────────────────────────────────────────────

async def run_compare_pipeline(request: CompareRequest) -> CompareResponse:
    """
    Full comparison pipeline:
    1. Fetch both URLs in parallel
    2. Extractor + Scorer for both sites in parallel
    3. Comparison Agent (LLM insights)
    4. Build visualization data (pure Python)
    """
    start_time = time.time()
    compare_id = str(uuid.uuid4())
    all_agent_usages = []

    # ── Step 1: Fetch both URLs in parallel ───────────────────────────────────
    print(f"[Compare {compare_id[:8]}] Fetching both URLs in parallel...")
    your_content, comp_content = await asyncio.gather(
        extract_from_url(request.your_url),
        extract_from_url(request.competitor_url),
    )

    # ── Step 2: Extract + Score both sites in parallel ────────────────────────
    print(f"[Compare {compare_id[:8]}] Running extractor + scorer on both sites...")
    (
        (your_profile, your_extractor_usage),
        (comp_profile, comp_extractor_usage),
    ) = await asyncio.gather(
        run_extractor_agent(your_content),
        run_extractor_agent(comp_content),
    )
    all_agent_usages.extend([your_extractor_usage, comp_extractor_usage])

    your_ct = your_profile.get("content_type", "general")
    comp_ct = comp_profile.get("content_type", "general")

    (
        (your_score, _, your_scorer_usage),
        (comp_score, _, comp_scorer_usage),
    ) = await asyncio.gather(
        run_scorer_agent(your_profile, your_content.full_text, your_ct),
        run_scorer_agent(comp_profile, comp_content.full_text, comp_ct),
    )
    all_agent_usages.extend([your_scorer_usage, comp_scorer_usage])

    print(f"[Compare {compare_id[:8]}] Scores — You: {your_score.overall}/100  Competitor: {comp_score.overall}/100")

    # ── Step 3: Comparison Agent ──────────────────────────────────────────────
    print(f"[Compare {compare_id[:8]}] Running comparison agent...")
    insights, comparison_usage = await run_comparison_agent(
        your_url=request.your_url,
        your_profile=your_profile,
        your_score=your_score,
        competitor_url=request.competitor_url,
        comp_profile=comp_profile,
        comp_score=comp_score,
    )
    all_agent_usages.append(comparison_usage)

    # ── Step 4: Build visualization data ─────────────────────────────────────
    print(f"[Compare {compare_id[:8]}] Building visualization data...")
    visualization_data = _build_visualization(your_profile, your_score, comp_profile, comp_score)

    # ── Aggregate tokens ──────────────────────────────────────────────────────
    token_usage = aggregate_token_usage(all_agent_usages)
    processing_time = round(time.time() - start_time, 2)

    print(f"[Compare {compare_id[:8]}] Done in {processing_time}s — "
          f"Tokens: {token_usage.total_tokens:,} (${token_usage.total_cost_usd:.4f})")

    return CompareResponse(
        compare_id=compare_id,
        your_site=_build_snapshot(request.your_url, your_profile, your_score),
        competitor_site=_build_snapshot(request.competitor_url, comp_profile, comp_score),
        your_score=your_score,
        competitor_score=comp_score,
        insights=insights,
        visualization_data=visualization_data,
        token_usage=token_usage,
        processing_time_seconds=processing_time,
        agents_used=["extractor×2", "scorer×2", "comparison_agent"],
    )
