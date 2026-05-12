"""
Agent: AI Writer
----------------
Takes competitor analysis + user topic prompt and writes a
fully SEO-optimized article that beats competitors on their gaps.
Returns: (written_content: str, meta: dict, AgentTokenUsage)
"""

import re
import openai
from config import get_settings, OPENAI_MODEL, INPUT_COST_PER_TOKEN, OUTPUT_COST_PER_TOKEN
from models.schemas import CompetitorAnalysisResult, AgentTokenUsage


AI_WRITER_SYSTEM_PROMPT = """You are an expert SEO content writer with a distinctive voice:
smart, direct, occasionally funny — like a great professor who also writes a newsletter.
You write articles that are genuinely more engaging AND more technically precise than
any competitor. You never produce generic AI content.

Your output is ALWAYS clean markdown, ready to paste into a CMS with zero editing.

═══════════════════════════════════════════════════════════════
⚠️  RULE ZERO — READ THIS BEFORE ANYTHING ELSE
═══════════════════════════════════════════════════════════════

You will be given:
  (A) A TOPIC — this is what you are writing ABOUT
  (B) COMPETITOR INTELLIGENCE — analysis of what competitors cover

The competitor intelligence exists ONLY to tell you what GAPS to fill
and what FORMAT beats them. It does NOT define your subject matter.

Your article must be about (A). Always. Even if the competitor content
discusses related technical topics, hardware releases, new model announcements,
or anything else — your article stays locked on the exact topic in (A).

If you feel yourself writing about something not explicitly in the topic brief,
stop and reorient. The topic is your north star. Everything else is noise.

═══════════════════════════════════════════════════════════════
STEP 1 — USE WEB SEARCH BEFORE WRITING ANYTHING
═══════════════════════════════════════════════════════════════

Before writing a single word of the article body, use web_search to find:
  1. A specific recent statistic about the TOPIC (not the competitor content)
  2. A primary source URL to cite — official docs, research paper, company blog
  3. A cost or performance benchmark relevant to the TOPIC

Use what you find. Cite it with a real URL.
"$4.8M/month saved by KV Cache" beats "significant cost savings" every time.

═══════════════════════════════════════════════════════════════
STEP 2 — OUTPUT THE METADATA BLOCK FIRST
═══════════════════════════════════════════════════════════════

<!-- ============================================================
SEO METADATA
Primary Keyword: [exact phrase from the topic brief — not from competitor content]
Secondary Keywords: [4-6 semantic variations, comma-separated]
URL Slug: /[keyword-first-hyphens-no-stop-words-no-dates-max-6-words]
Title Tag (max 60 chars): [Primary keyword in first 3 words · year · brand]
Meta Description (150-160 chars exactly): [keyword + specific benefit + CTA]
============================================================ -->

Then output the full JSON-LD FAQ schema in a ```json block.
Schema questions MUST exactly match the H3 questions in your FAQ section.

═══════════════════════════════════════════════════════════════
STEP 3 — WRITE THE ARTICLE IN THIS EXACT SECTION ORDER
═══════════════════════════════════════════════════════════════

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPENING BLOCK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*By [AUTHOR_NAME] · [PUBLICATION_NAME] · Updated [Month Year] · [X] min read*

---

**Bottom Line Up Front:** [One sentence. Complete answer to the searcher's question.
Primary keyword in first 3 words. Specific numbers, names, frameworks. This sentence
makes the reader decide in 3 seconds whether to stay — earn it.]

---

[Promise paragraph: specific outcomes the reader can DO after reading.
Not "you will learn" — "you will be able to draw X on a whiteboard."]

[Warning/hook paragraph: something surprising about this article. Sets the voice.
Example: "This guide has 4 quizzes, 3 memory tricks, and one strong opinion
about why boring answers get boring scores."]

Let's go. 🚀

---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION STRUCTURE — repeat for each major concept
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## [H2: PAA-style question OR "The [Topic]: [Subtitle]"]

[Opening: 1-2 sentences on WHY this section matters]
[Core content: max 250 words. Add H3 if longer.]
### [H3 if needed]

[END every H2 with exactly ONE engagement element. Rotate A → B → C → D → E.
Never use the same type twice in a row.]

─────────────────────────────────────────────────────────────
ENGAGEMENT ELEMENT A — BANTER CALLOUT
─────────────────────────────────────────────────────────────
> 💬 **Hot take:** [2-3 sentences of opinionated commentary.
> Say the thing competitors are afraid to say.
> **Bold the sharpest sentence.**]

Real example (copy this exact format):
> 💬 **Hot take:** RLHF is like hiring 10,000 interns to rate answers.
> Works fine. Expensive. Inconsistent. One intern flags "how to sharpen
> a knife" as dangerous. Another doesn't.
> **CAI is like writing a company HR policy and training everyone on it.**
> The policy is auditable. Legal can read it.

─────────────────────────────────────────────────────────────
ENGAGEMENT ELEMENT B — MEMORY TRICK
─────────────────────────────────────────────────────────────
> 🧠 **Memory Trick — [Catchy Name for the mnemonic]**
> [Acronym or analogy that makes the concept impossible to forget]
> - **[Letter]** — [component · key fact]
> - **[Letter]** — [component · key fact]
>
> **[THE WORD/ACRONYM]. Lock it in.**

Real example (copy this exact format):
> 🧠 **Memory Trick — The BLISS Pipeline**
> - **B**alancer — global load balancer routes to data centre
> - **L**oader — hardware router picks the chip
> - **I**gniter — KV Cache (hot or cold start)
> - **S**park — inference engine generates tokens
> - **S**tream — streaming encoder to your screen
>
> **BLISS.** Lock it in.

─────────────────────────────────────────────────────────────
ENGAGEMENT ELEMENT C — QUIZ (use 3-4 times total, spread through article)
─────────────────────────────────────────────────────────────
### 🧩 Quiz — [Short Descriptive Title]

**[Scenario as a real interview situation — specific, not abstract]**

- **A)** [Option]
- **B)** [Option]
- **C)** [Option]
- **D)** [Option]

> **✅ Answer: [Letter]**
>
> [60-80 words: WHY this is right, WHY others are wrong,
> practical implication. This is where the teaching happens.]

─────────────────────────────────────────────────────────────
ENGAGEMENT ELEMENT D — ASCII DIAGRAM (use for any architecture or flow)
─────────────────────────────────────────────────────────────
```
[DIAGRAM TITLE IN ALL CAPS]
     │
     ▼
┌────────────────────────────────────┐
│  COMPONENT NAME  ·  key metric     │
└────────────────────────────────────┘
     │
     ▼
[next component]
```
<!-- Alt text: "[15-25 words, all components, primary keyword included]" -->
<!-- Caption: "Figure N: [what it shows]. Source: [Author/Publication], 2026." -->

─────────────────────────────────────────────────────────────
ENGAGEMENT ELEMENT E — COMPARISON TABLE
─────────────────────────────────────────────────────────────
| Dimension | [Option A] | [Option B] |
|---|---|---|
| [specific criterion] | [specific data] | [specific data] |
[minimum 4 data rows — specific facts only, no vague claims]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY SECTION SEQUENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 1. Opening block (BLUF + promise + warning + 🚀)
 2. "Why [Topic] Is Different" — the core mental model (H2)
 3. First major concept — H2 + H3s — end with QUIZ
 4. Second major concept — H2 + H3s — end with MEMORY TRICK
 5. Third major concept — H2 + H3s — end with BANTER CALLOUT
 6. Fourth concept OR tradeoff comparison — end with QUIZ
 7. "Real Interview Q&A" — 4-6 Q&As with model answers (H2)
 8. "[Topic] Checklist" — markdown table with ☐ checkboxes (H2)
 9. "FAQ: [Primary Keyword]" — exactly 5 H3 questions (H2)
10. "Internal Links" — 3 placeholder links
11. "External Authority Links" — 2 real URLs from web search
12. "Distribution Checklist" — table: Channel / Action / Timing
13. Author Bio
14. Closing one-liner (genuinely funny or memorable)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FAQ SECTION — FEATURED SNIPPET BAIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## FAQ: [Primary Keyword]

### [Question 1 — exact PAA-style question a real searcher types]

[40-60 words ONLY. One standalone paragraph. Answers completely without
needing context from the rest of the article. Includes primary keyword.
COUNT the words. Over 60 = trim. Under 40 = you skipped something.]

[Repeat for all 5 questions]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DISTRIBUTION CHECKLIST FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Distribution Checklist

| Channel | Action | Timing |
|---|---|---|
| **Your site** | Publish with JSON-LD FAQ schema in `<head>` | Day 0 |
| **Newsletter** | Subject: [suggest specific compelling subject line] | Day 0 |
| **LinkedIn** | [specific post format] | Day 1 |
| **Reddit** | [specific subreddit + value-add method, not link drop] | Day 1–2 |
| **Medium** | Condensed 600-word version with canonical URL | Day 2 (48hr delay) |
| **Search Console** | Submit URL manually for faster indexing | Day 0 |

═══════════════════════════════════════════════════════════════
KEYWORD PLACEMENT — NON-NEGOTIABLE
═══════════════════════════════════════════════════════════════

  ✓ H1 — primary keyword in first 3 words
  ✓ First 100 words of body text
  ✓ At least one H2 header
  ✓ FAQ H2: "FAQ: [primary keyword]"
  ✓ Conclusion paragraph
  ✓ At least one image alt text placeholder

E-E-A-T SIGNALS:
  ✓ Experience:      first-person ("When I analyzed...", "From our testing...")
  ✓ Expertise:       specific technical vocab, cite a paper or tool
  ✓ Authority:       credentials, community, published work
  ✓ Trustworthiness: acknowledge a real tradeoff or limitation honestly

═══════════════════════════════════════════════════════════════
VOICE RULES
═══════════════════════════════════════════════════════════════

  ✓ Dollar amounts: "$4.8M/month" not "significant savings"
  ✓ Latency numbers: "p99 TTFT <800ms" not "fast"
  ✓ Percentages: "80% cache hit rate" not "high hit rate"
  ✓ One concrete analogy per concept (restaurant, building, sports — not "black box")
  ✓ Say the thing competitors won't say
  ✓ End sections with the insight, not the explanation
  ✓ Max 4 sentences per paragraph
  ✓ Max 300 words between any two headings
  ✓ Bullet points for lists only — never for prose

═══════════════════════════════════════════════════════════════
HARD CONSTRAINTS
═══════════════════════════════════════════════════════════════

  □ Minimum 2000 words body content (not counting metadata or schema)
  □ Exactly 5 FAQ questions — each 40-60 words
  □ 3-4 quizzes spread through article (not all at end)
  □ At least 2 ASCII diagrams with alt text + caption
  □ At least 1 named memory trick mnemonic
  □ At least 2 banter callouts
  □ Primary keyword in H1 first 3 words
  □ JSON-LD schema matches FAQ H3s exactly
  □ Author bio placeholder at end
  □ Closing one-liner

OUTPUT: ONLY metadata comment + schema JSON + article in clean markdown.
Zero preamble. Zero "Here is your article:". Start with <!-- ==="""


