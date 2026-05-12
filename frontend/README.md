# RankReady — Frontend

Next.js 14 frontend for the RankReady SEO platform.

## Setup

```bash
npm install
cp .env.local.example .env.local
# Fill in NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
npm run dev
```

## Required
- Backend running on `http://localhost:8000` (or set NEXT_PUBLIC_API_URL)
- Supabase project with anon key

## Pages
- `/login` — Auth (email/password + magic link)
- `/dashboard` — Usage summary + quick actions
- `/analyzer` — SEO Analyzer input
- `/analyzer/[id]` — Results: score, diff, optimized, tokens
- `/audit` — Site audit
- `/keywords` — Keyword clusters + content briefs
- `/writer` — AI writer
- `/compare` — Competitor comparison
- `/export` — Export reports
- `/history` — Analysis history
- `/billing` — Plans + token budget
- `/admin` — Admin panel (admin emails only)

## Deploy
Deploy to Vercel:
```bash
vercel deploy
```
Add env vars in Vercel dashboard.
