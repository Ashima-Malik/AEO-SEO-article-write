"""
Agent: AEO Citation Auditor
-----------------------------
Queries OpenAI web search for each target keyword and checks whether the
user's domain appears in the cited sources — exactly what Jasper calls
"Citation tracking in AI Overviews."

Flow per keyword:
  1. Ask OpenAI (with web_search_preview) the keyword as a real user would
  2. Extract cited URLs from response.output annotations
  3. Check if user_domain appears
  4. For gaps: surface competing cited domains

Returns (audit_result dict, AgentTokenUsage)
"""

import re
import asyncio
from urllib.parse import urlparse
import openai

from config import get_settings, OPENAI_MODEL, INPUT_COST_PER_TOKEN, OUTPUT_COST_PER_TOKEN
from models.schemas import AgentTokenUsage


def _extract_domain(url: str) -> str:
    try:
        domain = urlparse(url).netloc.lower()
        return domain.lstrip("www.")
    except Exception:
        return url.lower()


def _extract_cited_urls(response) -> list[dict]:
    """
    Extract cited URL + title from OpenAI Responses API output.
    Primary: response.output annotations (url_citation type)
    Fallback: regex over output_text
    """
    citations = []
    try:
        for item in (response.output or []):
            if getattr(item, "type", "") == "message":
                for content in (getattr(item, "content", []) or []):
                    for ann in (getattr(content, "annotations", []) or []):
                        if getattr(ann, "type", "") == "url_citation":
                            url = getattr(ann, "url", "")
                            if url:
                                citations.append({
                                    "url": url,
                                    "title": getattr(ann, "title", ""),
                                    "domain": _extract_domain(url),
                                })
    except Exception:
        pass

    if not citations:
        try:
            text = response.output_text or ""
            urls = re.findall(r'https?://[^\s\)\]\>\"\']+', text)
            citations = [{"url": u, "title": "", "domain": _extract_domain(u)} for u in urls[:10]]
        except Exception:
            pass

    return citations


async def _query_keyword(
    client: openai.OpenAI,
    keyword: str,
    user_domain: str,
) -> dict:
    """Query OpenAI web search for one keyword. Returns per-keyword result dict."""

    def _search():
        return client.responses.create(
            model=OPENAI_MODEL,
            tools=[{"type": "web_search_preview"}],
            input=keyword,
            instructions=(
                "Answer this query thoroughly, citing the most authoritative and relevant "
                "web sources. Prefer recent, specific, evidence-backed content."
            ),
            max_output_tokens=800,
        )

    try:
        response = await asyncio.to_thread(_search)
        citations = _extract_cited_urls(response)

        cited_domains = [c["domain"] for c in citations]
        is_cited = user_domain in cited_domains or any(
            user_domain in d for d in cited_domains
        )

        in_tok = getattr(response.usage, "input_tokens", None) or getattr(response.usage, "prompt_tokens", 0)
        out_tok = getattr(response.usage, "output_tokens", None) or getattr(response.usage, "completion_tokens", 0)

        return {
            "keyword": keyword,
            "cited": is_cited,
            "cited_sources": citations[:6],
            "answer_snippet": (response.output_text or "")[:500],
            "input_tokens": in_tok,
            "output_tokens": out_tok,
        }
    except Exception as e:
        print(f"[AEOCitationAuditor] Failed for '{keyword}': {e}")
        return {
            "keyword": keyword,
            "cited": False,
            "cited_sources": [],
            "answer_snippet": "",
            "error": str(e),
            "input_tokens": 0,
            "output_tokens": 0,
        }


async def run_aeo_citation_auditor(
    user_url: str,
    keywords: list[str],
) -> tuple[dict, AgentTokenUsage]:
    """
    Check if user's domain is cited by ChatGPT for each keyword.
    Runs all keyword queries in parallel.
    Returns (audit_result, AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)
    user_domain = _extract_domain(user_url)

    tasks = [_query_keyword(client, kw, user_domain) for kw in keywords[:5]]
    results = await asyncio.gather(*tasks)

    total_in  = sum(r.get("input_tokens",  0) for r in results)
    total_out = sum(r.get("output_tokens", 0) for r in results)

    cited_count = sum(1 for r in results if r.get("cited"))
    citation_rate = cited_count / len(results) if results else 0.0

    gaps = [
        {
            "keyword": r["keyword"],
            "competing_sources": r.get("cited_sources", []),
            "answer_snippet": r.get("answer_snippet", ""),
            "why_they_win": _infer_gap_reason(r.get("cited_sources", [])),
        }
        for r in results
        if not r.get("cited")
    ]

    audit_result = {
        "user_url":         user_url,
        "user_domain":      user_domain,
        "keywords_checked": len(results),
        "keywords_cited":   cited_count,
        "citation_rate":    round(citation_rate, 2),
        "citation_rate_pct": f"{round(citation_rate * 100)}%",
        "per_keyword":      results,
        "gaps":             gaps,
        "top_competing_domains": _top_domains(results, user_domain),
        "summary": (
            f"ChatGPT cites {user_domain} for {cited_count} of {len(results)} keywords "
            f"({round(citation_rate * 100)}% citation rate). "
            + ("Great AEO signal." if citation_rate >= 0.6
               else "Low citation rate — content needs AEO optimization.")
        ),
    }

    cost = (total_in * INPUT_COST_PER_TOKEN) + (total_out * OUTPUT_COST_PER_TOKEN)
    usage = AgentTokenUsage(
        agent_name="aeo_citation_auditor",
        input_tokens=total_in,
        output_tokens=total_out,
        cost_usd=round(cost, 6),
    )
    return audit_result, usage


def _top_domains(results: list[dict], exclude: str) -> list[dict]:
    freq: dict[str, int] = {}
    titles: dict[str, str] = {}
    for r in results:
        for src in r.get("cited_sources", []):
            d = src.get("domain", "")
            if d and d != exclude and exclude not in d:
                freq[d] = freq.get(d, 0) + 1
                if not titles.get(d):
                    titles[d] = src.get("title", "")
    return [
        {"domain": d, "cited_count": n, "title": titles.get(d, "")}
        for d, n in sorted(freq.items(), key=lambda x: -x[1])[:5]
    ]


def _infer_gap_reason(cited_sources: list[dict]) -> str:
    if not cited_sources:
        return "No sources found — query may not have returned results."
    domains = [s.get("domain", "") for s in cited_sources]
    high_auth = [d for d in domains if any(x in d for x in ["wikipedia", "gov", "edu", "nytimes", "reuters", "nature", "harvard"])]
    if high_auth:
        return f"High-authority sites dominating: {', '.join(high_auth[:3])}"
    return f"Competitors ranked: {', '.join(domains[:3])}. May need better E-E-A-T signals or more direct answers."