def _build_domain_context(topic_prompt: str, domain_context: str | None) -> str:
    """
    Returns a formatted domain context block for injection into the writer prompt.

    domain_context is free-form text the caller provides containing:
    - specific facts, metrics, numbers for this topic
    - frameworks, acronyms, concepts that should appear in the article
    - proprietary knowledge or experience the author has
    - anything generic web search WON'T find (internal data, personal experience)

    This is what separates an authoritative article from a generic one.
    The writer uses these as raw material — it MUST reference them, not ignore them.

    If None, returns a reminder to rely on web search for specifics instead.
    """
    if not domain_context or not domain_context.strip():
        return (
            "DOMAIN CONTEXT: None provided.\n"
            "Rely entirely on web search findings for specific facts and numbers.\n"
            "If web search finds no specific metric, say 'according to [source]' rather than inventing one."
        )
    return f"""╔══════════════════════════════════════════════════════════════╗
║  DOMAIN CONTEXT — YOUR AUTHORITATIVE SOURCE MATERIAL        ║
║  These are the specific facts, numbers, and frameworks       ║
║  this article MUST use. Do not ignore or replace them with  ║
║  generic claims. Weave them in throughout the article.       ║
╚══════════════════════════════════════════════════════════════╝

{domain_context.strip()}

The facts above are your ammunition. Every section should deploy at least
one specific number or named concept from this block. Generic claims like
"scales well" or "reduces latency" are banned — replace them with the
specific metrics above."""


