"""
Agent: Comparison Agent
------------------------
Takes two fully scored site profiles and produces:
- Strengths / weaknesses for each side
- Content gaps (what competitor covers that you don't)
- Your opportunities (where you can clearly win)
- Prioritized next steps with estimated impact
- Executive summary

Reuses no external agents — pure LLM reasoning over structured score data.
Returns: (ComparisonInsights, AgentTokenUsage)
"""

import json
import re
import openai

from config import get_settings, OPENAI_MODEL
from models.schemas import (
    SEOScore,
    ComparisonInsights,
    NextStep,
    AgentTokenUsage,
)
from services.token_tracker import build_agent_usage


COMPARISON_SYSTEM_PROMPT = """You are a senior SEO strategist. You will receive two websites' SEO analysis data:
- "your_site": the user's site
- "competitor_site": the competitor

Your job is to produce a detailed, actionable comparison.

Return ONLY valid JSON with this exact structure:

{
  "your_strengths": [
    "Specific thing your site does better than the competitor (be concrete)"
  ],
  "your_weaknesses": [
    "Specific area where your site underperforms the competitor"
  ],
  "competitor_strengths": [
    "What the competitor does well that you should learn from"
  ],
  "competitor_weaknesses": [
    "Where the competitor is weak — your opportunity to win"
  ],
  "content_gaps": [
    "Topic, section, or question the competitor covers that your site does not"
  ],
  "your_opportunities": [
    "Specific, concrete action your site can take to outrank the competitor"
  ],
  "executive_summary": "2-3 sentence plain-English overview: current state, biggest gap, most important opportunity.",
  "next_steps": [
    {
      "priority": "critical|high|medium",
      "action": "Specific action to take (verb-first, concrete)",
      "reason": "Why this matters for SEO — reference the scoring data",
      "estimated_impact": "+X to +Y SEO points or ranking improvement"
    }
  ]
}

Rules:
- next_steps must have at least 5 items, ordered by priority (critical first)
- Be specific — don't say "improve content", say "Add a 5-question FAQ section with 40-60 word answers"
- Reference actual score numbers when explaining reasoning
- your_opportunities must map directly to competitor_weaknesses
- Return ONLY valid JSON, no markdown, no preamble"""


def _build_comparison_input(
    your_url: str,
    your_profile: dict,
    your_score: SEOScore,
    competitor_url: str,
    comp_profile: dict,
    comp_score: SEOScore,
) -> str:
    def criteria_summary(score: SEOScore) -> str:
        lines = []
        for c in score.criteria:
            lines.append(f"  {c.name}: {c.score}/{c.max_score} ({c.rating})"
                         + (f" — Issue: {c.issue}" if c.issue else ""))
        return "\n".join(lines)

    return f"""YOUR SITE: {your_url}
Overall SEO Score: {your_score.overall}/100 ({your_score.rating})
Content Type: {your_profile.get("content_type", "unknown")}
Primary Keywords: {", ".join(your_profile.get("primary_keywords", []))}
Word Count: {your_profile.get("word_count", 0)}
Has FAQ: {your_profile.get("has_faq", False)}
Has Author Bio: {your_profile.get("has_author_bio", False)}
Internal Links: {your_profile.get("internal_link_count", 0)}
External Links: {your_profile.get("external_link_count", 0)}
E-E-A-T: Experience={your_score.eeat.experience_score}/25, Expertise={your_score.eeat.expertise_score}/25, Authority={your_score.eeat.authority_score}/25, Trust={your_score.eeat.trust_score}/25
E-E-A-T Signals Found: {", ".join(your_score.eeat.signals_found) or "none"}
E-E-A-T Missing: {", ".join(your_score.eeat.signals_missing) or "none"}
Top Issues: {"; ".join(your_score.top_issues)}

Scoring Breakdown:
{criteria_summary(your_score)}

---

COMPETITOR SITE: {competitor_url}
Overall SEO Score: {comp_score.overall}/100 ({comp_score.rating})
Content Type: {comp_profile.get("content_type", "unknown")}
Primary Keywords: {", ".join(comp_profile.get("primary_keywords", []))}
Word Count: {comp_profile.get("word_count", 0)}
Has FAQ: {comp_profile.get("has_faq", False)}
Has Author Bio: {comp_profile.get("has_author_bio", False)}
Internal Links: {comp_profile.get("internal_link_count", 0)}
External Links: {comp_profile.get("external_link_count", 0)}
E-E-A-T: Experience={comp_score.eeat.experience_score}/25, Expertise={comp_score.eeat.expertise_score}/25, Authority={comp_score.eeat.authority_score}/25, Trust={comp_score.eeat.trust_score}/25
E-E-A-T Signals Found: {", ".join(comp_score.eeat.signals_found) or "none"}
E-E-A-T Missing: {", ".join(comp_score.eeat.signals_missing) or "none"}
Top Issues: {"; ".join(comp_score.top_issues)}

Scoring Breakdown:
{criteria_summary(comp_score)}"""


