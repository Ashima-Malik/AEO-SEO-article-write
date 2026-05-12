"""
Agent: Content Brief Writer
----------------------------
Generates a full content brief from a keyword + context.
Returns: (brief_data dict, AgentTokenUsage)
"""

import json
import re
import openai
from config import get_settings, OPENAI_MODEL
from models.schemas import AgentTokenUsage
from services.token_tracker import build_agent_usage


BRIEF_WRITER_PROMPT = """You are a senior content strategist and SEO expert. Generate a comprehensive content brief.

Return ONLY valid JSON:

{
  "suggested_title": "H1 title with primary keyword in first 3 words, under 60 chars",
  "suggested_meta_description": "150-160 char meta: keyword + value prop + CTA",
  "suggested_url_slug": "primary-keyword-slug-no-stop-words",
  "target_word_count": 1500,
  "target_reading_level": "Professional / Intermediate",
  "content_angle": "One sentence: the unique hook or angle that makes this article different",
  "sections": [
    {
      "heading": "## H2 heading text (PAA-style question or keyword phrase)",
      "level": 2,
      "target_word_count": 300,
      "key_points": ["specific point to cover", "data or stat to include", "example to use"],
      "suggested_keywords": ["keyword to use naturally in this section"]
    }
  ],
  "faq_questions": [
    "Question 1?",
    "Question 2?",
    "Question 3?",
    "Question 4?",
    "Question 5?"
  ],
  "eeat_signals_to_include": [
    "Experience signal: e.g. 'include a first-person example of implementing this'",
    "Expertise signal: e.g. 'cite specific research paper or benchmark'",
    "Authority signal: e.g. 'mention credential or published work'",
    "Trust signal: e.g. 'acknowledge limitations and when NOT to use this approach'"
  ],
  "internal_link_suggestions": [
    "Link to: [topic] with anchor text '[descriptive phrase]'"
  ],
  "external_source_suggestions": [
    "Cite: [specific source name] for [specific claim]"
  ]
}

Rules:
- sections: 5-8 H2 sections minimum, each can have H3 sub-sections as additional items
- faq_questions: exactly 5, phrased as users type them, must be answerable in 40-60 words
- eeat_signals_to_include: exactly 4 (one per E-E-A-T dimension)
- internal_link_suggestions: 3 minimum
- external_source_suggestions: 2-3 high-authority sources (research, official docs, tier-1 publications)
- Keep concept tightly focused on the primary keyword — do not drift
- Return ONLY valid JSON"""


async def run_brief_writer(
    primary_keyword: str,
    target_keywords: list[str],
    content_type: str,
    topic_context: str | None,
) -> tuple[dict, AgentTokenUsage]:
    """
    Generate a content brief.
    Returns (brief_data, AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    kw_str = ", ".join(target_keywords) if target_keywords else primary_keyword
    context_str = f"\nADDITIONAL CONTEXT: {topic_context}" if topic_context else ""

    user_msg = f"""PRIMARY KEYWORD: {primary_keyword}
TARGET KEYWORDS: {kw_str}
CONTENT TYPE: {content_type}{context_str}

Generate a complete content brief. The brief should enable a writer to produce a high-ranking,
E-E-A-T-rich {content_type} without needing any additional research briefing."""

    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=BRIEF_WRITER_PROMPT,
        input=user_msg,
        tools=[{"type": "web_search_preview"}],
        max_output_tokens=2000,
    )

    usage = build_agent_usage("brief_writer", response)

    raw = (response.output_text or "").strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "suggested_title": f"{primary_keyword} — Complete Guide",
            "suggested_meta_description": f"Learn everything about {primary_keyword}. Expert guide with examples, tips, and actionable advice.",
            "suggested_url_slug": primary_keyword.lower().replace(" ", "-"),
            "target_word_count": 1500,
            "target_reading_level": "Professional / Intermediate",
            "content_angle": f"Practical guide to {primary_keyword} from a practitioner's perspective",
            "sections": [],
            "faq_questions": [],
            "eeat_signals_to_include": [],
            "internal_link_suggestions": [],
            "external_source_suggestions": [],
        }

    return data, usage
