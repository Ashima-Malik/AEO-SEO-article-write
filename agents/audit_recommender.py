"""
Agent: Audit Recommender
-------------------------
Takes the audit results and produces top 3 priority recommendations.
Small, focused LLM call — tracked for token usage.
Returns: (recommendations: list[str], AgentTokenUsage)
"""

import re
import json
import openai
from config import get_settings, OPENAI_MODEL
from models.schemas import AuditSection, AgentTokenUsage
from services.token_tracker import build_agent_usage


AUDIT_RECOMMENDER_PROMPT = """You are an expert SEO consultant. Given a technical site audit result, provide exactly 3 priority recommendations.

Each recommendation must be:
- Specific and actionable (start with a verb)
- Reference the actual issue found
- Include estimated SEO impact

Return ONLY valid JSON:
{
  "recommendations": [
    "Fix [specific issue] by [exact action] — estimated impact: [+X SEO points / ranking benefit]",
    "...",
    "..."
  ]
}

Order by impact: most impactful first. No markdown, no preamble."""


async def run_audit_recommender(
    url: str,
    overall_score: int,
    critical_issues: list[str],
    sections: list[AuditSection],
) -> tuple[list[str], AgentTokenUsage]:
    """
    Generate top 3 priority recommendations from audit results.
    Returns (recommendations, AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    # Build a compact summary of failed checks
    failed_checks = []
    for section in sections:
        for check in section.checks:
            if not check.passed:
                failed_checks.append(
                    f"[{check.severity.upper()}] {check.name}: {check.value or 'failed'}"
                    + (f" → {check.recommendation}" if check.recommendation else "")
                )

    user_msg = f"""URL: {url}
Overall Score: {overall_score}/100

CRITICAL/HIGH ISSUES:
{chr(10).join(critical_issues[:10]) or "None"}

ALL FAILED CHECKS:
{chr(10).join(failed_checks[:15]) or "None — all checks passed"}

Provide the 3 highest-impact recommendations to improve this page's SEO score."""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=400,
        messages=[
            {"role": "system", "content": AUDIT_RECOMMENDER_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )

    usage = build_agent_usage("audit_recommender", response)

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    try:
        data = json.loads(raw)
        recommendations = data.get("recommendations", [])[:3]
    except json.JSONDecodeError:
        recommendations = critical_issues[:3]

    return recommendations, usage
