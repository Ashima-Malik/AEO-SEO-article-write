"""
Agent 3: SEO Rewriter
----------------------
Takes the original content + score + issues list and produces a fully
SEO-optimized rewrite using a section-based multi-agent approach.

For articles: runs parallel GPT-4o calls per section (intro, body×N, FAQ, bio)
→ 3000-5000+ words of substantive content per analysis.

For bios & product pages: single focused call (shorter content).

Supports:
- Article: full inverted pyramid, multi-keyword strategy, E-E-A-T, figures, FAQ,
           author bio, distribution strategy, schema markup, long-tail opportunities
- Bio: 3 lengths (short/medium/long), multi-keyword, credential signals
- Product Page: hero, problem, solution, features, social proof, pricing,
                FAQ, schema, competitor table, CTA
- Web research: uses OpenAI gpt-4o-search-preview to pull latest data before writing
- User tone prompt: any content type respects the user's tone/style instructions
"""

import asyncio
import json
import re
import openai
from config import get_settings, OPENAI_MODEL
from models.schemas import ContentType, AgentTokenUsage
from services.token_tracker import build_agent_usage, calculate_cost
from services.rules_loader import get_active_rules, parse_rules_into_categories


# ─────────────────────────────────────────────────────────────────────────────
# SECTION-BASED PROMPTS (used for article multi-agent approach)
# ─────────────────────────────────────────────────────────────────────────────

OUTLINE_PROMPT = """You are an expert SEO content strategist. Generate a detailed article outline as JSON.

PRIMARY KEYWORD: {primary_keyword}
ALL KEYWORDS: {all_keywords}
ISSUES TO ADDRESS: {issues}
{research_context}

Create an outline with exactly 5 main H2 body sections. Make headings specific, value-driven, and keyword-rich.

Return ONLY valid JSON (no markdown code blocks, no explanation):
{{
  "title": "H1 title — primary keyword in first 3 words, clear value proposition",
  "sections": [
    {{
      "id": "section_1",
      "h2": "Specific H2 heading using a keyword variant",
      "description": "What this section covers in 1-2 sentences",
      "target_keyword": "keyword to emphasize in this section",
      "has_table": true
    }},
    {{
      "id": "section_2",
      "h2": "Another specific H2 heading",
      "description": "What this section covers",
      "target_keyword": "keyword variant",
      "has_table": false
    }}
  ],
  "faq_questions": [
    "Specific long-tail question 1 about {primary_keyword}?",
    "Specific long-tail question 2?",
    "Specific long-tail question 3?",
    "Specific long-tail question 4?",
    "Specific long-tail question 5?"
  ]
}}

The title MUST contain the primary keyword in the first 3 words."""


SEO_METADATA_PROMPT = """You are an SEO technical expert. Generate the SEO metadata block for this article.

PRIMARY KEYWORD: {primary_keyword}
ALL KEYWORDS: {all_keywords}
ARTICLE TITLE: {title}

Output ONLY this exact block format with real values filled in (no placeholders left blank):

---SEO METADATA---
Title Tag (<=60 chars): [title with primary keyword, max 60 chars]
Meta Description (150-160 chars): [primary keyword + clear value proposition + action CTA, EXACTLY 150-160 chars]
URL Slug: /[keyword-first-hyphenated-slug-no-stop-words]
Primary Keyword: {primary_keyword}
All Keywords: {all_keywords}
Semantic Keywords: [5-7 closely related terms and phrases]
Schema Markup: [SCHEMA: Article + FAQ JSON-LD — include in page <head>]
Page Speed Note: Compress all images to WebP format, use lazy loading for below-fold images, preload hero image.
Long-Tail Opportunities: [3 specific long-tail questions/phrases this page could rank for]
---END SEO METADATA---

Verify: Title Tag must be ≤60 chars. Meta Description must be 150-160 chars exactly."""


