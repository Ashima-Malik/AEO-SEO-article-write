"""
Agent: Query Planner
---------------------
Generates an AEO-optimized query plan for a topic:
- Trend data via pytrends (Google Trends)
- Search intent inference via OpenAI web search
- Content gap identification
- Prioritized query list with estimated difficulty and AI answer likelihood

Returns (query_plan_result dict, AgentTokenUsage)
"""

import json
import re
import asyncio
import openai

from config import get_settings, OPENAI_MODEL, INPUT_COST_PER_TOKEN, OUTPUT_COST_PER_TOKEN
from models.schemas import AgentTokenUsage


QUERY_PLAN_PROMPT = """You are an AEO (Answer Engine Optimization) query strategist.
Generate a comprehensive query plan for the topic below to maximize AI engine visibility.

TOPIC: {topic}
RELATED KEYWORDS: {keywords}
TREND CONTEXT: {trend_context}

Return ONLY valid JSON with this structure:
{{
  "primary_queries": [
    {{
      "query": "<exact search query>",
      "intent": "<informational|navigational|transactional|commercial>",
      "ai_answer_likelihood": "<High|Medium|Low — will AI engines answer this directly?>",
      "content_format": "<Best format: FAQ / Definition / How-To / List / Comparison / Deep-dive>",
      "difficulty": "<Easy|Medium|Hard — to rank for>",
      "why_prioritize": "<1 sentence reason>"
    }}
  ],
  "question_queries": [
    {{
      "question": "<natural language question a user would ask an AI assistant>",
      "ideal_answer_length": "<1-2 sentences / paragraph / listicle>",
      "content_gap": "<what's missing from typical content on this topic>"
    }}
  ],
  "long_tail_opportunities": [
    {{
      "query": "<specific long-tail query>",
      "monthly_trend": "<Rising|Stable|Declining — based on trend context>",
      "ai_visibility_opportunity": "<why this is underserved by AI engines>"
    }}
  ],
  "content_calendar": [
    {{
      "title": "<article title>",
      "primary_query": "<target query>",
      "format": "<article type>",
      "priority": "<High|Medium|Low>",
      "estimated_traffic_potential": "<Low|Medium|High>"
    }}
  ],
  "trend_summary": "<2-3 sentences summarizing topic trend direction and opportunities>",
  "gsc_note": "Connect Google Search Console for real search volume data. These estimates are based on AI-inferred trends.",
  "aeo_strategy": "<2-3 sentences on the AEO content strategy for this topic>"
}}

Generate: 6 primary_queries, 5 question_queries, 5 long_tail_opportunities, 4 content_calendar entries."""


def _get_pytrends_data(topic: str, keywords: list[str]) -> dict:
    """Fetch trend data from Google Trends via pytrends."""
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))

        kw_list = ([topic] + keywords)[:5]
        pytrends.build_payload(kw_list, cat=0, timeframe='today 12-m', geo='US')

        interest = pytrends.interest_over_time()
        related_queries = pytrends.related_queries()

        trend_data = {}

        if not interest.empty:
            for kw in kw_list:
                if kw in interest.columns:
                    series = interest[kw]
                    recent_avg = series[-4:].mean() if len(series) >= 4 else series.mean()
                    overall_avg = series.mean()
                    if overall_avg > 0:
                        pct_change = ((recent_avg - overall_avg) / overall_avg) * 100
                        direction = "Rising" if pct_change > 10 else ("Declining" if pct_change < -10 else "Stable")
                    else:
                        direction = "Stable"
                    trend_data[kw] = {
                        "direction": direction,
                        "recent_avg": round(float(recent_avg), 1),
                        "peak": int(series.max()),
                    }

        rising_queries = []
        for kw in kw_list[:2]:
            rq = related_queries.get(kw, {})
            rising = rq.get("rising")
            if rising is not None and not rising.empty:
                rising_queries.extend(rising["query"].head(3).tolist())

        return {
            "trends": trend_data,
            "rising_queries": rising_queries[:6],
            "data_source": "Google Trends (pytrends)",
        }

    except ImportError:
        return {"error": "pytrends not installed", "trends": {}, "rising_queries": []}
    except Exception as e:
        return {"error": str(e), "trends": {}, "rising_queries": []}


def _format_trend_context(trend_data: dict) -> str:
    if trend_data.get("error") and not trend_data.get("trends"):
        return "Trend data unavailable. Use general knowledge about topic popularity."

    lines = []
    for kw, data in trend_data.get("trends", {}).items():
        lines.append(f"- '{kw}': {data.get('direction', 'Unknown')} trend, peak interest {data.get('peak', 'N/A')}/100")
    if trend_data.get("rising_queries"):
        lines.append(f"Rising related queries: {', '.join(trend_data['rising_queries'][:4])}")
    return "\n".join(lines) if lines else "No trend data available."


def _parse_json(raw: str) -> dict:
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {}


async def run_query_planner(
    topic: str,
    keywords: list[str] | None = None,
) -> tuple[dict, AgentTokenUsage]:
    """
    Generate AEO query plan with trend data.
    Returns (query_plan_result, AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    kw_list = (keywords or [])[:5]

    # Fetch trend data in thread (pytrends is synchronous)
    trend_data = await asyncio.to_thread(_get_pytrends_data, topic, kw_list)
    trend_context = _format_trend_context(trend_data)

    prompt = QUERY_PLAN_PROMPT.format(
        topic=topic[:200],
        keywords=", ".join(kw_list) or "none provided",
        trend_context=trend_context,
    )

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an AEO query strategist. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1600,
        )
        raw = response.choices[0].message.content or ""
        in_tok  = response.usage.prompt_tokens
        out_tok = response.usage.completion_tokens
    except Exception as e:
        print(f"[QueryPlanner] API error: {e}")
        raw = ""
        in_tok, out_tok = 0, 0

    parsed = _parse_json(raw)

    result = {
        "topic": topic,
        "primary_queries":          parsed.get("primary_queries", []),
        "question_queries":         parsed.get("question_queries", []),
        "long_tail_opportunities":  parsed.get("long_tail_opportunities", []),
        "content_calendar":         parsed.get("content_calendar", []),
        "trend_summary":            parsed.get("trend_summary", ""),
        "aeo_strategy":             parsed.get("aeo_strategy", ""),
        "gsc_note":                 parsed.get("gsc_note", "Connect Google Search Console for real search volume data."),
        "trend_data":               trend_data,
        "has_real_trend_data":      bool(trend_data.get("trends")),
    }

    cost = (in_tok * INPUT_COST_PER_TOKEN) + (out_tok * OUTPUT_COST_PER_TOKEN)
    usage = AgentTokenUsage(
        agent_name="query_planner",
        input_tokens=in_tok,
        output_tokens=out_tok,
        cost_usd=round(cost, 6),
    )
    return result, usage