async def run_comparison_agent(
    your_url: str,
    your_profile: dict,
    your_score: SEOScore,
    competitor_url: str,
    comp_profile: dict,
    comp_score: SEOScore,
) -> tuple[ComparisonInsights, AgentTokenUsage]:
    """
    Compare two scored site profiles and return actionable insights.
    Returns (ComparisonInsights, AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    user_msg = _build_comparison_input(
        your_url, your_profile, your_score,
        competitor_url, comp_profile, comp_score,
    )

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=1500,
        messages=[
            {"role": "system", "content": COMPARISON_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )

    usage = build_agent_usage("comparison_agent", response)

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = _fallback_insights(your_score, comp_score)

    next_steps = [
        NextStep(
            priority=ns.get("priority", "medium"),
            action=ns.get("action", ""),
            reason=ns.get("reason", ""),
            estimated_impact=ns.get("estimated_impact", ""),
        )
        for ns in data.get("next_steps", [])
    ]

    insights = ComparisonInsights(
        your_strengths=data.get("your_strengths", []),
        your_weaknesses=data.get("your_weaknesses", []),
        competitor_strengths=data.get("competitor_strengths", []),
        competitor_weaknesses=data.get("competitor_weaknesses", []),
        content_gaps=data.get("content_gaps", []),
        your_opportunities=data.get("your_opportunities", []),
        executive_summary=data.get("executive_summary", ""),
        next_steps=next_steps,
    )

    return insights, usage


def _fallback_insights(your_score: SEOScore, comp_score: SEOScore) -> dict:
    """Minimal fallback when LLM parse fails."""
    delta = your_score.overall - comp_score.overall
    leader = "ahead of" if delta >= 0 else "behind"
    return {
        "your_strengths": [c.name for c in your_score.criteria if c.rating in ("excellent", "good")][:3],
        "your_weaknesses": [c.name for c in your_score.criteria if c.rating in ("missing", "needs_work")][:3],
        "competitor_strengths": [c.name for c in comp_score.criteria if c.rating in ("excellent", "good")][:3],
        "competitor_weaknesses": [c.name for c in comp_score.criteria if c.rating in ("missing", "needs_work")][:3],
        "content_gaps": ["Could not determine — manual review recommended"],
        "your_opportunities": ["Fix top-scoring issues to close the gap"],
        "executive_summary": (
            f"Your site scores {your_score.overall}/100, {abs(delta)} points {leader} the competitor "
            f"({comp_score.overall}/100). Focus on the criteria below to close the gap."
        ),
        "next_steps": [
            {
                "priority": "critical",
                "action": issue,
                "reason": "Identified as top issue by SEO scorer",
                "estimated_impact": "+3-8 SEO points",
            }
            for issue in your_score.top_issues[:5]
        ],
    }