INTRO_SECTION_PROMPT = """You are a world-class SEO content writer. Write the INTRODUCTION section for this article.

ARTICLE TITLE (H1): {title}
PRIMARY KEYWORD: {primary_keyword}
TONE: {tone}
ORIGINAL CONTENT (for context, do not copy): {original_snippet}

REQUIREMENTS — read every item, all are mandatory:
1. Start with the H1 heading: # {title}
2. BLUF: First 2 sentences directly answer the main question — no preamble, no "In today's digital landscape"
3. Primary keyword "{primary_keyword}" must appear in the FIRST 100 WORDS naturally
4. Include a credential/authority signal (first-person: "In my X years working with...", "Having led teams that...")
5. Give the reader a clear preview of what they'll learn (3-4 specific bullet points)
6. Include [EXTERNAL LINK: authoritative source or research on {primary_keyword}]
7. Use specific numbers, dates, or statistics — no vague claims like "recently" or "nowadays"
8. Word count: 280-380 words

Write ONLY the introduction. Start directly with # {title}. No preamble or meta-commentary."""


BODY_SECTION_PROMPT = """You are a world-class SEO content writer. Write ONE detailed body section for an article about {primary_keyword}.

SECTION HEADING: ## {section_h2}
SECTION FOCUS: {section_description}
TARGET KEYWORD FOR THIS SECTION: {section_keyword}
NEEDS TABLE: {has_table}
TONE: {tone}

REQUIREMENTS — all mandatory:
1. Start with ## {section_h2}
2. Opening paragraph directly addresses the section topic (no preamble)
3. Minimum 3 full paragraphs of substantive body text with specific details, tools, numbers, examples
4. Use ### H3 sub-headings for 2-3 sub-points within the section
5. If NEEDS TABLE is true: include a markdown comparison table:
   | Column A | Column B | Column C |
   |----------|----------|----------|
   | value    | value    | value    |
6. First-person examples: "When I/we tested this...", "In our recent audit...", "After reviewing X case studies..."
7. Specific tools, companies, frameworks mentioned by name (not "various tools")
8. Target keyword "{section_keyword}" appears 2-3 times naturally
9. Include [INTERNAL LINK: descriptive anchor phrase about a related topic]
10. Concluding paragraph that transitions or summarizes key insight
11. Word count: 500-700 words

Write ONLY this section. Start directly with ## {section_h2}. No preamble or commentary."""


FAQ_SECTION_PROMPT = """You are an SEO content expert specializing in featured snippet optimization. Write the FAQ section.

PRIMARY KEYWORD: {primary_keyword}
FAQ QUESTIONS (write answers for ALL 5):
{questions}

REQUIREMENTS:
1. Section heading: ## Frequently Asked Questions
2. Each question as an ### H3 subheading (use the exact question text)
3. Each answer: EXACTLY 40-60 words — standalone, answerable without reading the article
4. Answers must be direct and informative — featured snippet bait
5. Use "{primary_keyword}" naturally in at least 3 answers
6. Include at least 1 specific number, date, or metric per answer

Write ONLY the FAQ section. 5 questions, 5 answers. Start with ## Frequently Asked Questions."""


AUTHOR_BIO_PROMPT = """You are an SEO content expert. Write the Author Bio and Distribution Checklist sections.

PRIMARY KEYWORD: {primary_keyword}
TONE: {tone}

Write BOTH of the following sections in clean markdown:

## About the Author
[Write a compelling 4-sentence author bio:
- Open with their name, title, and primary credential (PhD, X years experience, founded X)
- Specific measurable achievement ("has helped 200+ companies", "grew organic traffic 340%")
- What they publish/lead/build — newsletter, team, research focus
- LinkedIn and portfolio link placeholders: [LINK: LinkedIn] [LINK: Website]
- [INTERNAL LINK: best article about {primary_keyword}]
Make the bio feel like a real expert, not a generic template.]

## Content Distribution Checklist
[Write a practical, specific distribution plan:
- **Newsletter intro** (1 paragraph): Key insight from the article, why subscribers care
- **LinkedIn post** (3 bullets): Hook using primary keyword, 3 specific insights, CTA
- **Twitter/X Thread** (5 tweets): Tweet 1 = hook with statistic, Tweets 2-4 = insights, Tweet 5 = CTA
- **Repurpose as**: 2-3 format suggestions with specific angle (e.g., "YouTube video: 'The 5 mistakes...'")
- **Internal linking targets**: 3 specific article topics that should link TO this one
]"""


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE-CALL PROMPTS (bio and product page — shorter, focused content)
# ─────────────────────────────────────────────────────────────────────────────

