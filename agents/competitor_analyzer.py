"""
Agent: Competitor Analyzer
--------------------------
Fetches competitor URLs, extracts their content,
and analyzes strengths / weaknesses / gaps to inform the AI Writer.
Returns: (CompetitorAnalysisResult, AgentTokenUsage)
"""

import json
import re
import asyncio
import httpx
import openai
from bs4 import BeautifulSoup

from config import get_settings, OPENAI_MODEL
from models.schemas import (
    CompetitorArticleSummary,
    CompetitorAnalysisResult,
    AgentTokenUsage,
)
from services.token_tracker import build_agent_usage


# ── Prompt ────────────────────────────────────────────────────────────────────

COMPETITOR_SYSTEM_PROMPT = """You are an expert SEO content strategist. You will be given one competitor article's text and metadata.

Analyze it and return ONLY valid JSON with this exact structure:

{
  "title": "article title or best guess",
  "word_count": 1200,
  "main_angle": "one-sentence description of the article's core argument or angle",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
  "missing_elements": ["missing element 1", "missing element 2"],
  "has_faq": false,
  "has_figures": false,
  "eeat_level": "low|medium|high"
}

Evaluation criteria:
- strengths: What does this article do well? (depth, structure, examples, data, E-E-A-T, visuals, FAQ, unique insights)
- weaknesses: What is shallow, missing, poorly structured, lacks evidence, lacks first-person experience, etc.
- missing_elements: Specific things a reader would still want to know after reading this article
- eeat_level: "high" if strong credentials/data/citations; "medium" if some; "low" if generic or thin
- has_faq: true if the article has a visible FAQ section
- has_figures: true if the article mentions charts, diagrams, tables, or screenshots

Return ONLY valid JSON. No markdown, no explanation."""


SYNTHESIS_SYSTEM_PROMPT = """You are a senior SEO content strategist. Given multiple competitor article analyses, synthesize them into a differentiation strategy.

Return ONLY valid JSON:

{
  "common_strengths": ["what most competitors do well", "..."],
  "common_weaknesses": ["what most competitors miss", "..."],
  "content_gaps": ["topic or section none of them cover adequately", "..."],
  "differentiation_angle": "One clear sentence: how the new article should be distinctly better",
  "recommended_structure": "Introduction → Core Concept → Deep Dive → Examples → FAQ → CTA (MUST be a single plain string with sections separated by →, NOT a JSON object or dict)",
  "long_tail_opportunities": ["long-tail question or phrase 1", "question 2", "question 3"]
}

Be specific and actionable. Focus on what will make the new article clearly superior."""


# ── URL Fetching ──────────────────────────────────────────────────────────────

async def _fetch_article_text(url: str, timeout: int = 15) -> tuple[str, str]:
    """Fetch a URL and return (title, plain_text). Returns empty strings on error."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Title
            title = ""
            if soup.title:
                title = soup.title.get_text(strip=True)
            elif soup.find("h1"):
                title = soup.find("h1").get_text(strip=True)

            # Remove nav/footer/script/style noise
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            # Truncate to ~6000 chars (enough for analysis, fits in context)
            text = text[:6000]
            return title, text

    except Exception as e:
        print(f"[CompetitorAnalyzer] Failed to fetch {url}: {e}")
        return "", ""


# ── Per-article analysis ──────────────────────────────────────────────────────

async def _analyze_single_article(
    url: str,
    title: str,
    text: str,
    topic_prompt: str,
    client: openai.OpenAI,
) -> tuple[CompetitorArticleSummary | None, dict]:
    """Analyze one competitor article. Returns (summary, raw_usage_dict)."""
    if not text.strip():
        return None, {"input_tokens": 0, "output_tokens": 0}

    word_count = len(text.split())

    user_msg = f"""TOPIC THE NEW ARTICLE WILL COVER: {topic_prompt}

COMPETITOR URL: {url}
COMPETITOR TITLE: {title or 'Unknown'}
WORD COUNT (approx): {word_count}

