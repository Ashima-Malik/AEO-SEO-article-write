# SEO Analyzer — Python FastAPI Backend

AI-powered SEO analysis engine using a 5-agent pipeline built on Claude.

---

## Architecture

```
seo-backend/
├── main.py                     # FastAPI app entry point
├── config.py                   # Settings, env vars, tier limits
├── requirements.txt
├── .env.example                # Copy to .env and fill in
├── supabase_schema.sql         # Run this in Supabase SQL Editor
│
├── agents/                     # The 5 AI agents
│   ├── extractor.py            # Agent 1: Parse + classify content
│   ├── scorer.py               # Agent 2: 100-point SEO score
│   ├── rewriter.py             # Agent 3: Optimize content
│   ├── validator.py            # Agent 4: Re-score optimized version
│   └── url_auditor.py          # Agent 5: URL + link audit
│
├── services/                   # Supporting services
│   ├── pipeline.py             # Orchestrates all 5 agents
│   ├── document.py             # Extract from .docx, text, URL
│   ├── rules_loader.py         # Load SEO rules from DB / fallback
│   ├── diff_generator.py       # Side-by-side diff generation
│   ├── docx_writer.py          # Write optimized .docx for download
│   └── auth.py                 # Supabase JWT + usage tracking
│
├── models/
│   └── schemas.py              # All Pydantic request/response models
│
└── routers/
    ├── analysis.py             # POST /analyze/* endpoints
    ├── billing.py              # Stripe subscription endpoints
    └── admin.py                # Admin rules management
```

---

## The 5-Agent Pipeline

```
Input (doc/url/text)
        ↓
[Agent 1: Extractor]   → Detects content type, keyword, structure
        ↓
[Agent 2: Scorer]      → Scores against 100-point rubric (parallel with Agent 5)
[Agent 5: URL Auditor] → Audits URL structure and link ecosystem
        ↓
[Agent 3: Rewriter]    → Produces SEO-optimized version
        ↓
[Agent 4: Validator]   → Re-scores optimized content, confirms improvement
        ↓
Response (scores, diff, optimized content, download)
```

---

## Setup — Local Development

### 1. Clone and install dependencies

```bash
cd seo-backend
python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your actual values
```

Required values in `.env`:
```
ANTHROPIC_API_KEY=        # Get from console.anthropic.com
SUPABASE_URL=             # Your Supabase project URL
SUPABASE_SERVICE_KEY=     # Service role key (not anon key!)
SUPABASE_JWT_SECRET=      # From Supabase > Settings > API
STRIPE_SECRET_KEY=        # From Stripe dashboard
STRIPE_WEBHOOK_SECRET=    # From Stripe > Webhooks
```

### 3. Set up Supabase database

1. Go to your Supabase project → SQL Editor
2. Copy the contents of `supabase_schema.sql`
3. Run it

### 4. Run the server

```bash
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

---

## API Endpoints

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analyze/document` | Upload .docx/.txt for analysis |
| POST | `/analyze/url` | Analyze content from a URL |
| POST | `/analyze/text` | Analyze pasted text |
| GET | `/analyze/{id}` | Retrieve previous analysis |
| GET | `/analyze/history/all` | Paginated analysis history |
| GET | `/analyze/{id}/download` | Download optimized .docx |

### Billing
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/billing/checkout` | Create Stripe checkout |
| POST | `/billing/portal` | Open Stripe customer portal |
| POST | `/billing/webhook` | Stripe webhook handler |
| GET | `/billing/status` | Usage and plan status |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/admin/rules` | Upload new SEO rules version |
| GET | `/admin/rules` | Get current active rules |
| GET | `/admin/rules/history` | All rule versions |
| GET | `/admin/stats` | Platform usage stats |

---

## Deployment — Railway (Recommended)

Railway is the easiest option for deploying a Python FastAPI app.

### 1. Create a Railway account
Go to railway.app → New Project → Deploy from GitHub

### 2. Create a `Procfile`

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 3. Add environment variables
In Railway dashboard → Variables → add all values from `.env.example`

### 4. Deploy
Push to your GitHub repo → Railway auto-deploys

Your API will be live at: `https://your-app.railway.app`

---

## Deployment — Render (Alternative)

1. Go to render.com → New Web Service
2. Connect your GitHub repo
3. Set:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables
5. Deploy

---

## Stripe Webhook Setup

After deploying, configure your Stripe webhook:

1. Stripe Dashboard → Developers → Webhooks → Add endpoint
2. URL: `https://your-api-url.com/billing/webhook`
3. Events to listen for:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
4. Copy the webhook secret → add to `.env` as `STRIPE_WEBHOOK_SECRET`

---

## Subscription Tiers

| Tier | Price | Analyses/month | Stripe Price ID |
|------|-------|---------------|-----------------|
| Starter | $29/mo | 20 | `STRIPE_STARTER_PRICE_ID` |
| Pro | $79/mo | 100 | `STRIPE_PRO_PRICE_ID` |
| Agency | $199/mo | Unlimited | `STRIPE_AGENCY_PRICE_ID` |

Create these products in Stripe Dashboard → Products → Add product.

---

## Updating SEO Rules

To update your SEO rules after deployment:

```bash
curl -X POST https://your-api.com/admin/rules \
  -H "X-Admin-Key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{"rules_markdown": "# Your updated rules...", "version_note": "Feb 2026 update"}'
```

Or use the Next.js admin panel (in the frontend codebase).

---

## Next Steps

1. ✅ Backend (this repo)
2. ⬜ Next.js frontend — UI with upload, score, diff, editor, download
3. ⬜ Supabase auth setup (email/password + magic link)
4. ⬜ Stripe products and price IDs
5. ⬜ Deploy backend to Railway/Render
6. ⬜ Deploy frontend to Vercel
7. ⬜ Configure Stripe webhook with live URL