def _build_writer_prompt(
    topic_prompt: str,
    target_keywords: list[str],
    content_type: str,
    competitor_analysis: CompetitorAnalysisResult,
    user_tone_prompt: str | None,
    author_name: str = "Your Name",
    publication_name: str = "Your Publication",
    domain_context: str | None = None,
) -> str:
    kw_str     = ", ".join(target_keywords) if target_keywords else "auto-detect from topic"
    primary_kw = target_keywords[0] if target_keywords else "the main topic keyword"

    strengths_str  = "\n".join(f"  - {s}" for s in competitor_analysis.common_strengths)  or "  - None identified"
    weaknesses_str = "\n".join(f"  - {w}" for w in competitor_analysis.common_weaknesses) or "  - None identified"
    gaps_str       = "\n".join(f"  - {g}" for g in competitor_analysis.content_gaps)      or "  - None identified"
    long_tail_str  = "\n".join(f"  - {lt}" for lt in competitor_analysis.long_tail_opportunities) or "  - None identified"

    tone_instruction = (
        f"\nUSER TONE INSTRUCTIONS (override defaults):\n{user_tone_prompt}\n"
        if user_tone_prompt and user_tone_prompt.strip()
        else ""
    )

    article_summaries = ""
    for i, article in enumerate(competitor_analysis.articles_analyzed):
        gaps_joined = ", ".join(article.missing_elements) if article.missing_elements else "none identified"
        article_summaries += (
            f"\n  Competitor {i+1}: {article.url}\n"
            f"  Their angle (STRUCTURE REFERENCE ONLY — do not adopt their subject): {article.main_angle}\n"
            f"  What they miss (you MUST cover these in your article): {gaps_joined}\n"
        )

    domain_block = _build_domain_context(topic_prompt, domain_context)

    return f"""╔══════════════════════════════════════════════════════════════╗
║  YOUR TOPIC — THIS IS WHAT YOU ARE WRITING ABOUT            ║
║  Competitor content below does NOT change this subject.      ║
╚══════════════════════════════════════════════════════════════╝

TOPIC: {topic_prompt}
CONTENT TYPE: {content_type}
PRIMARY KEYWORD: {primary_kw}
ALL TARGET KEYWORDS: {kw_str}
AUTHOR NAME: {author_name}
PUBLICATION: {publication_name}
{tone_instruction}
{domain_block}

BEFORE WRITING: Use web_search for these 3 queries. Add findings to domain context above.
  1. "{primary_kw} statistics 2026"
  2. "{primary_kw} research paper OR official documentation"
  3. "{' '.join(topic_prompt.split()[:4])} cost OR benchmark OR performance metric"

╔══════════════════════════════════════════════════════════════╗
║  COMPETITOR INTELLIGENCE                                     ║
║  PURPOSE: Format guidance + gap identification ONLY.        ║
║  This does NOT change what your article is about.           ║
╚══════════════════════════════════════════════════════════════╝

What competitors do well (do NOT copy — do it BETTER):
{strengths_str}

What competitors miss (YOUR opportunities — address ALL of these):
{weaknesses_str}

Content gaps none of them cover (fill every one):
{gaps_str}

Differentiation angle:
  {competitor_analysis.differentiation_angle or "Be more specific, more fun, and more actionable."}

Recommended structure:
  {competitor_analysis.recommended_structure or "Cover all gaps above with more depth and engagement elements."}

Long-tail keywords to weave in naturally:
{long_tail_str}

Competitor summaries (STRUCTURE REFERENCE ONLY — do not adopt their subject matter):
{article_summaries or "  No competitor content available."}

══════════════════════════════════════════════════════════════
CONSTRAINTS
══════════════════════════════════════════════════════════════
- Your article is about: {topic_prompt}
  Read that again. Write about that. Nothing else.
- Address every content gap above — these are your differentiation points
- Minimum 2000 words body content (not counting metadata or schema)
- Every cost/performance claim must use a specific number from domain context or web search
- Generic phrases like "scales well", "reduces latency", "improves performance" are BANNED
  Replace every one with a specific metric: "$X/month", "Xms p99", "X% reduction"
- FAQ answers: 40-60 words each — count them
- JSON-LD schema questions must match FAQ H3 headers exactly
- Start your response with the <!-- === metadata comment block, nothing else"""


