"""
SEO Editor Router
------------------
Endpoints for the Word-like inline SEO editor.

POST /editor/optimize-selection  - Optimize a selected chunk of text
POST /editor/score-document      - Run a quick SEO score on the full document
POST /editor/extract-headings    - Extract headings from a URL (structure only)
"""

import asyncio
import re
import openai
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from config import get_settings, OPENAI_MODEL
from services.auth import get_current_user
from services.token_tracker import build_agent_usage

router = APIRouter(prefix="/editor", tags=["editor"])

CURRENT_YEAR = datetime.now().year


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class SelectionOptimizeRequest(BaseModel):
    selected_text: str = Field(..., description="The text the user has selected")
    document_context: str = Field("", description="Full document for context (first 2000 chars)")
    target_keyword: str = Field("", description="Primary SEO keyword")
    action: str = Field(
        "seo_optimize",
        description="Action: seo_optimize | add_keyword | make_snippet | add_eeat | fix_heading | add_links | expand"
    )
    target_keywords: Optional[list[str]] = None


class SelectionOptimizeResponse(BaseModel):
    original: str
    optimized: str
    explanation: str
    action: str
    tokens_used: int
    cost_usd: float


class QuickScoreRequest(BaseModel):
    document: str
    target_keyword: str
    target_keywords: Optional[list[str]] = None


class QuickScoreResponse(BaseModel):
    score: int
    keyword_density: float
    word_count: int
    heading_count: int
    has_faq: bool
    has_author_bio: bool
    internal_links: int
    issues: list[str]
    quick_wins: list[str]


class HeadingsRequest(BaseModel):
    url: str


class HeadingsResponse(BaseModel):
    url: str
    headings: list[dict]   # [{ level: 1, text: "..." }]
    markdown_outline: str


# ─────────────────────────────────────────────────────────────────────────────
# Action prompts
# ─────────────────────────────────────────────────────────────────────────────

