"""
Agent 2: SEO Scorer
--------------------
Scores the content against the exact 100-point rubric from the SEO rules document.
Uses the content profile from Agent 1 + the full SEO rules.

The 13 scoring criteria (from Section 7.1 of the SEO doc):
1. Keyword in H1 (5 pts)
2. Keyword in first 100 words (5 pts)
3. Keyword in URL slug (5 pts)
4. Title tag ≤60 chars (5 pts)
5. Meta description 155 chars (5 pts)
6. H2/H3 heading frequency (15 pts)
7. Inverted pyramid structure (10 pts)
8. E-E-A-T signals (15 pts)
9. Visual/diagram quality (10 pts)
10. FAQ section (10 pts)
11. Internal links (5 pts)
12. External authority links (5 pts)
13. Author bio present (5 pts)
"""

import json
import re
import openai
from config import get_settings, OPENAI_MODEL
from models.schemas import SEOScore, ScoringCriterion, EEATAnalysis
from services.rules_loader import get_active_rules
from services.token_tracker import build_agent_usage
from models.schemas import AgentTokenUsage


SCORER_SYSTEM_PROMPT = """You are an expert SEO auditor. You score content using a precise 100-point rubric.

You will receive:
1. A content profile (from extraction analysis)
2. The full SEO rules document
3. The content text

Apply the EXACT scoring rubric below and return a detailed score.

SCORING RUBRIC (100 points total):

| # | Criterion | Scoring Rules | Max |
|---|-----------|---------------|-----|
| 1 | Keyword in H1 | 5=exact match, 3=partial/synonym, 0=missing | 5 |
| 2 | Keyword in first 100 words | 5=natural placement, 3=forced/awkward, 0=absent | 5 |
| 3 | Keyword in URL slug | 5=exact match, 3=partial, 0=no keyword | 5 |
| 4 | Title tag (≤60 chars) | 5=keyword+year+brand under 60, 3=keyword only, 0=missing | 5 |
| 5 | Meta description (150-160 chars) | 5=keyword+CTA+value, 3=keyword only, 0=missing | 5 |
| 6 | H2/H3 heading frequency | 15=heading every <300 words, 10=some gaps, 5=few headers, 0=none | 15 |
| 7 | Inverted pyramid structure | 10=BLUF+answer-first, 5=partial, 0=buried lead | 10 |
| 8 | E-E-A-T signals | 15=all 4 signals present, 10=2-3 signals, 5=1 signal, 0=none | 15 |
| 9 | Visual/diagram quality | 10=descriptive alt text + captions, 5=images but no alt, 0=no images | 10 |
| 10 | FAQ section | 10=5 questions with 40-60 word answers, 5=present but incomplete, 0=missing | 10 |
| 11 | Internal links (min 2) | 5=2+ with descriptive anchor text, 3=2+ with generic anchors, 0=fewer than 2 | 5 |
| 12 | External authority links | 5=1-2 high-authority sources, 3=1 low-DA source, 0=none | 5 |
| 13 | Author bio | 5=full bio with credential+link, 3=name only, 0=missing | 5 |

For E-E-A-T, check all 4 signals:
- Experience: first-person language, specific outcomes with numbers, real project references
- Expertise: technical vocabulary, specific citations, deep domain knowledge
- Authority: credentials mentioned, previous publications referenced, expert quoted
- Trustworthiness: primary sources cited, updated date shown, honest about limitations

Return ONLY a valid JSON object. No markdown, no preamble.

{
  "criteria": [
    {
      "id": 1,
      "name": "Keyword in H1",
      "score": 0-5,
      "max_score": 5,
      "rating": "excellent|good|acceptable|needs_work|missing",
      "issue": "what is wrong or null if perfect",
      "fix": "exact fix to apply or null if perfect",
      "severity": "critical|high|medium|low"
    }
    ... (all 13 criteria)
  ],
  "eeat": {
    "experience_score": 0-25,
    "expertise_score": 0-25,
    "authority_score": 0-25,
    "trust_score": 0-25,
    "signals_found": ["list of found signals"],
    "signals_missing": ["list of missing signals"]
  },
  "top_issues": ["top 5 critical issues as plain strings"],
  "quick_wins": ["top 3 easiest fixes as plain strings"],
  "suggested_title_tag": "optimized title tag under 60 chars",
  "suggested_meta_description": "optimized meta description 150-160 chars",
  "suggested_url_slug": "keyword-first-slug-with-hyphens"
}"""


async def run_scorer_agent(
    content_profile: dict,
    extracted_text: str,
    content_type: str
) -> tuple[SEOScore, dict, AgentTokenUsage]:
    """
    Agent 2: Score content against the 100-point SEO rubric.
    Returns (SEOScore model, raw_score_dict with suggestions, AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)
    seo_rules = get_active_rules()

    # Use full content — truncating to 4000 chars caused FAQs, author bios and
    # internal links (which appear at the end of articles) to score 0.
    content_for_scoring = extracted_text[:15000]

    input_payload = f"""
CONTENT PROFILE:
{json.dumps(content_profile, indent=2)}

CONTENT TYPE: {content_type}
WORD COUNT: {len(extracted_text.split())} words

FULL CONTENT TEXT (score the ENTIRE article, not just the beginning):
{content_for_scoring}

SEO RULES REFERENCE (scoring rubric section):
{_extract_scoring_section(seo_rules)}
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=2000,
        messages=[
            {"role": "system", "content": SCORER_SYSTEM_PROMPT},
            {"role": "user", "content": input_payload}
        ]
    )

    # Capture token usage immediately after API call
    usage = build_agent_usage("scorer", response)

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    try:
        score_data = json.loads(raw)
    except json.JSONDecodeError:
        score_data = _build_fallback_score(content_profile)

    return _build_seo_score(score_data), score_data, usage


