"""
Agent: Entity Mapper
---------------------
Extracts named entities from content, evaluates coverage vs expected entities
for the topic, and identifies missing high-value entities.

Returns (entity_map_result dict, AgentTokenUsage)
"""

import json
import re
import openai

from config import get_settings, OPENAI_MODEL, INPUT_COST_PER_TOKEN, OUTPUT_COST_PER_TOKEN
from models.schemas import AgentTokenUsage


ENTITY_MAP_PROMPT = """You are an entity extraction and knowledge graph expert. Analyze the content and topic, then return ONLY valid JSON.

TOPIC / PRIMARY KEYWORD: {topic}

CONTENT (first 4000 chars):
{content}

Your job:
1. Extract all named entities found in the content with their type and context
2. Based on the topic, list entities that SHOULD be present but are missing
3. Score entity coverage (0-100): how well does the content cover the expected entity landscape?
4. Identify the most important missing entities that AI engines would expect

Entity types: PERSON, ORGANIZATION, PRODUCT, TECHNOLOGY, CONCEPT, PLACE, EVENT, STATISTIC, DATE

Return this exact JSON:
{{
  "entities_found": [
    {{
      "name": "<entity name>",
      "type": "<PERSON|ORGANIZATION|PRODUCT|TECHNOLOGY|CONCEPT|PLACE|EVENT|STATISTIC|DATE>",
      "context": "<1 sentence showing how it's used>",
      "clarity_score": <0-100, how clearly is this entity defined in the content>
    }}
  ],
  "entity_coverage_score": <0-100>,
  "coverage_rating": "<Comprehensive / Good / Partial / Sparse>",
  "missing_entities": [
    {{
      "name": "<entity that should be present>",
      "type": "<type>",
      "why_important": "<why AI engines expect this for the topic>",
      "suggested_addition": "<how to naturally add this to the content>"
    }}
  ],
  "entity_density": "<entities per 500 words estimate>",
  "knowledge_graph_readiness": "<High / Medium / Low — based on entity clarity and coverage>",
  "top_entity_clusters": [
    {{
      "cluster_name": "<e.g. 'Key People', 'Tools & Technologies', 'Market Stats'>",
      "entities": ["<name>", "<name>"]
    }}
  ],
  "recommendations": [
    "<specific action to improve entity coverage for AEO>"
  ]
}}

Limit entities_found to top 15 most important. Limit missing_entities to top 8. Limit recommendations to 4."""


def _parse_json(raw: str) -> dict:
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {}


async def run_entity_mapper(
    content: str,
    topic: str,
) -> tuple[dict, AgentTokenUsage]:
    """
    Map entities in content and identify coverage gaps.
    Returns (entity_map_result, AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    prompt = ENTITY_MAP_PROMPT.format(
        topic=topic[:200],
        content=content[:4000],
    )

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an entity extraction expert for AEO. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1200,
        )
        raw = response.choices[0].message.content or ""
        in_tok  = response.usage.prompt_tokens
        out_tok = response.usage.completion_tokens
    except Exception as e:
        print(f"[EntityMapper] API error: {e}")
        raw = ""
        in_tok, out_tok = 0, 0

    parsed = _parse_json(raw)

    result = {
        "entities_found": parsed.get("entities_found", []),
        "entity_count": len(parsed.get("entities_found", [])),
        "entity_coverage_score": parsed.get("entity_coverage_score", 0),
        "coverage_rating": parsed.get("coverage_rating", "Unknown"),
        "missing_entities": parsed.get("missing_entities", []),
        "entity_density": parsed.get("entity_density", ""),
        "knowledge_graph_readiness": parsed.get("knowledge_graph_readiness", "Unknown"),
        "top_entity_clusters": parsed.get("top_entity_clusters", []),
        "recommendations": parsed.get("recommendations", []),
    }

    cost = (in_tok * INPUT_COST_PER_TOKEN) + (out_tok * OUTPUT_COST_PER_TOKEN)
    usage = AgentTokenUsage(
        agent_name="entity_mapper",
        input_tokens=in_tok,
        output_tokens=out_tok,
        cost_usd=round(cost, 6),
    )
    return result, usage
