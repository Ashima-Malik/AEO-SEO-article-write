"""
Service to load and parse SEO rules from Supabase.
Rules are stored once (from your AI-SEO-Strategy-Complete.docx)
and retrieved on every analysis call.
"""

import re
from typing import Optional
from functools import lru_cache
from config import get_settings

# The full SEO rules extracted from AI-SEO-Strategy-Complete.docx
# This is the hardcoded fallback — also stored in Supabase for admin updates
DEFAULT_SEO_RULES = """
# The Complete AI SEO Strategy Rules
## Source: AI PM Insider — Ashima Malik, Ph.D — February 2026

---

## Section 1: The 6 SEO Pillars (apply to ALL content types)

### Pillar 1: Keyword Relevance (Very High Weight — Gates Discovery)
- Primary keyword must be woven naturally, NOT stuffed
- Target long-tail keywords over broad terms (long-tail converts 3-5x better)
- Keyword research should be done BEFORE writing, not after
- Use PAA (People Also Ask) box questions as H2/H3 headers
- Audit top 3 competing results and fill their content gaps

### Pillar 2: Content Structure (High Weight — Affects Featured Snippets)
- Use strict H1 > H2 > H3 hierarchy — never skip levels
- Maximum 300 words between any two headings — no wall of text
- Use inverted pyramid: answer first, prove it after
- BLUF (Bottom Line Up Front): give the answer in the first 3 sentences

### Pillar 3: E-E-A-T Signals (Very High Weight — Critical for YMYL)
- Experience: Use first-person ("When I ran this analysis..."), include specific outcomes
- Expertise: Use technical vocabulary correctly, cite specific papers/companies/people
- Authority: Link to previous published work, reference credentials in bio
- Trustworthiness: Cite primary sources, show "Updated [date]", acknowledge limitations

### Pillar 4: Technical SEO (High Weight — Table Stakes)
- Title tag: keyword + year + brand, under 60 characters
- Meta description: keyword + CTA, 150-160 characters
- URL slug: keyword-first, hyphens (not underscores), no stop words, no dates for evergreen
- Schema markup: Article schema + FAQ schema for articles; Product schema for product pages

### Pillar 5: Visual & Multimodal (Growing — 2026 Ranking Factor)
- Every image MUST have descriptive alt text (10-25 words, includes primary keyword)
- Every image MUST have a caption: "Figure N: [description]. Source: [brand], [year]."
- Alt text format: describe for a blind person AND include primary keyword
- Google can now "read" image content — label diagrams correctly

### Pillar 6: Link Ecosystem (High Weight — Domain Authority Driver)
- Minimum 2 internal links per article (up to ~8)
- Anchor text must be descriptive — never "click here"
- 1-2 external links to high-authority sources minimum
- External links only to: research papers, government sites, Tier 1 publications, official docs
- Never link to competitors or low-DA sites

---

## Section 2: Article SEO Rules

### Keyword Placement (EXACT — missing any one is a ranking signal loss)
| Placement | Rule | Priority |
|-----------|------|----------|
| H1 Title | Primary keyword in first 6 words | CRITICAL |
| URL Slug | Keyword-only, hyphens, no stop words | CRITICAL |
| First Paragraph | Keyword in first 100 words, natural | CRITICAL |
| Meta Description | Keyword + CTA, 150-160 chars | HIGH |
| First H2 | Keyword or close synonym | HIGH |
| Image Alt Text | Keyword in at least one image alt tag | MEDIUM |
| Last Paragraph | Keyword appears once near conclusion | MEDIUM |
| Title Tag | Keyword + year + brand, under 60 chars | CRITICAL |

### Article Structure — Inverted Pyramid
- Hook (0-200 words): BLUF one sentence, primary keyword, E-E-A-T credential signal, what reader will learn
- Expert Signal (200-500 words): First technical concept with specific data, table or diagram
- Core Content (500-2500 words): H2/H3 from PAA, max 300 words per section, diagram/table every 400 words
- FAQ Section (near end): 5 questions as H3 headers, each answer 40-60 words, standalone paragraph
- CTA + Author Bio (end): one clear CTA, author bio with credentials and LinkedIn, internal links

### FAQ Rules
- Exactly 5 questions as H3 headers
- Each answer: 40-60 words ONLY — this is featured snippet bait
- Each answer must be a standalone paragraph (answerable without context)

---

## Section 3: Bio SEO Rules

### Bio SEO Checklist
- Primary keyword in first sentence (e.g., "AI Product Manager", "LLM System Design")
- Credential signal: Ph.D, years of experience, company name, or specific achievement
- Publication/media mention if available (Forbes, TechCrunch, etc.)
- Audience size or reach number (newsletter subscribers, followers, users)
- At least one internal link from bio to best-performing article
- LinkedIn URL (Google uses for entity disambiguation)
- Photo alt text: "[Your Name] [Job Title]" — NOT "headshot.jpg"
- Consistent NAP: same Name, bio text, links across all platforms

### Bio Lengths
- Short bio (50 words): Article byline — prove expertise in 3 sentences
- Medium bio (150 words): About page — rank for name + expertise keyword
- Long bio (400+ words): Author page — rank for "[Name] [Title]" searches

---

## Section 4: Product Page SEO Rules

### Product Page Structure
- Hero: H1 with primary keyword + clear value prop + CTA above fold
- Problem section: Describe pain in searcher's exact language
- Solution section: Specific, not generic
- Features: Each feature as H3 (each H3 can rank independently)
- Social proof: Named testimonials with company + title
- Pricing: Transparent pricing (opaque pricing loses to competitors who show prices)
- FAQ: 5 product-specific questions, 40-60 word answers (FAQ schema)
- Competitor comparison table: captures competitor-brand searches

### Product Page Schema (Required)
- Product Schema: name, description, image, brand, offers, aggregateRating
- FAQ Schema: 5 product questions (appear as expandable Q&As in Google)
- SoftwareApplication Schema (if SaaS): applicationCategory, operatingSystem, offers

### Keyword Strategy for Product Pages
- Target transactional keywords: "best X tool", "X pricing", "buy X", "X alternative"
- NOT informational keywords (those are for articles)
- Page length: 800-1500 words (conversion wins over depth)

---

## Section 5: URL & Link SEO Rules

### URL Structure Rules
- Use keyword-first slug
- Hyphens, never underscores
- No stop words (remove: how, to, the, a, an, for, of)
- No dates for evergreen content
- Short and descriptive
- Use folder structure: /category/topic/article

### Internal Link Rules
- Minimum 2 internal links per article, up to ~8
- Anchor text must be descriptive topic phrase, never "click here" or "read more"
- Every spoke article must link back to its hub (pillar) page
- New article: immediately link to it from 3 highest-traffic existing articles
- Never orphan an article (zero internal links pointing to it)

### External Link Rules
- 1-2 external links per article minimum
- Only link to: official research papers, government sites, Tier 1 publications (NYT, FT, Nature), official product docs
- Never link to competitors, low-DA sites, or paywalled content
- Use rel=nofollow ONLY for sponsored or user-generated links, NOT genuine citations

---

## Section 7: The 100-Point SEO Scoring Rubric

| Criterion | Scoring | Max Points |
|-----------|---------|------------|
| Keyword in H1 (exact or close) | 5=exact, 3=partial, 0=missing | 5 |
| Keyword in first 100 words | 5=natural, 3=forced, 0=no | 5 |
| Keyword in URL slug | 5=exact, 3=partial, 0=no | 5 |
| Title tag (60 chars max) | 5=keyword+year+brand, 3=keyword only, 0=missing | 5 |
| Meta description (155 chars) | 5=keyword+CTA+value, 3=keyword only, 0=missing | 5 |
| H2/H3 heading frequency | 15=heading every <300 words, 10=some gaps, 0=few | 15 |
| Inverted pyramid structure | 10=BLUF+value-first, 5=partial, 0=buried lead | 10 |
| E-E-A-T signals | 15=all 4 signals, 10=2-3 signals, 0=none | 15 |
| Visual/diagram quality | 10=alt text+captions, 5=images no alt, 0=no images | 10 |
| FAQ section | 10=5 questions 40-60 words each, 5=incomplete, 0=missing | 10 |
| Internal links (min 2) | 5=2+ descriptive, 3=2+ generic, 0=less than 2 | 5 |
| External authority links | 5=1-2 high DA, 3=1 low DA, 0=none | 5 |
| Author bio present | 5=full bio+credential+link, 3=name only, 0=missing | 5 |

### Score Rating Scale
- 90-100: Excellent — Publish, promote aggressively, can rank page 1
- 80-89: Good — Publish with confidence, monitor 30 days
- 70-79: Acceptable — Fix top 2 issues first, then publish
- 60-69: Needs Work — Do not publish yet, fix keyword + structure
- Below 60: Not Ready — Major rewrite required
"""