def _extract_scoring_section(rules: str) -> str:
    """Extract just the scoring rubric section from the full rules."""
    lines = rules.split("\n")
    in_scoring = False
    result = []
    for line in lines:
        if "section 7" in line.lower() or "100-point" in line.lower() or "scoring rubric" in line.lower():
            in_scoring = True
        if in_scoring:
            result.append(line)
            if len(result) > 60:
                break
    return "\n".join(result) if result else rules[-2000:]


def _build_seo_score(data: dict) -> SEOScore:
    """Convert raw score dict to SEOScore model."""
    criteria_list = []
    total = 0

    for c in data.get("criteria", []):
        score = c.get("score", 0)
        max_score = c.get("max_score", 5)
        total += score

        # Determine rating
        ratio = score / max_score if max_score > 0 else 0
        if ratio >= 0.9:
            rating = "excellent"
        elif ratio >= 0.7:
            rating = "good"
        elif ratio >= 0.5:
            rating = "acceptable"
        elif ratio > 0:
            rating = "needs_work"
        else:
            rating = "missing"

        # Validate severity — LLM sometimes returns unexpected values
        raw_severity = c.get("severity", "medium")
        valid_severities = {"critical", "high", "medium", "low"}
        severity = raw_severity if raw_severity in valid_severities else "medium"

        criteria_list.append(ScoringCriterion(
            name=c.get("name", "Unknown"),
            score=score,
            max_score=max_score,
            rating=rating,   # always use computed ratio-based rating, never LLM string
            issue=c.get("issue"),
            fix=c.get("fix"),
            severity=severity,
        ))

    # Override total if provided
    overall = min(100, max(0, total))

    # Rating scale from the SEO doc
    if overall >= 90:
        rating = "Excellent"
        emoji = "🏆"
        recommendation = "Publish. Promote aggressively. This can rank page 1."
    elif overall >= 80:
        rating = "Good"
        emoji = "✅"
        recommendation = "Publish with confidence. Monitor rankings for 30 days."
    elif overall >= 70:
        rating = "Acceptable"
        emoji = "🟡"
        recommendation = "Fix the top 2 issues first, then publish."
    elif overall >= 60:
        rating = "Needs Work"
        emoji = "🟠"
        recommendation = "Do not publish yet. Fix keyword placement and structure first."
    else:
        rating = "Not Ready"
        emoji = "🔴"
        recommendation = "Major rewrite required. Run the AI rewriter."

    eeat_raw = data.get("eeat", {})
    eeat = EEATAnalysis(
        experience_score=eeat_raw.get("experience_score", 0),
        expertise_score=eeat_raw.get("expertise_score", 0),
        authority_score=eeat_raw.get("authority_score", 0),
        trust_score=eeat_raw.get("trust_score", 0),
        signals_found=eeat_raw.get("signals_found", []),
        signals_missing=eeat_raw.get("signals_missing", []),
    )

    return SEOScore(
        overall=overall,
        rating=rating,
        rating_emoji=emoji,
        publish_recommendation=recommendation,
        criteria=criteria_list,
        eeat=eeat,
        top_issues=data.get("top_issues", [])[:5],
        quick_wins=data.get("quick_wins", [])[:3],
    )


def _build_fallback_score(profile: dict) -> dict:
    """Fallback score if Claude response fails to parse."""
    criteria = [
        {"name": "Keyword in H1", "score": 5 if profile.get("keyword_in_h1") else 0, "max_score": 5, "severity": "critical"},
        {"name": "Keyword in First 100 Words", "score": 5 if profile.get("keyword_in_first_100_words") else 0, "max_score": 5, "severity": "critical"},
        {"name": "Keyword in URL Slug", "score": 0, "max_score": 5, "severity": "critical"},
        {"name": "Title Tag (≤60 chars)", "score": 3 if profile.get("title_tag") else 0, "max_score": 5, "severity": "critical"},
        {"name": "Meta Description (150-160 chars)", "score": 3 if profile.get("meta_description") else 0, "max_score": 5, "severity": "high"},
        {"name": "H2/H3 Heading Frequency", "score": 10, "max_score": 15, "severity": "high"},
        {"name": "Inverted Pyramid Structure", "score": 5, "max_score": 10, "severity": "high"},
        {"name": "E-E-A-T Signals", "score": 5, "max_score": 15, "severity": "high"},
        {"name": "Visual/Diagram Quality", "score": 5 if profile.get("image_count", 0) > 0 else 0, "max_score": 10, "severity": "medium"},
        {"name": "FAQ Section", "score": 10 if profile.get("has_faq") else 0, "max_score": 10, "severity": "medium"},
        {"name": "Internal Links (min 2)", "score": 5 if profile.get("internal_link_count", 0) >= 2 else 0, "max_score": 5, "severity": "medium"},
        {"name": "External Authority Links", "score": 3 if profile.get("external_link_count", 0) > 0 else 0, "max_score": 5, "severity": "low"},
        {"name": "Author Bio", "score": 5 if profile.get("has_author_bio") else 0, "max_score": 5, "severity": "medium"},
    ]
    return {
        "criteria": criteria,
        "eeat": {"experience_score": 5, "expertise_score": 5, "authority_score": 5, "trust_score": 5,
                 "signals_found": [], "signals_missing": ["experience", "expertise", "authority", "trust"]},
        "top_issues": ["Could not fully analyze — manual review recommended"],
        "quick_wins": ["Add primary keyword to H1", "Write meta description", "Add FAQ section"],
        "suggested_title_tag": profile.get("title_tag") or "Add your optimized title here",
        "suggested_meta_description": profile.get("meta_description") or "Add your meta description here (150-160 chars)",
        "suggested_url_slug": "your-keyword-slug",
    }