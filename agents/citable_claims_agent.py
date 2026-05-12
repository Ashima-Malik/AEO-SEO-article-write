"""
Agent: Citable Claims Generator
---------------------------------
Takes content + topic and generates standalone, verifiable claims
formatted for AI engine citation. Each claim is self-contained,
factually grounded, and optimized to be quoted by AI assistants.

Returns (citable_claims_result dict, AgentTokenUsage)
"""

import json
import re
import openai

from config import get_settings, OPENAI_MODEL, INPUT_COST_PER_TOKEN, OUTPUT_COST_PER_TOKEN
from models.schemas import AgentTokenUsage


CITABLE_CLAIMS_PROMPT = """You are an expert at crafting content that AI assistants (ChatGPT, Perplexity, Gemini) cite in their answers.

Citable claims must be:
- Self-contained (no "as mentioned above" or pronouns without antecedents)
- Specific and verifiable (include numbers, dates, names, sources where possible)
- Written at a reading level that AI engines parse as authoritative
- 1-3 sentences maximum
- Directly answerable (structured as an answer to a question)

TOPIC: {topic}
TARGET KEYWORDS: {keywords}

CONTENT TO ANALYZE AND ENHANCE:
{content}

Return ONLY valid JSON with this structure:
{{
  "extracted_citable_claims": [
    {{
      "claim": "<verbatim strong claim already in the content>",
      "question_it_answers": "<the question a user might ask that this answers>",
      "citation_strength": "<Strong / Medium / Weak>",
      "why_citable": "<why AI engines would cite this>"
    }}
  ],
  "generated_citable_claims": [
    {{
      "claim": "<new standalone claim based on topic + content context>",
      "question_it_answers": "<what user query this would answer>",
      "recommended_placement": "<where in article to add: intro / after H2 / FAQ / conclusion>",
      "format": "<Sentence / Statistic / Definition / How-to opener / Comparison>"
    }}
  ],
  "faq_pairs": [
    {{
      "question": "<specific, search-intent question>",
      "answer": "<direct, 2-3 sentence answer optimized for AI citation>"
    }}
  ],
  "definition_statements": [
    {{
      "term": "<key term>",
      "definition": "<clear, citable 1-sentence definition>"
    }}
  ],
  "citation_optimization_score": <0-100, how citation-ready is the current content>,
  "top_recommendations": [
    "<specific action to increase citation likelihood>"
  ]
}}

Generate exactly 5 generated_citable_claims, 4 faq_pairs, 3 definition_statements.
Extracted claims: find up to 5 from existing content. Recommendations: 3-4 items."""


def _parse_json(raw: str) -> dict:
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {}


async def run_citable_claims_agent(
    content: str,
    topic: str,
    keywords: list[str] | None = None,
) -> tuple[dict, AgentTokenUsage]:
    """
    Generate and extract citable claims from content.
    Returns (citable_claims_result, AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    kw_str = ", ".join((keywords or [])[:5]) or topic
    prompt = CITABLE_CLAIMS_PROMPT.format(
        topic=topic[:200],
        keywords=kw_str,
        content=content[:4000],
    )

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You generate citable claims for AEO. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        raw = response.choices[0].message.content or ""
        in_tok  = response.usage.prompt_tokens
        out_tok = response.usage.completion_tokens
    except Exception as e:
        print(f"[CitableClaimsAgent] API error: {e}")
        raw = ""
        in_tok, out_tok = 0, 0

    parsed = _parse_json(raw)

    result = {
        "extracted_citable_claims":  parsed.get("extracted_citable_claims", []),
        "generated_citable_claims":  parsed.get("generated_citable_claims", []),
        "faq_pairs":                 parsed.get("faq_pairs", []),
        "definition_statements":     parsed.get("definition_statements", []),
        "citation_optimization_score": parsed.get("citation_optimization_score", 0),
        "top_recommendations":       parsed.get("top_recommendations", []),
        "total_claims_generated":    len(parsed.get("generated_citable_claims", [])),
    }

    cost = (in_tok * INPUT_COST_PER_TOKEN) + (out_tok * OUTPUT_COST_PER_TOKEN)
    usage = AgentTokenUsage(
        agent_name="citable_claims_agent",
        input_tokens=in_tok,
        output_tokens=out_tok,
        cost_usd=round(cost, 6),
    )
    return result, usage
