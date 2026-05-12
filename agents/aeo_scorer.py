"""
Agent: AEO Scorer
------------------
Scores content on an 8-criteria AI Readiness rubric (0-100).
Criteria: Direct Answer Density, Entity Clarity, FAQ Schema Readiness,
Factual Claim Density, Citation Worthiness, Schema Markup, Content Freshness,
Authority Signals.

Returns (aeo_score_result dict, AgentTokenUsage)
"""

import json
import re
import openai

from config import get_settings, OPENAI_MODEL, INPUT_COST_PER_TOKEN, OUTPUT_COST_PER_TOKEN
from models.schemas import AgentTokenUsage


AEO_RUBRIC_PROMPT = """You are an expert AEO (Answer Engine Optimization) evaluator. Score the content below on an 8-criteria rubric, each worth up to 100 points. Return ONLY valid JSON.

CRITERIA:
1. direct_answer_density — Does it open with a direct, concise answer? Are key questions answered immediately before elaboration? (0-100)
2. entity_clarity — Are named entities (people, places, brands, products) clearly defined with context? (0-100)
3. faq_schema_readiness — Does it contain Q&A pairs or FAQ-style sections that could be marked up with FAQ schema? (0-100)
4. factual_claim_density — How many verifiable, specific facts (stats, dates, names, numbers) per 500 words? (0-100; 80+ = excellent)
5. citation_worthiness — Would AI assistants cite this? Is it authoritative, specific, and clearly attributed? (0-100)
6. schema_markup — Does the content signal structured data opportunities (HowTo, FAQ, Article, Product, Person)? (0-100)
7. content_freshness — Are dates, statistics, and references recent and clearly timestamped? (0-100)
8. authority_signals — Are there E-E-A-T signals: author credentials, original research, expert quotes, primary sources? (0-100)

CONTENT TO SCORE:
{content}

CONTENT PROFILE (context):
{profile}

Return this exact JSON structure:
{{
  "criteria": {{
    "direct_answer_density": {{ "score": <0-100>, "rationale": "<15-25 words>", "improvements": ["<actionable fix>"] }},
    "entity_clarity":         {{ "score": <0-100>, "rationale": "<15-25 words>", "improvements": ["<actionable fix>"] }},
    "faq_schema_readiness":   {{ "score": <0-100>, "rationale": "<15-25 words>", "improvements": ["<actionable fix>"] }},
    "factual_claim_density":  {{ "score": <0-100>, "rationale": "<15-25 words>", "improvements": ["<actionable fix>"] }},
    "citation_worthiness":    {{ "score": <0-100>, "rationale": "<15-25 words>", "improvements": ["<actionable fix>"] }},
    "schema_markup":          {{ "score": <0-100>, "rationale": "<15-25 words>", "improvements": ["<actionable fix>"] }},
    "content_freshness":      {{ "score": <0-100>, "rationale": "<15-25 words>", "improvements": ["<actionable fix>"] }},
    "authority_signals":      {{ "score": <0-100>, "rationale": "<15-25 words>", "improvements": ["<actionable fix>"] }}
  }},
  "overall": <weighted average 0-100>,
  "rating": "<one of: AI-Ready / Strong / Needs Work / Not Optimized>",
  "top_wins": ["<what the content does well for AEO>", "<second win>"],
  "critical_gaps": ["<most impactful gap>", "<second gap>"],
  "ai_citation_likelihood": "<High / Medium / Low>",
  "recommended_schema_types": ["<e.g. FAQ, HowTo, Article>"]
}}"""


WEIGHTS = {
    "direct_answer_density": 0.20,
    "entity_clarity":         0.12,
    "faq_schema_readiness":   0.12,
    "factual_claim_density":  0.18,
    "citation_worthiness":    0.18,
    "schema_markup":          0.08,
    "content_freshness":      0.06,
    "authority_signals":      0.06,
}


def _parse_aeo_score(raw: str) -> dict:
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {}


def _compute_weighted_overall(criteria: dict) -> int:
    total = 0.0
    for key, weight in WEIGHTS.items():
        score = criteria.get(key, {}).get("score", 50)
        total += score * weight
    return round(total)


def _rating(score: int) -> str:
    if score >= 80: return "AI-Ready"
    if score >= 65: return "Strong"
    if score >= 50: return "Needs Work"
    return "Not Optimized"


async def run_aeo_scorer(
    content: str,
    content_profile: dict | None = None,
) -> tuple[dict, AgentTokenUsage]:
    """
    Score content on AEO rubric.
    content_profile: optional dict from extractor agent for richer context.
    Returns (aeo_score_result, AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    profile_str = json.dumps(content_profile or {}, indent=2)[:800]
    prompt = AEO_RUBRIC_PROMPT.format(
        content=content[:4000],
        profile=profile_str,
    )

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an AEO scoring expert. Always return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1200,
        )
        raw = response.choices[0].message.content or ""
        in_tok  = response.usage.prompt_tokens
        out_tok = response.usage.completion_tokens
    except Exception as e:
        print(f"[AEOScorer] API error: {e}")
        raw = ""
        in_tok, out_tok = 0, 0

    parsed = _parse_aeo_score(raw)
    criteria = parsed.get("criteria", {})

    # Recompute overall from weights if LLM overall is missing
    overall = parsed.get("overall") or _compute_weighted_overall(criteria)
    overall = max(0, min(100, int(overall)))

    result = {
        "overall": overall,
        "rating": parsed.get("rating") or _rating(overall),
        "criteria": criteria,
        "top_wins": parsed.get("top_wins", []),
        "critical_gaps": parsed.get("critical_gaps", []),
        "ai_citation_likelihood": parsed.get("ai_citation_likelihood", "Unknown"),
        "recommended_schema_types": parsed.get("recommended_schema_types", []),
        "weights_used": WEIGHTS,
    }

    cost = (in_tok * INPUT_COST_PER_TOKEN) + (out_tok * OUTPUT_COST_PER_TOKEN)
    usage = AgentTokenUsage(
        agent_name="aeo_scorer",
        input_tokens=in_tok,
        output_tokens=out_tok,
        cost_usd=round(cost, 6),
    )
    return result, usage
