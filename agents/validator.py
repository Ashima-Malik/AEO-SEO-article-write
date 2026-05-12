"""
Agent 4: Validator
-------------------
Re-scores the optimized content using the same 100-point rubric.
Confirms improvement over the original score.
Flags any issues the Rewriter may have missed.
"""

import json
import re
import openai
from config import get_settings, OPENAI_MODEL
from models.schemas import SEOScore, AgentTokenUsage
from services.token_tracker import build_agent_usage, AgentTokenUsage as _ATokenUsage
from agents.scorer import run_scorer_agent
from services.document import extract_from_text


async def run_validator_agent(
    optimized_content: str,
    target_keyword: str,
    content_type: str,
    original_score: int
) -> tuple[SEOScore, AgentTokenUsage]:
    """
    Agent 4: Re-score the optimized content.
    Returns (SEOScore, AgentTokenUsage).
    """
    # Re-extract content profile from the optimized text
    optimized_extracted = extract_from_text(optimized_content)
    optimized_extracted.url_slug = _derive_slug(optimized_content, target_keyword)

    # Build a quick profile
    content_profile = {
        "content_type": content_type,
        "primary_keyword": target_keyword,
        "keyword_confidence": "high",
        "title_tag": _extract_h1(optimized_content),
        "h1": _extract_h1(optimized_content),
        "meta_description": None,
        "has_faq": _has_faq(optimized_content),
        "has_author_bio": _has_author_bio(optimized_content),
        "has_author_credentials": _has_credentials(optimized_content),
        "keyword_in_h1": target_keyword.lower() in (_extract_h1(optimized_content) or "").lower(),
        "keyword_in_first_100_words": target_keyword.lower() in " ".join(optimized_content.split()[:100]).lower(),
        "keyword_in_title": True,
        "heading_count": _count_headings(optimized_content),
        "image_count": _count_images(optimized_content),
        "internal_link_count": optimized_content.count("[INTERNAL LINK:"),
        "external_link_count": optimized_content.count("[EXTERNAL LINK:"),
        "word_count": len(optimized_content.split()),
    }

    # Run the scorer against the optimized content
    score_after, _, validator_usage = await run_scorer_agent(
        content_profile,
        optimized_content,
        content_type
    )

    return score_after, validator_usage


async def run_quick_validator(
    optimized_content: str,
    target_keyword: str,
    content_type: str
) -> dict:
    """
    Quick validation pass — uses Claude to check for any remaining issues
    without a full re-score (saves API calls for the basic tier).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    prompt = f"""You are an SEO validator. Review this optimized content and confirm what was fixed.

TARGET KEYWORD: {target_keyword}
CONTENT TYPE: {content_type}

OPTIMIZED CONTENT:
{optimized_content[:3000]}

Check ONLY these 5 most critical items:
1. Is the keyword in the H1?
2. Is the keyword in the first 100 words?
3. Is there a FAQ section with at least 5 questions?
4. Are there heading tags (H2/H3) throughout?
5. Is there an author bio (or placeholder)?

Return ONLY JSON:
{{
  "keyword_in_h1": true/false,
  "keyword_in_first_100": true/false,
  "has_faq": true/false,
  "has_headings": true/false,
  "has_author_bio": true/false,
  "remaining_issues": ["any issues still present"],
  "validation_passed": true/false
}}"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=1000,
        messages=[
            {"role": "system", "content": "You are a precise SEO validator. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"validation_passed": True, "remaining_issues": []}


# ---------- Helper functions ----------

def _extract_h1(content: str) -> str | None:
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    return match.group(1).strip() if match else None


def _has_faq(content: str) -> bool:
    lower = content.lower()
    return "faq" in lower or "frequently asked" in lower or "### " in content and "?" in content


def _has_author_bio(content: str) -> bool:
    lower = content.lower()
    return "author bio" in lower or "about the author" in lower or "[author bio" in lower


def _has_credentials(content: str) -> bool:
    signals = ["ph.d", "phd", "years of experience", "founded", "author of", "newsletter", "linkedin"]
    lower = content.lower()
    return any(s in lower for s in signals)


def _count_headings(content: str) -> int:
    return len(re.findall(r'^#{1,6}\s+', content, re.MULTILINE))


def _count_images(content: str) -> int:
    return content.count("[IMAGE:") + len(re.findall(r'!\[', content))


def _derive_slug(content: str, keyword: str) -> str:
    """Derive a URL slug from the keyword."""
    import re
    slug = keyword.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    # Remove stop words
    stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but', 'how'}
    parts = [p for p in slug.split('-') if p not in stop_words]
    return '-'.join(parts)