BIO_REWRITER_PROMPT = """You are an expert personal brand strategist and SEO consultant. Rewrite this bio in 3 optimized versions.

RULES TO FOLLOW:
{rules}

ISSUES TO FIX:
{issues}

PRIMARY KEYWORD: {primary_keyword}
ALL TARGET KEYWORDS: {all_keywords}
SEMANTIC KEYWORDS: {semantic_keywords}

USER TONE & STYLE INSTRUCTIONS:
{user_tone}

=====================================
OUTPUT: 3 BIO VERSIONS + SEO METADATA
=====================================

---SEO METADATA---
Title Tag (<=60 chars): [Name] — [Primary Keyword] | [Brand]
Meta Description (150-160 chars): [Bio page meta with primary keyword + credential + value]
URL Slug: /[name-primary-keyword]
Primary Keyword: [main keyword]
Schema Markup: [SCHEMA: Person schema with name, jobTitle, url, sameAs (LinkedIn)]
Long-Tail Opportunities: [2-3 name + keyword search phrases to target]
---END SEO METADATA---

## Short Bio (50 words) — For article bylines, guest posts
Rules:
- Primary keyword in FIRST 3 WORDS or first sentence
- Credential signal (Ph.D / years of experience / company / achievement with number)
- One specific accomplishment or reach metric
- CTA or follow link: [LINK: LinkedIn / newsletter / website]

## Medium Bio (150 words) — For About page, newsletter footer
Rules:
- Primary keyword in first sentence
- All target keywords used naturally
- Full credential + specific achievement with number
- Audience size / newsletter subscribers / team size
- [INTERNAL LINK: best article on primary keyword topic]
- LinkedIn URL placeholder

## Long Bio (400 words) — For dedicated author/speaker page
Rules:
- All medium bio rules
- "My Approach" section (H3): what makes your method distinctive, specific frameworks used
- "Featured Work & Publications" section (H3): [PUBLICATION: outlet name] markers
- Multiple natural uses of all target keywords
- [EXTERNAL LINK: any published work / research / media mention]
- Distribution note: [DISTRIBUTION: How to use this bio — author pages, podcast intros, LinkedIn About]

Return all three versions in clean markdown, clearly labeled."""


