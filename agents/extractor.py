"""
Agent 1: Content Extractor & Classifier
Returns: (content_profile dict, AgentTokenUsage)
"""

import json
import re
import openai
from config import get_settings, OPENAI_MODEL
from models.schemas import ExtractedContent, ContentType, AgentTokenUsage
from services.token_tracker import build_agent_usage


EXTRACTOR_SYSTEM_PROMPT = """You are an expert SEO content analyst. Analyze raw content and extract structured SEO metadata.

Identify:
1. content_type: "article", "bio", "product_page", or "general"
2. primary_keywords — up to 5 keyword phrases this content targets or should target.
   - primary_keywords[0] is the MAIN keyword (highest intent, most specific)
   - primary_keywords[1-4] are secondary/semantic keywords (related terms, LSI, long-tail variations)
   - Each keyword should be a specific phrase (2-4 words), not a single generic word
   - Include long-tail variations that match search intent (e.g. "how to build AI agents", "AI product manager skills")
3. semantic_keywords — 5-8 closely related terms/phrases that should appear naturally in the content
4. long_tail_gaps — 3-5 long-tail questions/phrases this content could also rank for but currently doesn't address
5. title_tag, h1, meta_description (current values or null)
6. has_faq, has_author_bio, has_author_credentials, has_schema_markup, has_figures (true/false)
7. eeat_signals_found and eeat_signals_missing (lists)
8. keyword_in_h1, keyword_in_first_100_words, keyword_in_title (true/false — check primary keyword)
9. content_gaps (missing SEO elements) and strengths (existing ones)
10. primary_keyword_in_first_3_words_of_h1 (true/false — critical rule)

Return ONLY valid JSON. No markdown, no preamble.

{
  "content_type": "article|bio|product_page|general",
  "primary_keywords": ["main keyword", "secondary keyword 2", "semantic variation 3", "long-tail phrase 4", "related term 5"],
  "primary_keyword": "main keyword (same as primary_keywords[0])",
  "semantic_keywords": ["related term 1", "LSI phrase 2", "synonym 3", "entity 4", "concept 5"],
  "long_tail_gaps": ["question or phrase 1", "question or phrase 2", "question or phrase 3"],
  "keyword_confidence": "high|medium|low",
  "title_tag": "...",
  "h1": "...",
  "meta_description": "...",
  "has_faq": false,
  "has_author_bio": false,
  "has_author_credentials": false,
  "has_schema_markup": false,
  "has_figures": false,
  "eeat_signals_found": [],
  "eeat_signals_missing": [],
  "keyword_in_h1": false,
  "primary_keyword_in_first_3_words_of_h1": false,
  "keyword_in_first_100_words": false,
  "keyword_in_title": false,
  "heading_count": 0,
  "avg_words_between_headings": 0,
  "image_count": 0,
  "images_with_alt_text": 0,
  "internal_link_count": 0,
  "external_link_count": 0,
  "word_count": 0,
  "content_gaps": [],
  "strengths": []
}"""


async def run_extractor_agent(
    extracted_content: ExtractedContent,
    target_keyword: str | None = None,
    target_keywords: list[str] | None = None,
    content_type: ContentType | None = None,
) -> tuple[dict, AgentTokenUsage]:
    """Returns (content_profile, token_usage)"""
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    # Build keyword instruction
    if target_keywords:
        kw_instruction = f"USER-PROVIDED KEYWORDS (use these as the primary_keywords basis): {', '.join(target_keywords[:5])}"
    elif target_keyword:
        kw_instruction = f"TARGET KEYWORD: {target_keyword} (detect up to 4 more related keywords automatically)"
    else:
        kw_instruction = "TARGET KEYWORDS: auto-detect up to 5 keywords from the content"

    content_summary = f"""
Title: {extracted_content.title or 'Not found'}
H1: {extracted_content.h1 or 'Not found'}
Meta Description: {extracted_content.meta_description or 'Not found'}
URL Slug: {extracted_content.url_slug or 'Not provided'}
Word Count: {extracted_content.word_count}
Heading Count: {len(extracted_content.headings)}
Image Count: {len(extracted_content.images)}
Internal Links: {len(extracted_content.internal_links)}
External Links: {len(extracted_content.external_links)}
Has FAQ: {extracted_content.has_faq}
Has Author Bio: {extracted_content.has_author_bio}

HEADINGS:
{_format_headings(extracted_content.headings)}

FULL TEXT (first 3000 chars):
{extracted_content.full_text[:3000]}

{kw_instruction}
{"CONTENT TYPE: " + content_type.value if content_type else "CONTENT TYPE: auto-detect"}
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=1200,
        messages=[
            {"role": "system", "content": EXTRACTOR_SYSTEM_PROMPT},
            {"role": "user", "content": content_summary}
        ]
    )

    # Capture token usage
    usage = build_agent_usage("extractor", response)

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    try:
        profile = json.loads(raw)
    except json.JSONDecodeError:
        profile = _build_fallback_profile(extracted_content, target_keyword, target_keywords, content_type)

    # Ensure primary_keywords is always a list
    if not profile.get("primary_keywords"):
        pk = profile.get("primary_keyword", target_keyword or "")
        profile["primary_keywords"] = [pk] if pk else []

    # If user provided keywords, inject them as primary
    if target_keywords:
        for kw in reversed(target_keywords[:5]):
            if kw not in profile["primary_keywords"]:
                profile["primary_keywords"].insert(0, kw)
        profile["primary_keywords"] = profile["primary_keywords"][:5]
        profile["primary_keyword"] = profile["primary_keywords"][0]

    # Enrich with extracted counts
    profile["word_count"] = extracted_content.word_count
    profile["internal_link_count"] = len(extracted_content.internal_links)
    profile["external_link_count"] = len(extracted_content.external_links)
    profile["image_count"] = len(extracted_content.images)
    profile["heading_count"] = len(extracted_content.headings)
    profile["headings"] = extracted_content.headings

    return profile, usage


def _format_headings(headings: list) -> str:
    if not headings:
        return "No headings found"
    return "\n".join([f"  {'#' * h['level']} {h['text']}" for h in headings[:20]])


def _build_fallback_profile(content, keyword, keywords, content_type) -> dict:
    kw = keyword or (keywords[0] if keywords else None) or (content.h1 or "").split()[0] if (content.h1 or keyword or keywords) else "unknown"
    kw_list = keywords[:5] if keywords else ([kw] if kw else [])
    return {
        "content_type": content_type.value if content_type else content.detected_content_type.value,
        "primary_keywords": kw_list,
        "primary_keyword": kw,
        "semantic_keywords": [],
        "long_tail_gaps": [],
        "keyword_confidence": "low",
        "title_tag": content.title,
        "h1": content.h1,
        "meta_description": content.meta_description,
        "has_faq": content.has_faq,
        "has_author_bio": content.has_author_bio,
        "has_author_credentials": False,
        "has_schema_markup": False,
        "has_figures": False,
        "eeat_signals_found": [],
        "eeat_signals_missing": ["experience", "expertise", "authority", "trust"],
        "keyword_in_h1": kw.lower() in (content.h1 or "").lower() if kw else False,
        "primary_keyword_in_first_3_words_of_h1": False,
        "keyword_in_first_100_words": kw.lower() in " ".join(content.full_text.split()[:100]).lower() if kw else False,
        "keyword_in_title": kw.lower() in (content.title or "").lower() if kw else False,
        "content_gaps": [],
        "strengths": [],
    }