def get_rules_from_db() -> Optional[str]:
    """Fetch active SEO rules from Supabase (skipped if supabase not installed)."""
    try:
        from supabase import create_client, Client
        settings = get_settings()
        client: Client = create_client(settings.supabase_url, settings.supabase_service_key)
        result = client.table("seo_rules").select("content").eq("is_active", True).order("created_at", desc=True).limit(1).execute()
        if result.data:
            return result.data[0]["content"]
    except Exception as e:
        print(f"[RulesLoader] Could not fetch rules from DB, using default: {e}")
    return None


def get_active_rules() -> str:
    """Get active SEO rules — from DB if available, else use hardcoded default."""
    db_rules = get_rules_from_db()
    return db_rules if db_rules else DEFAULT_SEO_RULES


def parse_rules_into_categories(rules_markdown: str) -> dict:
    """
    Parse the markdown rules into a structured dict by category.
    Used to pass focused rule subsets to each agent.
    """
    categories = {
        "pillars": "",
        "article": "",
        "bio": "",
        "product_page": "",
        "url_links": "",
        "scoring_rubric": "",
    }

    current_section = None
    lines = rules_markdown.split("\n")

    section_map = {
        "section 1": "pillars",
        "section 2": "article",
        "section 3": "bio",
        "section 4": "product_page",
        "section 5": "url_links",
        "section 7": "scoring_rubric",
        "pillar": "pillars",
        "article seo": "article",
        "bio seo": "bio",
        "product page": "product_page",
        "url": "url_links",
        "scoring": "scoring_rubric",
        "100-point": "scoring_rubric",
    }

    buffer = []
    for line in lines:
        lower = line.lower()
        matched = False
        for key, cat in section_map.items():
            if key in lower and line.startswith("#"):
                if current_section and buffer:
                    categories[current_section] += "\n".join(buffer) + "\n"
                current_section = cat
                buffer = [line]
                matched = True
                break
        if not matched:
            buffer.append(line)

    if current_section and buffer:
        categories[current_section] += "\n".join(buffer) + "\n"

    return categories