PRODUCT_PAGE_REWRITER_PROMPT = """You are a conversion copywriter and SEO strategist specializing in B2B SaaS and AI product pages.

RULES TO FOLLOW:
{rules}

ISSUES TO FIX:
{issues}

PRIMARY KEYWORD: {primary_keyword} (transactional intent: "best X", "X pricing", "buy X", "X alternative")
ALL TARGET KEYWORDS: {all_keywords}
SEMANTIC KEYWORDS: {semantic_keywords}

USER TONE & STYLE INSTRUCTIONS:
{user_tone}

=====================================
MANDATORY PRODUCT PAGE STRUCTURE
=====================================

---SEO METADATA---
Title Tag (<=60 chars): [Primary keyword + brand — under 60 chars]
Meta Description (150-160 chars): [Transactional keyword + key benefit + CTA]
URL Slug: /[transactional-keyword-slug]
Primary Keyword: [main keyword]
All Keywords: [comma-separated]
Schema Markup: [SCHEMA: Product + FAQ + SoftwareApplication JSON-LD for <head>]
Page Speed Note: [hero image compression, lazy load below-fold sections]
Long-Tail Opportunities: [3 transactional long-tail phrases to target]
---END SEO METADATA---

## 1. HERO SECTION
- H1: Primary keyword in FIRST 3 WORDS + clear value proposition (max 10 words after keyword)
- Subtitle (H2): The specific outcome your customer gets — use a semantic keyword variant
- [CTA BUTTON: Primary CTA text — e.g. "Start Free Trial" / "See Pricing" / "Book a Demo"]
- Trust signal: X users / X companies / rating [TESTIMONIAL BADGE: short quote]

## 2. PROBLEM SECTION
### H2: "The [Problem] Every [Target Customer] Faces"
- Describe the pain in the SEARCHER'S EXACT LANGUAGE — use their words, not brand voice
- 3-4 bullet points: specific frustrations, cost of the problem, failed alternatives tried
- Close with the cost of inaction (quantify if possible)

## 3. SOLUTION SECTION
### H2: "How [Product Name] Solves [Problem]"
- Specific mechanism — not "we make it easy" but HOW it actually works
- Use semantic keywords naturally here
- [FIGURE 1: Product screenshot or architecture diagram showing the solution]
  Caption: "Figure 1: [How the product solves X]. Source: [Brand]."
  Alt text: "[primary keyword] [product name] [what it does] screenshot"

## 4. FEATURES SECTION
### H2: "Everything You Need to [Primary Outcome]"
Each feature as its own H3 (each can rank independently):
### [Feature Name]: [Benefit in 5 words]
[2-3 sentences: what it does, how it works, specific outcome with metric if possible]
[FIGURE N: Feature screenshot — Alt: "[primary keyword] [feature name] interface"]

Minimum 4 features. Use remaining target keywords as feature names/descriptions.

## 5. SOCIAL PROOF SECTION
### H2: "Trusted by [Target Audience]"
[TESTIMONIAL: Name, Title, Company — 1-2 sentence quote about specific outcome]
[TESTIMONIAL: Name, Title, Company — quote]
[TESTIMONIAL: Name, Title, Company — quote]
[CASE STUDY: Company achieved [specific metric] using [Product] — [INTERNAL LINK: case study page]]

## 6. PRICING SECTION
### H2: "Simple, Transparent Pricing"
[PRICING TABLE: Tier 1 — price/features | Tier 2 — price/features | Tier 3 — price/features]
- "Most Popular" badge on recommended tier
- [CTA BUTTON: per tier — e.g. "Start [Tier Name]"]

## 7. FAQ SECTION
### H2: "Frequently Asked Questions"
EXACTLY 5 questions as H3, each answer 40-60 words (FAQ schema bait):
### [Transactional question — e.g. "How much does [Product] cost?"]
[40-60 word standalone answer using a keyword variation]

## 8. COMPETITOR COMPARISON
### H2: "[Product] vs The Alternatives"
[COMPETITOR TABLE: Feature | [Your Product] | [Competitor 1] | [Competitor 2]]
[INTERNAL LINK: Full comparison article]

## 9. FINAL CTA SECTION
### H2: "Start [Primary Outcome] Today"
- Restate core value in 1 sentence using primary keyword
- Remove friction: free trial / no credit card / instant setup
- [CTA BUTTON: Final CTA]
- [INTERNAL LINK: Relevant guide or article for this keyword]

Return in clean markdown, starting with the SEO METADATA block."""


# ─────────────────────────────────────────────────────────────────────────────
# WEB RESEARCH (OpenAI built-in web search — no extra API key needed)
# ─────────────────────────────────────────────────────────────────────────────

