# RankReady — AI-Powered SEO & AEO Platform

RankReady is a full-stack AI platform for SEO analysis, content optimization, and Answer Engine Optimization (AEO). It combines a FastAPI backend with a multi-agent GPT-4o pipeline and a Next.js 14 frontend.

---

## What It Does

### SEO Tools

**SEO Analyzer**
Paste text, upload a document, or provide a URL. The 5-agent pipeline analyzes the content, scores it against a 100-point SEO rubric, rewrites it with web-researched optimizations, and validates the improvement. Output includes a before/after score, tracked changes with rule citations, and a downloadable optimized document.

**Site Audit**
Enter any URL to get a structured audit of on-page SEO issues — title tags, meta descriptions, heading hierarchy, link structure, and technical signals.

**Keywords**
Enter a topic to generate a keyword cluster (primary + secondary + long-tail keywords) and a full content brief with recommended article structure, target audience, and coverage requirements.

**AI Writer**
Provide a topic, optional target keywords, optional competitor URLs, and a tone instruction. The pipeline analyzes competitor content for gaps, then writes a fully SEO-optimized article with suggested title tag, meta description, and URL slug.

**Compare**
Enter your URL and a competitor URL. The comparison agent analyzes both and identifies where the competitor outperforms you — content depth, keyword coverage, structure, and readability.

### AEO Tools (Answer Engine Optimization)

**AEO Audit**
Scores content for AI-discoverability — how likely it is to be cited by ChatGPT, Perplexity, or Google AI Overviews. Covers fact density, entity clarity, question-answer structure, and source credibility signals.

**Citation Tracker**
Analyze a URL for citation potential. Identifies which claims are citable, which entities are well-defined, and what's missing for AI engines to confidently reference the content.

**Query Planner**
Given a topic and optional keywords, generates a structured plan of the queries users ask AI engines — mapped to content types, intent clusters, and recommended answer formats.

---

## Architecture

```
rankready/
├── main.py                      # FastAPI app entry point
├── config.py                    # Settings (OPENAI_API_KEY, CORS)
├── requirements.txt
├── .env                         # Local environment variables (not committed)
│
├── agents/                      # 15 GPT-4o agents
│   ├── extractor.py             # Classifies content type + detects keyword
│   ├── scorer.py                # 100-point SEO rubric scorer
│   ├── rewriter.py              # Section-based rewriter with web research
│   ├── validator.py             # Re-scores optimized content
│   ├── url_auditor.py           # URL structure + link ecosystem audit
│   ├── competitor_analyzer.py   # Fetches + analyzes competitor URLs
│   ├── ai_writer.py             # Writes SEO-optimized articles
│   ├── keyword_clusterer.py     # Keyword clustering + content brief
│   ├── comparison_agent.py      # Side-by-side URL comparison
│   ├── audit_recommender.py     # Site audit recommendations
│   ├── brief_writer.py          # Content brief generation
│   ├── aeo_scorer.py            # AEO discoverability scoring
│   ├── aeo_citation_auditor.py  # Citation potential analysis
│   ├── citable_claims_agent.py  # Identifies citable claims
│   ├── entity_mapper.py         # Entity recognition + mapping
│   ├── fact_density_auditor.py  # Fact density analysis
│   └── query_planner.py         # AI query planning
│
├── services/
│   ├── pipeline.py              # Orchestrates the 5-agent SEO pipeline
│   ├── writer_pipeline.py       # Orchestrates the AI writer pipeline
│   ├── document.py              # Extracts content from .docx, text, URL
│   ├── diff_generator.py        # Generates tracked changes between versions
│   ├── docx_writer.py           # Writes optimized .docx for download
│   ├── token_tracker.py         # Token counting + cost estimation
│   └── rules_loader.py          # Loads SEO rules (DB or local fallback)
│
├── models/
│   └── schemas.py               # All Pydantic request/response models
│
├── routers/
│   ├── analysis.py              # POST /analyze/* endpoints
│   ├── writer.py                # POST /writer/create
│   ├── compare.py               # POST /compare
│   ├── audit.py                 # POST /audit
│   ├── keywords.py              # POST /keywords/cluster, /keywords/brief
│   ├── aeo.py                   # POST /aeo/*
│   ├── editor.py                # POST /editor/*
│   ├── export.py                # GET /analyze/{id}/download
│   ├── admin.py                 # Admin rules management
│   └── billing.py               # Stripe integration (optional)
│
└── frontend/                    # Next.js 14 app
    ├── app/
    │   ├── page.tsx             # Home page
    │   ├── analyzer/            # SEO Analyzer
    │   ├── audit/               # Site Audit
    │   ├── keywords/            # Keyword Research
    │   ├── writer/              # AI Writer
    │   ├── compare/             # URL Comparison
    │   └── aeo/                 # AEO tools
    ├── components/
    │   ├── layout/              # AppLayout, TopBar, Sidebar
    │   └── ui/                  # Shared UI components
    └── lib/
        └── api.ts               # Typed API client
```