ACTION_PROMPTS = {
    "seo_optimize": """You are an expert SEO editor. Rewrite the selected text to be fully SEO-optimized.

RULES:
- Primary keyword "{keyword}" must appear naturally (not stuffed)
- If this is an H1/H2: keyword must be in the first 3 words
- If this is body text: BLUF style — answer the question in the first sentence
- Remove filler phrases ("In today's world", "It's worth noting", "Needless to say")
- Add specific data points, numbers, or examples where missing
- Improve sentence rhythm: short punchy sentences + occasional longer technical ones
- Current year is {current_year} — fix any outdated year references
- Keep the same approximate length (±20%)

CONTEXT (full document excerpt):
{context}

SELECTED TEXT TO OPTIMIZE:
{selected}

Return ONLY the optimized replacement text. No explanation, no preamble.""",

    "add_keyword": """You are an SEO keyword specialist. Rewrite the selected text to naturally include the target keyword.

TARGET KEYWORD: "{keyword}"
CURRENT YEAR: {current_year}

RULES:
- Insert "{keyword}" once or twice naturally — never force it awkwardly
- Do NOT change the meaning or structure of the text
- Do NOT add the keyword if it already appears naturally
- The text must still read like a human expert wrote it
- Keep approximately the same length

CONTEXT:
{context}

SELECTED TEXT:
{selected}

Return ONLY the rewritten text with the keyword added naturally. No explanation.""",

    "make_snippet": """You are a featured snippet optimization specialist. Rewrite the selected text to win a Google featured snippet.

TARGET KEYWORD: "{keyword}"

RULES:
- Length: EXACTLY 40-60 words — count carefully
- Must be a standalone paragraph (answerable without reading the article)
- Start directly with the answer — no "According to..." or "In this article..."
- Use plain, clear language
- Include the keyword naturally in the first sentence
- No markdown formatting in the answer itself (no bullets, no bold)

SELECTED TEXT TO OPTIMIZE:
{selected}

Return ONLY the 40-60 word optimized snippet. No explanation. Count the words before responding.""",

    "add_eeat": """You are an E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) specialist.
Rewrite the selected text to add strong E-E-A-T signals.

RULES:
- Add first-person experience ("When I built...", "In my 8 years...", "After reviewing 200+ cases...")
- Add specific numbers, tools, company names — never vague claims
- Add a credential signal if appropriate ("as a certified...", "having led teams that...")
- Add a citation placeholder if claiming facts: [EXTERNAL LINK: source description]
- Keep the expert voice — this should read like a practitioner wrote it, not a copywriter
- Do NOT change the core message — enhance the authority signals only

CONTEXT:
{context}

SELECTED TEXT:
{selected}

Return ONLY the enhanced text. No explanation.""",

    "fix_heading": """You are an SEO heading specialist. Fix this heading to follow SEO best practices.

TARGET KEYWORD: "{keyword}"
CURRENT YEAR: {current_year}

RULES FOR H1:
- Primary keyword must be in the FIRST 3 WORDS
- Include {current_year} if it's a guide/tutorial/list article
- Max 60 characters (fits in title tag)
- Clear value proposition: what does the reader get?
- Example: "{keyword}: Complete {current_year} Guide for [Audience]"

RULES FOR H2/H3:
- Use a keyword variant or semantic keyword (not the exact same keyword as H1)
- Phrase as a benefit or question the section answers
- Keep under 70 characters
- Never start with "The", "A", "An" — start with the key concept

SELECTED HEADING:
{selected}

Return ONLY the optimized heading text. No #, no markdown, no explanation.""",

    "add_links": """You are an internal linking specialist. Rewrite the selected text to add descriptive link placeholders.

RULES:
- Add 1-2 [INTERNAL LINK: descriptive anchor phrase] placeholders
  Example: [INTERNAL LINK: how to write SEO title tags]
- Add 0-1 [EXTERNAL LINK: source description] if a statistic or claim needs a citation
  Example: [EXTERNAL LINK: Google's search quality guidelines]
- Anchor text must be descriptive (NEVER "click here", "read more", "here", "this article")
- Link placement must feel natural — don't interrupt a sentence mid-thought
- Keep all existing text — only add the link placeholders

CONTEXT:
{context}

SELECTED TEXT:
{selected}

Return ONLY the text with link placeholders added. No explanation.""",

    "expand": """You are an expert content writer. Expand the selected text with more detail, depth, and specificity.

TARGET KEYWORD: "{keyword}"
CURRENT YEAR: {current_year}

RULES:
- Add 1-2 more paragraphs of substantive content (specific examples, data, how-to steps, comparisons)
- Add a markdown table if comparing options, tools, or approaches
- Use concrete numbers and tool names — no vague generalities
- Maintain the same voice and expertise level as the surrounding text
- Do NOT add generic filler — every sentence must add information value
- Target length: 2-3x the original selection

CONTEXT:
{context}

SELECTED TEXT TO EXPAND:
{selected}

Return ONLY the expanded content (include the original + additions). No explanation.""",
}


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/optimize-selection", response_model=SelectionOptimizeResponse)
async def optimize_selection(
    request: SelectionOptimizeRequest,
    user: dict = Depends(get_current_user),
):
    """
    Optimize a selected chunk of text from the in-browser editor.
    Fast, targeted — only rewrites the selection, not the whole document.
    """
    if not request.selected_text.strip():
        raise HTTPException(status_code=422, detail="selected_text cannot be empty")
    if len(request.selected_text) > 5000:
        raise HTTPException(status_code=422, detail="Selection too long (max 5000 chars). Select a smaller section.")

    action = request.action
    if action not in ACTION_PROMPTS:
        action = "seo_optimize"

    keyword = request.target_keyword or (
        request.target_keywords[0] if request.target_keywords else ""
    )

    prompt = ACTION_PROMPTS[action].format(
        keyword=keyword,
        current_year=CURRENT_YEAR,
        context=request.document_context[:2000],
        selected=request.selected_text,
    )

    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    def _call():
        return client.responses.create(
            model=OPENAI_MODEL,
            instructions=(
                "You are a precise SEO editor. Follow the instructions exactly. "
                "Return ONLY the requested text — no preamble, no explanation, no meta-commentary."
            ),
            input=prompt,
            tools=[{"type": "web_search_preview"}],
            max_output_tokens=2000,
            temperature=0.6,
        )

    response = await asyncio.to_thread(_call)
    usage = build_agent_usage("editor_selection", response)
    optimized = (response.output_text or "").strip()

    # Build a short explanation based on action
    explanations = {
        "seo_optimize": f"SEO-optimized: keyword placement, BLUF structure, removed filler phrases, grounded in current web data.",
        "add_keyword": f"Added keyword '{keyword}' naturally without changing the meaning.",
        "make_snippet": "Rewritten as a 40-60 word featured snippet — standalone and directly answerable.",
        "add_eeat": "Added E-E-A-T signals: first-person experience, specific numbers, credential language.",
        "fix_heading": "Heading fixed: keyword in first 3 words, SEO-optimized.",
        "add_links": "Added descriptive internal and external link placeholders.",
        "expand": "Expanded with specific examples, data points, and additional detail.",
    }

    return SelectionOptimizeResponse(
        original=request.selected_text,
        optimized=optimized,
        explanation=explanations.get(action, "Text optimized."),
        action=action,
        tokens_used=usage.input_tokens + usage.output_tokens,
        cost_usd=usage.cost_usd,
    )