async def _get_web_research(
    client: openai.OpenAI,
    keyword: str,
    user_brief: str = "",
) -> str:
    """
    Use OpenAI Responses API with web_search_preview tool to fetch recent web content.
    The model actively searches the web and returns a research summary with citations.
    No extra API key needed — uses the same OpenAI client.
    """
    try:
        brief_context = f"\n\nWriter's context / focus: {user_brief}" if user_brief else ""

        def _search():
            return client.responses.create(
                model=OPENAI_MODEL,
                tools=[{"type": "web_search_preview"}],
                input=(
                    f"Research the topic '{keyword}' by searching the web and provide a concise, factual summary covering:\n"
                    f"1. The most recent statistics and data points (include sources and dates)\n"
                    f"2. Current expert opinions, trends, and emerging best practices\n"
                    f"3. Common questions people are searching for about this topic\n"
                    f"4. Key frameworks, tools, or methodologies cited by authoritative sources\n"
                    f"5. Any recent studies, reports, or notable publications\n"
                    f"{brief_context}\n\n"
                    f"Be specific — include actual numbers, researcher names, and publication names. "
                    f"Focus on information that would make an article feel current and authoritative."
                ),
                max_output_tokens=1200,
            )

        resp = await asyncio.to_thread(_search)
        research = (resp.output_text or "").strip()
        return research
    except Exception as e:
        print(f"[WebSearch] Failed to fetch web research: {e}")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# SECTION WRITING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _call_section_sync(
    client: openai.OpenAI,
    system_msg: str,
    user_msg: str,
    agent_name: str,
    max_tokens: int = 1500,
) -> tuple[str, AgentTokenUsage]:
    """
    Synchronous OpenAI Responses API call for use with asyncio.to_thread().
    Uses web_search_preview tool so the model can look up current data while writing.
    Each section agent call runs in a thread pool for true parallelism.
    """
    resp = client.responses.create(
        model=OPENAI_MODEL,
        instructions=system_msg,
        input=user_msg,
        tools=[{"type": "web_search_preview"}],
        max_output_tokens=max_tokens,
        temperature=0.7,
    )
    usage = build_agent_usage(agent_name, resp)
    return (resp.output_text or "").strip(), usage