---

## The 5-Agent SEO Pipeline

```
Input (URL / text / .docx)
           │
   [Agent 1: Extractor]      Detects content type, primary keyword, structure
           │
   [Agent 2: Scorer]    ─┐   Scores against 100-point SEO rubric
   [Agent 5: URL Auditor]┘   Audits URL structure and links (parallel)
           │
   [Agent 3: Rewriter]       Section-based rewrite with live web research
           │                 (7 parallel GPT-4o calls per article)
   [Agent 4: Validator]      Re-scores optimized content, confirms improvement
           │
   Response: scores, tracked changes, optimized content, download link
```

---

## The AI Writer Pipeline

```
Input (topic + optional competitor URLs + keywords + tone)
           │
   [Competitor Analyzer]     Fetches + analyzes competitor pages for gaps
   (skipped if no URLs)
           │
   [AI Writer]               Writes full SEO-optimized article
           │
   Response: article, title tag, meta description, URL slug, agents used
```

---

## API Endpoints

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analyze/text` | Analyze pasted text |
| POST | `/analyze/url` | Analyze content from a URL |
| POST | `/analyze/document` | Upload .docx/.txt for analysis |
| GET | `/analyze/{id}` | Retrieve a previous analysis |
| GET | `/analyze/history/all` | Paginated analysis history |
| GET | `/analyze/{id}/download` | Download optimized .docx |

### SEO Tools
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/writer/create` | Write an SEO-optimized article |
| POST | `/compare` | Compare two URLs |
| POST | `/audit` | Run a site audit |
| POST | `/keywords/cluster` | Generate keyword cluster |
| POST | `/keywords/brief` | Generate content brief |

### AEO Tools
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/aeo/full-audit` | Full AEO audit |
| POST | `/aeo/score` | AEO discoverability score |
| POST | `/aeo/citation-audit` | Citation potential analysis |
| POST | `/aeo/citable-claims` | Extract citable claims |
| POST | `/aeo/entity-map` | Entity mapping |
| POST | `/aeo/fact-density` | Fact density analysis |
| POST | `/aeo/query-plan` | AI query planning |

---

## Setup

### Requirements
- Python 3.10+
- Node.js 18+
- OpenAI API key

### Backend

```bash
cd seo
python -m venv myenv
source myenv/bin/activate        # Windows: myenv\Scripts\activate
pip install -r requirements.txt
```

Create `.env`:
```
OPENAI_API_KEY=your_key_here
```

Start the server:
```bash
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at: http://localhost:3000

---

**Render:**
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add `OPENAI_API_KEY` in environment variables



## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.10) |
| AI Model | OpenAI GPT-4o / GPT-4o-search-preview |
| Frontend | Next.js 14 (App Router) |
| Styling | Inline styles + CSS modules |
| Icons | Lucide React |
| Font | Plus Jakarta Sans |


---

Built by [Ashima Malik, Ph.D](https://www.linkedin.com/in/ashima-malik-ph-d-10740711a/)