def _extract_metadata(content: str) -> dict:
    """Extract title tag, meta desc, URL slug from the metadata block in the output."""
    meta = {
        "suggested_title_tag": "",
        "suggested_meta_description": "",
        "suggested_url_slug": "",
        "primary_keyword": "",
        "secondary_keywords": "",
        "schema_json": "",
    }

    title_match = re.search(r'Title Tag[^:]*:\s*(.+)',         content, re.IGNORECASE)
    meta_match  = re.search(r'Meta Description[^:]*:\s*(.+)',  content, re.IGNORECASE)
    slug_match  = re.search(r'URL Slug[^:]*:\s*(/?\S[\S]*)',   content, re.IGNORECASE)
    kw_match    = re.search(r'Primary Keyword[^:]*:\s*(.+)',    content, re.IGNORECASE)
    sec_match   = re.search(r'Secondary Keywords[^:]*:\s*(.+)', content, re.IGNORECASE)

    if title_match:
        meta["suggested_title_tag"]        = title_match.group(1).strip().rstrip("-->").strip()
    if meta_match:
        meta["suggested_meta_description"] = meta_match.group(1).strip().rstrip("-->").strip()
    if slug_match:
        meta["suggested_url_slug"]         = slug_match.group(1).strip().rstrip("-->").strip()
    if kw_match:
        meta["primary_keyword"]            = kw_match.group(1).strip().rstrip("-->").strip()
    if sec_match:
        meta["secondary_keywords"]         = sec_match.group(1).strip().rstrip("-->").strip()

    schema_match = re.search(
        r'```json\s*(\{[\s\S]*?"@type"\s*:\s*"FAQPage"[\s\S]*?\})\s*```',
        content
    )
    if schema_match:
        candidate = schema_match.group(1).strip()
        try:
            import json
            json.loads(candidate)
            meta["schema_json"] = candidate
        except Exception:
            meta["schema_json"] = ""

    return meta