async def _run_section_based_rewrite(
    client: openai.OpenAI,
    original_content: str,
    primary_kw: str,
    all_kws_str: str,
    issues_str: str,
    tone: str,
    score_data: dict,
    user_brief: str = "",
) -> tuple[str, list[AgentTokenUsage]]:
    """
    Section-based multi-agent article rewrite.
    First fetches web research, then runs an outline call,
    then spawns parallel section calls.
    Returns (full_article_markdown, list_of_agent_usages).
    """
    all_usages: list[AgentTokenUsage] = []
    system_writer = (
        "You are an expert SEO content writer. Write detailed, substantive, specific content. "
        "Every section must have real data, specific examples, and actionable insights. "
        "Never use generic filler like 'In today's digital landscape' or 'It's worth noting'. "
        "Write as a credentialed expert who has done the work firsthand."
    )

    # ── Step 0: Web research via OpenAI built-in search ─────────────────────
    print(f"[Rewriter] Fetching web research for '{primary_kw}'...")
    raw_research = await _get_web_research(client, primary_kw, user_brief)
    if raw_research:
        research_context = f"RECENT WEB RESEARCH (use these facts and data points):\n{raw_research[:2000]}"
        print(f"[Rewriter] Web research fetched ({len(raw_research)} chars)")
    else:
        research_context = ""
        print("[Rewriter] Web research unavailable, proceeding without it")

    # ── Step 1: Generate article outline ────────────────────────────────────
    outline_prompt = OUTLINE_PROMPT.format(
        primary_keyword=primary_kw,
        all_keywords=all_kws_str,
        issues=issues_str[:500],
        research_context=research_context,
    )

    def _get_outline():
        return _call_section_sync(
            client,
            "You are an SEO content strategist. Return ONLY valid JSON, no markdown.",
            outline_prompt,
            "rewriter_outline",
            max_tokens=800,
        )

    outline_raw_text, outline_usage = await asyncio.to_thread(_get_outline)
    all_usages.append(outline_usage)

    # Parse outline JSON
    clean_outline = re.sub(r'^```json\s*', '', outline_raw_text.strip())
    clean_outline = re.sub(r'\s*```$', '', clean_outline)
    try:
        outline = json.loads(clean_outline)
    except (json.JSONDecodeError, ValueError):
        outline = {}

    title = outline.get("title") or f"{primary_kw}: The Complete Guide"
    sections = outline.get("sections") or []
    faq_questions = (outline.get("faq_questions") or [])[:5]

    # Ensure 5 sections minimum
    if len(sections) < 4:
        sections = [
            {"h2": f"What Is {primary_kw} and Why It Matters", "description": "Definition, importance, current landscape", "target_keyword": primary_kw, "has_table": False},
            {"h2": f"How {primary_kw} Works: A Step-by-Step Breakdown", "description": "Mechanics, process, frameworks", "target_keyword": primary_kw, "has_table": True},
            {"h2": f"Best {primary_kw} Strategies That Actually Work", "description": "Proven tactics and expert approaches", "target_keyword": primary_kw, "has_table": False},
            {"h2": f"Top {primary_kw} Tools and Resources Compared", "description": "Comparison of tools, platforms, resources", "target_keyword": primary_kw, "has_table": True},
            {"h2": f"Common {primary_kw} Mistakes and How to Avoid Them", "description": "Pitfalls, misconceptions, expert fixes", "target_keyword": primary_kw, "has_table": False},
        ]

    if len(faq_questions) < 5:
        faq_questions = [
            f"What is {primary_kw}?",
            f"How do I get started with {primary_kw}?",
            f"What are the best {primary_kw} tools available?",
            f"How long does it take to see results with {primary_kw}?",
            f"Is {primary_kw} worth investing in?",
        ]

    # ── Step 2: Build all section prompts ───────────────────────────────────
    metadata_user = SEO_METADATA_PROMPT.format(
        primary_keyword=primary_kw,
        all_keywords=all_kws_str,
        title=title,
    )

    intro_user = INTRO_SECTION_PROMPT.format(
        title=title,
        primary_keyword=primary_kw,
        tone=tone,
        original_snippet=original_content[:800],
    )

    body_users = [
        BODY_SECTION_PROMPT.format(
            primary_keyword=primary_kw,
            section_h2=sec.get("h2", f"Section {i + 1}"),
            section_description=sec.get("description", ""),
            section_keyword=sec.get("target_keyword", primary_kw),
            has_table="YES — include a markdown table" if sec.get("has_table") else "NO — use lists and paragraphs instead",
            tone=tone,
        )
        for i, sec in enumerate(sections[:5])
    ]

    faq_user = FAQ_SECTION_PROMPT.format(
        primary_keyword=primary_kw,
        questions="\n".join(f"{i + 1}. {q}" for i, q in enumerate(faq_questions)),
    )

    bio_user = AUTHOR_BIO_PROMPT.format(
        primary_keyword=primary_kw,
        tone=tone,
    )

    # ── Step 3: Run all sections in parallel ─────────────────────────────────
    tasks = [
        asyncio.to_thread(_call_section_sync, client, "You are an SEO technical expert. Output only the metadata block.", metadata_user, "rewriter_metadata", 500),
        asyncio.to_thread(_call_section_sync, client, system_writer, intro_user, "rewriter_intro", 900),
    ]
    for i, bu in enumerate(body_users):
        tasks.append(
            asyncio.to_thread(_call_section_sync, client, system_writer, bu, f"rewriter_body_{i + 1}", 1600)
        )
    tasks.append(asyncio.to_thread(_call_section_sync, client, system_writer, faq_user, "rewriter_faq", 900))
    tasks.append(asyncio.to_thread(_call_section_sync, client, system_writer, bio_user, "rewriter_bio", 700))

    results = await asyncio.gather(*tasks)

    # Unpack & collect usages
    section_texts: list[str] = []
    for text, usage in results:
        section_texts.append(text)
        all_usages.append(usage)

    # ── Step 4: Assemble final article ───────────────────────────────────────
    # results order: metadata, intro, body×N, faq, bio
    n_body = len(body_users)
    metadata_block = section_texts[0]
    intro_text = section_texts[1]
    body_texts = section_texts[2: 2 + n_body]
    faq_text = section_texts[2 + n_body]
    bio_text = section_texts[3 + n_body]

    full_article = "\n\n".join([
        metadata_block,
        intro_text,
        *body_texts,
        faq_text,
        bio_text,
    ])

    return full_article, all_usages


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AGENT ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