ARTICLE TEXT (first 5000 chars):
{text[:5000]}"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=800,
        messages=[
            {"role": "system", "content": COMPETITOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    usage_dict = {
        "input_tokens": getattr(response.usage, "prompt_tokens", 0),
        "output_tokens": getattr(response.usage, "completion_tokens", 0),
    }

    try:
        data = json.loads(raw)
        summary = CompetitorArticleSummary(
            url=url,
            title=data.get("title") or title or url,
            word_count=data.get("word_count") or word_count,
            main_angle=data.get("main_angle", ""),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            missing_elements=data.get("missing_elements", []),
            has_faq=bool(data.get("has_faq", False)),
            has_figures=bool(data.get("has_figures", False)),
            eeat_level=data.get("eeat_level", "low"),
        )
        return summary, usage_dict
    except (json.JSONDecodeError, Exception) as e:
        print(f"[CompetitorAnalyzer] Parse error for {url}: {e}")
        return None, usage_dict


# ── Synthesis ─────────────────────────────────────────────────────────────────

def _synthesize_analyses(
    summaries: list[CompetitorArticleSummary],
    topic_prompt: str,
    client: openai.OpenAI,
) -> tuple[dict, dict]:
    """Synthesize all competitor summaries into a differentiation strategy."""
    summaries_text = "\n\n".join([
        f"Article {i+1}: {s.url}\n"
        f"  Angle: {s.main_angle}\n"
        f"  Strengths: {', '.join(s.strengths)}\n"
        f"  Weaknesses: {', '.join(s.weaknesses)}\n"
        f"  Missing: {', '.join(s.missing_elements)}\n"
        f"  Has FAQ: {s.has_faq} | Has Figures: {s.has_figures} | E-E-A-T: {s.eeat_level}"
        for i, s in enumerate(summaries)
    ])

    user_msg = f"""TOPIC FOR NEW ARTICLE: {topic_prompt}

COMPETITOR ANALYSES:
{summaries_text}

Synthesize these into a differentiation strategy for the new article."""

    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=SYNTHESIS_SYSTEM_PROMPT,
        input=user_msg,
        tools=[{"type": "web_search_preview"}],
        max_output_tokens=800,
    )

    raw = (response.output_text or "").strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    _in = getattr(response.usage, "input_tokens", None)
    _out = getattr(response.usage, "output_tokens", None)
    usage_dict = {
        "input_tokens": _in if _in is not None else getattr(response.usage, "prompt_tokens", 0),
        "output_tokens": _out if _out is not None else getattr(response.usage, "completion_tokens", 0),
    }

    try:
        data = json.loads(raw)
        # Coerce recommended_structure to str if LLM returned a dict/list
        rec = data.get("recommended_structure", "")
        if isinstance(rec, dict):
            data["recommended_structure"] = " → ".join(
                f"{k}: {v}" if v and str(v).strip() else k
                for k, v in rec.items()
            )
        elif isinstance(rec, list):
            data["recommended_structure"] = " → ".join(str(s) for s in rec)
        elif not isinstance(rec, str):
            data["recommended_structure"] = str(rec)
        return data, usage_dict
    except json.JSONDecodeError:
        return {
            "common_strengths": [],
            "common_weaknesses": [],
            "content_gaps": [],
            "differentiation_angle": "Write a more comprehensive, experience-backed article with FAQ and visuals.",
            "recommended_structure": "Introduction → Core Concept → Deep Dive → Examples → FAQ → CTA",
            "long_tail_opportunities": [],
        }, usage_dict


# ── Main Entry Point ──────────────────────────────────────────────────────────

async def run_competitor_analyzer_agent(
    competitor_urls: list[str],
    topic_prompt: str,
) -> tuple[CompetitorAnalysisResult, AgentTokenUsage]:
    """
    Fetch all competitor URLs, analyze each, then synthesize.
    Returns (CompetitorAnalysisResult, AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    total_input_tokens = 0
    total_output_tokens = 0

    # Step 1: Fetch all URLs in parallel
    print(f"[CompetitorAnalyzer] Fetching {len(competitor_urls)} URLs...")
    fetch_results = await asyncio.gather(
        *[_fetch_article_text(url) for url in competitor_urls],
        return_exceptions=True,
    )

    # Step 2: Analyze each article (sequential to avoid OpenAI rate limits)
    summaries: list[CompetitorArticleSummary] = []
    for url, fetch_result in zip(competitor_urls, fetch_results):
        if isinstance(fetch_result, Exception):
            print(f"[CompetitorAnalyzer] Fetch exception for {url}: {fetch_result}")
            continue
        title, text = fetch_result
        if not text:
            continue

        summary, usage = await _analyze_single_article(url, title, text, topic_prompt, client)
        total_input_tokens += usage["input_tokens"]
        total_output_tokens += usage["output_tokens"]
        if summary:
            summaries.append(summary)

    print(f"[CompetitorAnalyzer] Analyzed {len(summaries)} articles successfully.")

    # Fallback if all fetches failed
    if not summaries:
        result = CompetitorAnalysisResult(
            articles_analyzed=[],
            common_strengths=[],
            common_weaknesses=["Could not fetch competitor articles"],
            content_gaps=["All content aspects — could not analyze competitors"],
            differentiation_angle="Write a comprehensive, well-structured original article on the topic.",
            recommended_structure="Introduction → Core Concepts → Deep Dive → Examples → FAQ → CTA",
            long_tail_opportunities=[],
        )
        agent_usage = AgentTokenUsage(
            agent_name="competitor_analyzer",
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
        )
        return result, agent_usage

    # Step 3: Synthesize all analyses
    synthesis_data, synth_usage = _synthesize_analyses(summaries, topic_prompt, client)
    total_input_tokens += synth_usage["input_tokens"]
    total_output_tokens += synth_usage["output_tokens"]

    result = CompetitorAnalysisResult(
        articles_analyzed=summaries,
        common_strengths=synthesis_data.get("common_strengths", []),
        common_weaknesses=synthesis_data.get("common_weaknesses", []),
        content_gaps=synthesis_data.get("content_gaps", []),
        differentiation_angle=synthesis_data.get("differentiation_angle", ""),
        recommended_structure=synthesis_data.get("recommended_structure", ""),
        long_tail_opportunities=synthesis_data.get("long_tail_opportunities", []),
    )

    from config import INPUT_COST_PER_TOKEN, OUTPUT_COST_PER_TOKEN
    cost = (total_input_tokens * INPUT_COST_PER_TOKEN) + (total_output_tokens * OUTPUT_COST_PER_TOKEN)

    agent_usage = AgentTokenUsage(
        agent_name="competitor_analyzer",
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
        cost_usd=round(cost, 6),
    )

    return result, agent_usage