@router.post("/score-document", response_model=QuickScoreResponse)
async def score_document(
    request: QuickScoreRequest,
    user: dict = Depends(get_current_user),
):
    """
    Quick client-side SEO score for the document being edited.
    Uses rule-based checks (no LLM) — instant response.
    """
    doc = request.document
    kw = request.target_keyword.lower().strip()
    words = doc.split()
    word_count = len(words)

    # Keyword density
    kw_count = doc.lower().count(kw) if kw else 0
    density = round((kw_count / max(word_count, 1)) * 100, 2)

    # Heading count
    heading_count = len(re.findall(r'^#{1,6}\s', doc, re.MULTILINE))

    # H1 check
    h1_match = re.search(r'^#\s+(.+)$', doc, re.MULTILINE)
    h1 = h1_match.group(1).strip() if h1_match else ""
    kw_in_h1 = kw in h1.lower() if kw else False
    kw_in_first_100 = kw in " ".join(words[:100]).lower() if kw else False

    # FAQ / Author bio
    has_faq = bool(re.search(r'(faq|frequently asked|###.*\?)', doc, re.IGNORECASE))
    has_author_bio = bool(re.search(r'(about the author|author bio|\[author)', doc, re.IGNORECASE))

    # Links
    internal_links = len(re.findall(r'\[INTERNAL LINK:', doc))

    # Score calculation (rough)
    score = 50
    if kw_in_h1: score += 10
    if kw_in_first_100: score += 10
    if heading_count >= 4: score += 10
    if has_faq: score += 10
    if has_author_bio: score += 5
    if internal_links >= 2: score += 5
    if word_count >= 1000: score += 5
    if density >= 0.5 and density <= 3.0: score += 5
    score = min(score, 100)

    # Issues list
    issues = []
    quick_wins = []
    if not kw_in_h1 and kw:
        issues.append(f'H1 does not contain "{kw}" in first 3 words')
        quick_wins.append(f'Select the H1 → "Fix Heading" → adds keyword to first 3 words')
    if not kw_in_first_100 and kw:
        issues.append(f'"{kw}" not found in the first 100 words')
        quick_wins.append('Select the opening paragraph → "Add Keyword" action')
    if heading_count < 4:
        issues.append(f'Only {heading_count} headings found — need at least 4 H2s')
        quick_wins.append('Add ## H2 headings every 250-300 words')
    if not has_faq:
        issues.append('No FAQ section — missing featured snippet opportunity')
        quick_wins.append('Add a ## FAQ section with 5 H3 questions')
    if not has_author_bio:
        issues.append('No author bio — E-E-A-T signal missing')
        quick_wins.append('Add ## About the Author with credentials + LinkedIn link')
    if internal_links < 2:
        issues.append(f'Only {internal_links} internal link(s) — need at least 2')
        quick_wins.append('Select key phrases → "Add Links" to insert [INTERNAL LINK: ...] placeholders')
    if word_count < 800:
        issues.append(f'Only {word_count} words — aim for 1500+')
        quick_wins.append('Select thin sections → "Expand" to add depth')
    if density > 3.0 and kw:
        issues.append(f'Keyword density {density}% is too high (over 3%) — keyword stuffing risk')

    return QuickScoreResponse(
        score=score,
        keyword_density=density,
        word_count=word_count,
        heading_count=heading_count,
        has_faq=has_faq,
        has_author_bio=has_author_bio,
        internal_links=internal_links,
        issues=issues,
        quick_wins=quick_wins,
    )


@router.post("/extract-headings", response_model=HeadingsResponse)
async def extract_headings(
    request: HeadingsRequest,
    user: dict = Depends(get_current_user),
):
    """
    Fetch a URL and extract ONLY the heading structure (H1-H3).
    Returns headings as a list and as a markdown outline ready to paste into the editor.
    """
    import httpx
    from bs4 import BeautifulSoup

    url = request.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; SEOAnalyzer/1.0)"}
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not fetch URL: {e}")

    soup = BeautifulSoup(html, "html.parser")
    heading_tags = soup.find_all(["h1", "h2", "h3"])

    headings = []
    md_lines = []
    for tag in heading_tags:
        text = tag.get_text(strip=True)
        if not text:
            continue
        level = int(tag.name[1])
        headings.append({"level": level, "text": text})
        prefix = "#" * level
        md_lines.append(f"{prefix} {text}\n\n[Write your content here...]\n")

    if not headings:
        raise HTTPException(status_code=422, detail="No headings found on that page.")

    return HeadingsResponse(
        url=url,
        headings=headings,
        markdown_outline="\n".join(md_lines),
    )
