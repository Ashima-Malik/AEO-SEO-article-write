"""
Agent 5: URL & Link Auditor
----------------------------
Specialized agent for auditing URL structure and link ecosystem.
Based on Section 5 of the SEO rules document.

Runs as part of the main analysis pipeline AND can be called standalone
for a URL/link-only audit.
"""

import json
import re
import openai
from config import get_settings, OPENAI_MODEL
from models.schemas import AgentTokenUsage
from services.token_tracker import build_agent_usage
from services.rules_loader import get_active_rules, parse_rules_into_categories


URL_AUDITOR_SYSTEM_PROMPT = """You are an expert SEO URL and link strategist. Audit the provided content for URL structure and link quality issues.

Apply these EXACT rules from the SEO strategy document:

URL STRUCTURE RULES:
- Must be keyword-first slug
- Hyphens (not underscores)
- No stop words (the, a, an, how, to, for, of, and, or)
- No dates for evergreen content
- Short and descriptive
- Folder structure: /category/topic/article

INTERNAL LINK RULES:
- Minimum 2 internal links per article (up to ~8)
- Anchor text must be descriptive topic phrase
- Never use "click here", "read more", "here", "this article"
- Every spoke article must link to its hub/pillar page
- New article needs links from 3 highest-traffic existing articles

EXTERNAL LINK RULES:
- 1-2 external links minimum
- Only link to: research papers, government sites, Tier 1 publications (NYT, FT, Nature, Reuters), official docs
- Never link to: competitors, low-DA sites, paywalled content
- rel=nofollow ONLY for sponsored/UGC links, NOT genuine citations

Return ONLY valid JSON:
{
  "url_analysis": {
    "current_slug": "current URL slug or null",
    "issues": ["list of URL issues"],
    "recommended_slug": "keyword-first-optimized-slug",
    "stop_words_found": ["list"],
    "has_underscores": true/false,
    "has_dates": true/false,
    "is_keyword_first": true/false
  },
  "internal_links": {
    "count": number,
    "minimum_met": true/false,
    "anchor_text_issues": ["list of bad anchor texts found"],
    "orphan_risk": true/false,
    "recommendations": ["list of internal link recommendations"]
  },
  "external_links": {
    "count": number,
    "minimum_met": true/false,
    "low_quality_links": ["any suspect external links"],
    "missing_authority_links": true/false,
    "recommendations": ["list of external link recommendations"]
  },
  "hub_spoke_assessment": {
    "has_hub_link": true/false,
    "spoke_links_count": number,
    "recommendation": "hub and spoke recommendation"
  },
  "priority_fixes": [
    {
      "issue": "description",
      "fix": "exact fix to apply",
      "impact": "critical|high|medium|low"
    }
  ]
}"""


async def run_url_auditor_agent(
    content: str,
    current_url: str | None = None,
    target_keyword: str | None = None,
    internal_links: list[str] = None,
    external_links: list[str] = None
) -> tuple[dict, AgentTokenUsage]:
    """
    Agent 5: Audit URL structure and link ecosystem.
    Returns (audit_results, AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    rules_categories = parse_rules_into_categories(get_active_rules())
    url_rules = rules_categories.get("url_links", "")

    # Extract inline links from content
    md_internal = re.findall(r'\[([^\]]+)\]\((/[^)]+)\)', content)
    md_external = re.findall(r'\[([^\]]+)\]\((https?://[^)]+)\)', content)

    all_internal = (internal_links or []) + [link[1] for link in md_internal]
    all_external = (external_links or []) + [link[1] for link in md_external]
    all_anchors = [link[0] for link in (md_internal + md_external)]

    user_message = f"""
AUDIT REQUEST:

Target Keyword: {target_keyword or 'Not provided'}
Current URL: {current_url or 'Not provided'}

Internal Links Found ({len(all_internal)}):
{chr(10).join(f'  - {l}' for l in all_internal[:20]) or '  None found'}

External Links Found ({len(all_external)}):
{chr(10).join(f'  - {l}' for l in all_external[:20]) or '  None found'}

Anchor Texts Found:
{chr(10).join(f'  - "{a}"' for a in all_anchors[:20]) or '  None found'}

CONTENT EXCERPT (first 1500 chars):
{content[:1500]}

RELEVANT SEO RULES:
{url_rules}
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=1000,
        messages=[
            {"role": "system", "content": URL_AUDITOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    # Capture token usage
    usage = build_agent_usage("url_auditor", response)

    try:
        return json.loads(raw), usage
    except json.JSONDecodeError:
        return _build_fallback_url_audit(current_url, target_keyword, len(all_internal), len(all_external)), usage


def _build_fallback_url_audit(
    url: str | None,
    keyword: str | None,
    internal_count: int,
    external_count: int
) -> dict:
    """Fallback URL audit if Claude response fails."""
    issues = []
    if not keyword:
        issues.append("Target keyword not provided — cannot verify keyword-first URL")
    if internal_count < 2:
        issues.append(f"Only {internal_count} internal links found — minimum 2 required")
    if external_count == 0:
        issues.append("No external links found — 1-2 authority links required")

    return {
        "url_analysis": {
            "current_slug": url,
            "issues": issues,
            "recommended_slug": keyword.lower().replace(" ", "-") if keyword else "add-keyword-slug",
            "stop_words_found": [],
            "has_underscores": "_" in (url or ""),
            "has_dates": bool(re.search(r'\d{4}', url or "")),
            "is_keyword_first": False
        },
        "internal_links": {
            "count": internal_count,
            "minimum_met": internal_count >= 2,
            "anchor_text_issues": [],
            "orphan_risk": internal_count == 0,
            "recommendations": ["Add minimum 2 internal links with descriptive anchor text"] if internal_count < 2 else []
        },
        "external_links": {
            "count": external_count,
            "minimum_met": external_count >= 1,
            "low_quality_links": [],
            "missing_authority_links": external_count == 0,
            "recommendations": ["Add 1-2 external links to high-authority sources"] if external_count == 0 else []
        },
        "hub_spoke_assessment": {
            "has_hub_link": False,
            "spoke_links_count": 0,
            "recommendation": "Implement hub & spoke internal linking architecture"
        },
        "priority_fixes": [{"issue": i, "fix": "See SEO rules", "impact": "high"} for i in issues]
    }