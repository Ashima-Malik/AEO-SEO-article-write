"""
Agent: Keyword Clusterer
-------------------------
Given a topic, generates keyword clusters grouped by search intent.
Returns: (KeywordClusterResponse data dict, AgentTokenUsage)
"""

import json
import re
import openai
from config import get_settings, OPENAI_MODEL
from models.schemas import AgentTokenUsage
from services.token_tracker import build_agent_usage


KEYWORD_CLUSTERER_PROMPT = """You are an expert SEO keyword strategist. Given a topic, generate a comprehensive keyword cluster.

Return ONLY valid JSON:

{
  "primary_keyword": "the single best keyword to target (2-4 words, high intent, specific)",
  "clusters": [
    {
      "intent": "informational",
      "keywords": ["how does X work", "what is X", "X explained", "X guide", "X tutorial"],
      "rationale": "One sentence: why these keywords fit informational intent"
    },
    {
      "intent": "transactional",
      "keywords": ["best X tool", "X pricing", "buy X", "X alternative", "X vs Y"],
      "rationale": "One sentence: why these keywords fit transactional intent"
    },
    {
      "intent": "navigational",
      "keywords": ["X official docs", "X github", "X company", "X login"],
      "rationale": "One sentence: why these fit navigational intent"
    },
    {
      "intent": "long_tail",
      "keywords": ["how to implement X for Y", "X step by step for beginners", "X use cases in Z"],
      "rationale": "One sentence: why long-tail, low competition"
    }
  ],
  "paa_questions": [
    "What is X?",
    "How does X work?",
    "What are the benefits of X?",
    "How to get started with X?",
    "What are the best X tools?"
  ],
  "semantic_keywords": ["related term 1", "LSI keyword 2", "entity 3", "concept 4", "synonym 5"],
  "negative_keywords": ["too broad term 1", "competitor brand 2", "irrelevant term 3"]
}

Rules:
- Each cluster should have 5-8 keywords
- paa_questions: exactly 5 questions phrased as a user would type them
- semantic_keywords: 5-8 terms that should appear naturally in the content
- negative_keywords: 3-5 terms that are too broad, too competitive, or off-target
- All keywords must be relevant to the EXACT topic — do not drift to related topics
- No markdown, no preamble"""


async def run_keyword_clusterer(
    topic: str,
    seed_keywords: list[str] | None,
    content_type: str,
) -> tuple[dict, AgentTokenUsage]:
    """
    Generate keyword clusters for a topic.
    Returns (data_dict, AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    seed_str = f"\nSEED KEYWORDS (prioritize these): {', '.join(seed_keywords)}" if seed_keywords else ""
    user_msg = f"""TOPIC: {topic}
CONTENT TYPE: {content_type}{seed_str}

Generate a complete keyword cluster for this topic. Focus on keywords that:
1. Match the content type ({content_type})
2. Have realistic ranking potential for a new article
3. Cover the full spectrum of search intent around this topic"""

    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=KEYWORD_CLUSTERER_PROMPT,
        input=user_msg,
        tools=[{"type": "web_search_preview"}],
        max_output_tokens=1000,
    )

    usage = build_agent_usage("keyword_clusterer", response)

    raw = (response.output_text or "").strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "primary_keyword": seed_keywords[0] if seed_keywords else topic,
            "clusters": [],
            "paa_questions": [],
            "semantic_keywords": [],
            "negative_keywords": [],
        }

    return data, usage