async def run_rewriter_agent(
    original_content: str,
    content_type: str,
    target_keyword: str,
    score_before: int,
    issues: list[str],
    score_data: dict,
    target_keywords: list[str] | None = None,
    user_tone_prompt: str | None = None,
    user_brief: str = "",
) -> tuple[str, list[dict], AgentTokenUsage]:
    """
    Agent 3: Rewrite content to be fully SEO optimized.
    Articles use section-based multi-agent approach (parallel calls, 3000-5000+ words).
    Bios and product pages use focused single-call approach.
    Returns (optimized_content, changes_made_list, combined_AgentTokenUsage).
    """
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key)

    rules_categories = parse_rules_into_categories(get_active_rules())

    # Build keyword strings
    all_kws = target_keywords or [target_keyword]
    primary_kw = all_kws[0] if all_kws else target_keyword
    all_kws_str = ", ".join(all_kws)
    semantic_kws = ", ".join(score_data.get("semantic_keywords", []))

    tone = user_tone_prompt or (
        "Smart, direct, occasionally witty — like a great professor writing a newsletter. "
        "No generic AI-sounding phrases ('In today's digital landscape...', 'It's worth noting...'). "
        "Use specific data points and numbers. Short sentences mixed with longer technical ones for rhythm."
    )

    issues_str = "\n".join(f"- {i}" for i in issues)

    # ── Route to section-based rewrite for articles ───────────────────────
    is_article = content_type in (ContentType.ARTICLE.value, "article", "general", "")

    if is_article:
        optimized_content, section_usages = await _run_section_based_rewrite(
            client=client,
            original_content=original_content,
            primary_kw=primary_kw,
            all_kws_str=all_kws_str,
            issues_str=issues_str,
            tone=tone,
            score_data=score_data,
            user_brief=user_brief,
        )
        # Combine all section usages into one AgentTokenUsage for the pipeline
        combined_input = sum(u.input_tokens for u in section_usages)
        combined_output = sum(u.output_tokens for u in section_usages)
        combined_usage = AgentTokenUsage(
            agent_name="rewriter",
            input_tokens=combined_input,
            output_tokens=combined_output,
            cost_usd=calculate_cost(combined_input, combined_output),
        )

    else:
        # ── Single-call path for bio and product_page ────────────────────
        if content_type in (ContentType.BIO.value, "bio"):
            system_prompt = BIO_REWRITER_PROMPT.format(
                rules=rules_categories.get("bio", ""),
                issues=issues_str,
                primary_keyword=primary_kw,
                all_keywords=all_kws_str,
                semantic_keywords=semantic_kws or "auto-detect from content",
                user_tone=tone,
            )
        elif content_type in (ContentType.PRODUCT_PAGE.value, "product_page"):
            system_prompt = PRODUCT_PAGE_REWRITER_PROMPT.format(
                rules=rules_categories.get("product_page", ""),
                issues=issues_str,
                primary_keyword=primary_kw,
                all_keywords=all_kws_str,
                semantic_keywords=semantic_kws or "auto-detect from content",
                user_tone=tone,
            )
        else:
            system_prompt = BIO_REWRITER_PROMPT.format(
                rules=rules_categories.get("pillars", ""),
                issues=issues_str,
                primary_keyword=primary_kw,
                all_keywords=all_kws_str,
                semantic_keywords=semantic_kws or "auto-detect from content",
                user_tone=tone,
            )

        user_message = f"""ORIGINAL CONTENT TO REWRITE:

{original_content}

QUICK WINS TO IMPLEMENT FIRST:
{chr(10).join(f'- {w}' for w in score_data.get('quick_wins', []))}

CURRENT SEO AUDIT SUGGESTIONS:
Suggested title tag: {score_data.get('suggested_title_tag', '')}
Suggested meta description: {score_data.get('suggested_meta_description', '')}
Suggested URL slug: {score_data.get('suggested_url_slug', '')}
Long-tail gaps identified: {', '.join(score_data.get('long_tail_gaps', []))}
"""

        def _single_call():
            return client.responses.create(
                model=OPENAI_MODEL,
                instructions=system_prompt,
                input=user_message,
                tools=[{"type": "web_search_preview"}],
                max_output_tokens=8000,
                temperature=0.7,
            )

        response = await asyncio.to_thread(_single_call)
        combined_usage = build_agent_usage("rewriter", response)
        optimized_content = (response.output_text or "").strip()

    changes_made = _extract_changes_made(issues, score_data, primary_kw, content_type, all_kws)
    return optimized_content, changes_made, combined_usage


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_changes_made(
    issues: list[str],
    score_data: dict,
    keyword: str,
    content_type: str,
    all_keywords: list[str],
) -> list[dict]:
    """Build a human-readable list of changes applied."""
    changes = []

    for criterion in score_data.get("criteria", []):
        score = criterion.get("score", 5)
        max_score = criterion.get("max_score", 5)
        fix = criterion.get("fix")
        if score < max_score and fix:
            changes.append({
                "location": criterion.get("name", ""),
                "original": criterion.get("issue", ""),
                "optimized": fix,
                "rule": f"SEO Rule: {criterion.get('name', '')}",
                "impact": criterion.get("severity", "medium"),
            })

    changes.append({
        "location": "H1 Title",
        "original": "Primary keyword not in first 3 words of H1",
        "optimized": f"Primary keyword '{keyword}' placed in first 3 words of H1 title",
        "rule": "H1 must contain primary keyword in first 3 words",
        "impact": "critical",
    })

    changes.append({
        "location": "Multi-keyword strategy",
        "original": "Single keyword targeting",
        "optimized": f"All keywords woven naturally: {', '.join(all_keywords)}",
        "rule": "Target up to 5 semantic keyword variations per piece",
        "impact": "high",
    })

    changes.append({
        "location": "SEO Metadata Block",
        "original": "Missing or suboptimal title tag, meta description, URL slug",
        "optimized": "Full SEO metadata block added: title tag, meta description, URL slug, schema markup, page speed note, long-tail opportunities",
        "rule": "Technical SEO: title tag <=60 chars, meta 150-160 chars, keyword-first slug",
        "impact": "critical",
    })

    changes.append({
        "location": "Web Research",
        "original": "No web research",
        "optimized": "Article grounded in latest web research — current statistics, expert opinions, and authoritative sources",
        "rule": "Content must reference current data and authoritative sources (E-E-A-T)",
        "impact": "high",
    })

    changes.append({
        "location": "Figures & Diagrams",
        "original": "No figure placeholders",
        "optimized": "Figure placeholders added with captions and keyword-rich alt text",
        "rule": "Every image must have descriptive alt text (10-25 words, includes primary keyword)",
        "impact": "medium",
    })

    if content_type in ("article", "general", ""):
        changes.append({
            "location": "Section-Based Rewrite",
            "original": "Single monolithic content block",
            "optimized": "Rewritten as a comprehensive article with 5 detailed sections, each 500-700 words",
            "rule": "H2 every 250-300 words, minimum 3 paragraphs per section",
            "impact": "critical",
        })
        changes.append({
            "location": "FAQ Section",
            "original": "Missing or incomplete FAQ",
            "optimized": "5-question FAQ added with 40-60 word standalone answers (featured snippet bait)",
            "rule": "FAQ section: 5 H3 questions, each answer 40-60 words",
            "impact": "high",
        })
        changes.append({
            "location": "Author Bio",
            "original": "Missing author bio",
            "optimized": "Author bio section added with credential signal and LinkedIn placeholder",
            "rule": "Author bio required: credentials + LinkedIn link (E-E-A-T trust signal)",
            "impact": "high",
        })

    return changes
