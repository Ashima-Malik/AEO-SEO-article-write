-- ============================================================
-- SEO Analyzer — Supabase Database Schema
-- Run these in order in Supabase SQL Editor
-- ============================================================


-- ─── 1. Users Table (extends Supabase Auth) ──────────────────

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    subscription_tier TEXT NOT NULL DEFAULT 'starter'
        CHECK (subscription_tier IN ('starter', 'pro', 'agency')),
    analyses_used INTEGER NOT NULL DEFAULT 0,
    analyses_limit INTEGER NOT NULL DEFAULT 20,
    billing_cycle_start TIMESTAMPTZ DEFAULT NOW(),
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-create user profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email)
    VALUES (NEW.id, NEW.email)
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- ─── 2. Atomic Usage Increment Function ──────────────────────

CREATE OR REPLACE FUNCTION public.increment_analyses_used(user_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE public.users
    SET analyses_used = analyses_used + 1,
        updated_at = NOW()
    WHERE id = user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ─── 3. Analyses Table ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    input_type TEXT NOT NULL CHECK (input_type IN ('document', 'url', 'text')),
    content_type TEXT NOT NULL CHECK (content_type IN ('article', 'bio', 'product_page', 'general')),
    target_keyword TEXT,

    -- Content (capped at 10k chars for storage efficiency)
    original_content TEXT,
    optimized_content TEXT,

    -- Scores
    score_before INTEGER NOT NULL DEFAULT 0 CHECK (score_before >= 0 AND score_before <= 100),
    score_after INTEGER NOT NULL DEFAULT 0 CHECK (score_after >= 0 AND score_after <= 100),

    -- Detailed breakdown (JSONB for flexible querying)
    issues_json JSONB DEFAULT '{}',
    changes_json JSONB DEFAULT '{}',

    -- Status
    status TEXT NOT NULL DEFAULT 'completed'
        CHECK (status IN ('processing', 'completed', 'failed')),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS analyses_user_id_idx ON public.analyses(user_id);
CREATE INDEX IF NOT EXISTS analyses_created_at_idx ON public.analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS analyses_content_type_idx ON public.analyses(content_type);


-- ─── 4. SEO Rules Table ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.seo_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    version_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Only one active rule set at a time
CREATE UNIQUE INDEX IF NOT EXISTS seo_rules_one_active
    ON public.seo_rules(is_active)
    WHERE is_active = TRUE;


-- ─── 5. Row Level Security (RLS) ─────────────────────────────

-- Enable RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.seo_rules ENABLE ROW LEVEL SECURITY;

-- Users: can only read/update their own profile
CREATE POLICY "Users can view own profile"
    ON public.users FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.users FOR UPDATE
    USING (auth.uid() = id);

-- Analyses: users can only see their own
CREATE POLICY "Users can view own analyses"
    ON public.analyses FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own analyses"
    ON public.analyses FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- SEO Rules: readable by authenticated users, writable only by service role
CREATE POLICY "Authenticated users can read rules"
    ON public.seo_rules FOR SELECT
    TO authenticated
    USING (true);

-- Service role bypass (used by backend)
-- The backend uses the service_role key which bypasses RLS automatically


-- ─── 6. Updated_at trigger ───────────────────────────────────

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- ─── 7. Useful Views ─────────────────────────────────────────

-- Admin dashboard: usage summary
CREATE OR REPLACE VIEW public.usage_summary AS
SELECT
    subscription_tier,
    COUNT(*) as user_count,
    AVG(analyses_used) as avg_analyses_used,
    SUM(analyses_used) as total_analyses_used
FROM public.users
GROUP BY subscription_tier;

-- Average score improvement by content type
CREATE OR REPLACE VIEW public.score_improvements AS
SELECT
    content_type,
    COUNT(*) as analysis_count,
    ROUND(AVG(score_before), 1) as avg_score_before,
    ROUND(AVG(score_after), 1) as avg_score_after,
    ROUND(AVG(score_after - score_before), 1) as avg_improvement
FROM public.analyses
WHERE status = 'completed'
GROUP BY content_type;


-- ─── Done! ────────────────────────────────────────────────────
-- Next steps:
-- 1. Run this SQL in Supabase SQL Editor
-- 2. Create a Storage bucket called 'documents' (optional)
-- 3. Copy your .env.example to .env and fill in values
-- 4. Run: pip install -r requirements.txt
-- 5. Run: uvicorn main:app --reload