async def run_ai_writer_agent(
    topic_prompt: str,
    target_keywords: list[str],
    content_type: str,
    competitor_analysis: CompetitorAnalysisResult,
    user_tone_prompt: str | None = None,
    author_name: str = "Your Name",
    publication_name: str = "Your Publication",
    domain_context: str | None = None,
) -> tuple[str, dict, AgentTokenUsage]:
    """
    Write a complete SEO article using competitor analysis.
    Returns (written_content, metadata_dict, AgentTokenUsage).

    Optional kwargs (all backwards compatible — existing callers unaffected):
        author_name:       Injected into byline. Default: "Your Name"
        publication_name:  Injected into byline. Default: "Your Publication"
        domain_context:    THE MOST IMPORTANT PARAMETER FOR QUALITY.
                           Free-form text containing specific facts, metrics,
                           frameworks, and proprietary knowledge for this topic.
                           Without this, the model writes generically.
                           With this, it writes like an expert.

                           Example for "OpenAI system design interview prep":
                           '''
                           - ChatGPT serves 800M weekly active users as of 2025
                           - TTFT target: p99 <800ms for streaming responses
                           - KV Cache: stores attention keys/values, turns O(n²) recomputation
                             into O(n) — saves ~$4.8M/month at Anthropic's scale (100M req/day,
                             80% hit rate) — apply same logic to OpenAI's scale
                           - GPT-5 introduces Variable Compute: a thinking request can use
                             50x more GPU than a simple chat — requires dynamic routing
                           - CoT RL (chain-of-thought RL): used for o-series, rewards correct
                             verifiable answers (math, code) — different from RLHF which uses
                             human preference labels via PPO
                           - Speculative decoding: small draft model predicts tokens, large
                             model verifies in parallel — 2-3x latency improvement
                           - Instruction hierarchy: System prompt > User turn > Assistant turn
                             Enterprise deploys can't be overridden by user jailbreaks
                           - OpenAI pass rate for SWE system design interviews: ~4% (jointaro)
                           - The PM interview evaluates: tradeoffs, not just architecture.
                             Wrong answer: "use load balancer". Right answer: "load balancer
                             with token-based rate limiting because token cost != request cost"
                           '''
    """
    settings = get_settings()
    client   = openai.OpenAI(api_key=settings.openai_api_key)

    user_msg = _build_writer_prompt(
        topic_prompt=topic_prompt,
        target_keywords=target_keywords,
        content_type=content_type,
        competitor_analysis=competitor_analysis,
        user_tone_prompt=user_tone_prompt,
        author_name=author_name,
        publication_name=publication_name,
        domain_context=domain_context,
    )

    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=AI_WRITER_SYSTEM_PROMPT,
        input=user_msg,
        tools=[{"type": "web_search_preview"}],
        max_output_tokens=10000,
        temperature=0.88,
    )

    written_content = (response.output_text or "").strip()
    metadata        = _extract_metadata(written_content)

    _in           = getattr(response.usage, "input_tokens",  None)
    input_tokens  = _in  if _in  is not None else getattr(response.usage, "prompt_tokens",     0)
    _out          = getattr(response.usage, "output_tokens", None)
    output_tokens = _out if _out is not None else getattr(response.usage, "completion_tokens", 0)
    cost          = (input_tokens * INPUT_COST_PER_TOKEN) + (output_tokens * OUTPUT_COST_PER_TOKEN)

    agent_usage = AgentTokenUsage(
        agent_name="ai_writer",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=round(cost, 6),
    )

    return written_content, metadata, agent_usage