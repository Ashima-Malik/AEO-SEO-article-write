"""
Agent: Fact Density Auditor
----------------------------
Analyzes content for factual density: facts per 500 words, fact types,
vague claim detection, and improvement suggestions.

Returns (fact_density_result dict, AgentTokenUsage)
"""

import json
import re
import openai

from config import get_settings, OPENAI_MODEL, INPUT_COST_PER_TOKEN, OUTPUT_COST_PER_TOKEN
from models.schemas import AgentTokenUsage


FACT_AUDIT_PROMPT = """You are a fact-density auditor for AI-optimized content. Analyze the content below and return ONLY valid JSON.

Your job:
1. Count and categorize verifiable facts (statistics, dates, proper nouns with context, named studies, dollar amounts, percentages, geographic facts)
2. Flag vague claims (weasel words: "many", "some", "experts say", "studies show", "significantly", "most", "often", without specifics)
3. Estimate fact density per 500 words
4. Rate each section of content
5. Suggest specific replacements for top 3 vague claims

CONTENT (first 4000 chars):
{content}

Return this exact JSON:
{{
  "word_count": <estimated word count>,
  "total_facts_found": <integer>,
  "fact_density_per_500_words": <float, round to 1 decimal>,
  "density_rating": "<one of: Excellent (8+) / Good (5-7) / Fair (3-4) / Low (<3)>",
  "fact_types": {{
    "statistics_percentages": <count>,
    "dates_timeframes": <count>,
    "named_entities_with_context": <count>,
    "dollar_amounts": <count>,
    "study_citations": <count>,
    "geographic_facts": <count>,
    "other_verifiable": <count>
  }},
  "vague_claims_found": [
    {{
      "claim": "<exact quote from content, max 20 words>",
      "issue": "<why it's vague>",
      "suggested_fix": "<concrete replacement with specifics>"
    }}
  ],
  "strongest_facts": [
    "<quote of the most credible, specific fact in the content>"
  ],
  "missing_fact_types": ["<e.g. 'market size data', 'study citations', 'specific dates'>"],
  "ai_citation_impact": "<1-2 sentences on how fact density affects AI citation likelihood>",
  "recommendations": [
    "<specific, actionable recommendation to increase fact density>"
  ]
}}

Limit vague_claims_found to top 5. Limit strongest_facts to top 3. Limit recommendations to top 4."""


def _parse_json(raw: str) -> dict:
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {}


async def run_fact_density_auditor(
    content: str,
) -> tuple[dict, AgentTokenUsage]:
    """
    Audit factual density of content.
    Returns (fact_density_result, AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    prompt = FACT_AUDIT_PROMPT.format(content=content[:4000])

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a fact-density auditor. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1000,
        )
        raw = response.choices[0].message.content or ""
        in_tok  = response.usage.prompt_tokens
        out_tok = response.usage.completion_tokens
    except Exception as e:
        print(f"[FactDensityAuditor] API error: {e}")
        raw = ""
        in_tok, out_tok = 0, 0

    parsed = _parse_json(raw)

    # Normalize density rating
    density = parsed.get("fact_density_per_500_words", 0)
    if not parsed.get("density_rating"):
        if density >= 8:
            parsed["density_rating"] = "Excellent (8+)"
        elif density >= 5:
            parsed["density_rating"] = "Good (5-7)"
        elif density >= 3:
            parsed["density_rating"] = "Fair (3-4)"
        else:
            parsed["density_rating"] = "Low (<3)"

    result = {
        "word_count": parsed.get("word_count", 0),
        "total_facts_found": parsed.get("total_facts_found", 0),
        "fact_density_per_500_words": parsed.get("fact_density_per_500_words", 0.0),
        "density_rating": parsed.get("density_rating", "Unknown"),
        "fact_types": parsed.get("fact_types", {}),
        "vague_claims_found": parsed.get("vague_claims_found", []),
        "strongest_facts": parsed.get("strongest_facts", []),
        "missing_fact_types": parsed.get("missing_fact_types", []),
        "ai_citation_impact": parsed.get("ai_citation_impact", ""),
        "recommendations": parsed.get("recommendations", []),
    }

    cost = (in_tok * INPUT_COST_PER_TOKEN) + (out_tok * OUTPUT_COST_PER_TOKEN)
    usage = AgentTokenUsage(
        agent_name="fact_density_auditor",
        input_tokens=in_tok,
        output_tokens=out_tok,
        cost_usd=round(cost, 6),
    )
    return result, usage
