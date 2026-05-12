-- ============================================================
-- SEO Analyzer — Token Tracking Migration
-- Run this AFTER the main supabase_schema.sql
-- Adds token budget columns + atomic increment function
-- ============================================================


-- ─── 1. Add token columns to users table ─────────────────────

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS tokens_used_this_month INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS token_budget INTEGER NOT NULL DEFAULT 500000,
    ADD COLUMN IF NOT EXISTS estimated_cost_usd NUMERIC(10, 4) NOT NULL DEFAULT 0.0;

-- Set correct token budget per existing tier
UPDATE public.users SET token_budget = 500000  WHERE subscription_tier = 'starter';
UPDATE public.users SET token_budget = 2000000 WHERE subscription_tier = 'pro';
UPDATE public.users SET token_budget = 8000000 WHERE subscription_tier = 'agency';


-- ─── 2. Add token columns to analyses table ──────────────────

ALTER TABLE public.analyses
    ADD COLUMN IF NOT EXISTS tokens_input INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS tokens_output INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS tokens_total INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cost_usd NUMERIC(8, 6) NOT NULL DEFAULT 0.0;

CREATE INDEX IF NOT EXISTS analyses_tokens_total_idx ON public.analyses(tokens_total);


-- ─── 3. Atomic token increment function ──────────────────────
-- Called after every analysis to update running monthly totals

CREATE OR REPLACE FUNCTION public.increment_token_usage(
    p_user_id UUID,
    p_tokens INTEGER,
    p_cost NUMERIC
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    UPDATE public.users
    SET
        tokens_used_this_month = tokens_used_this_month + p_tokens,
        estimated_cost_usd = estimated_cost_usd + p_cost,
        updated_at = NOW()
    WHERE id = p_user_id;
END;
$$;


-- ─── 4. Monthly token reset function ─────────────────────────
-- Called by Stripe webhook on invoice.paid
-- Also callable manually from admin panel

CREATE OR REPLACE FUNCTION public.reset_monthly_tokens(p_user_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    UPDATE public.users
    SET
        tokens_used_this_month = 0,
        analyses_used = 0,
        billing_cycle_start = NOW(),
        updated_at = NOW()
    WHERE id = p_user_id;
END;
$$;


-- ─── 5. Update token_budget when tier changes ────────────────
-- Trigger fires when subscription_tier is updated (e.g. after upgrade)

CREATE OR REPLACE FUNCTION public.sync_token_budget_on_tier_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.subscription_tier != OLD.subscription_tier THEN
        NEW.token_budget := CASE NEW.subscription_tier
            WHEN 'starter' THEN 500000
            WHEN 'pro'     THEN 2000000
            WHEN 'agency'  THEN 8000000
            ELSE 500000
        END;
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER sync_token_budget
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION public.sync_token_budget_on_tier_change();


-- ─── 6. Token usage view (for admin dashboard) ───────────────

CREATE OR REPLACE VIEW public.token_usage_summary AS
SELECT
    u.subscription_tier,
    COUNT(u.id) AS user_count,
    SUM(u.tokens_used_this_month) AS total_tokens_used,
    ROUND(AVG(u.tokens_used_this_month), 0) AS avg_tokens_per_user,
    SUM(u.estimated_cost_usd) AS total_cost_usd,
    ROUND(AVG(
        CASE
            WHEN u.token_budget > 0
            THEN (u.tokens_used_this_month::NUMERIC / u.token_budget) * 100
            ELSE 0
        END
    ), 1) AS avg_budget_used_pct
FROM public.users u
GROUP BY u.subscription_tier;


-- ─── 7. Per-user token usage view ────────────────────────────

CREATE OR REPLACE VIEW public.user_token_status AS
SELECT
    u.id,
    u.email,
    u.subscription_tier,
    u.tokens_used_this_month,
    u.token_budget,
    u.token_budget - u.tokens_used_this_month AS tokens_remaining,
    ROUND(
        (u.tokens_used_this_month::NUMERIC / NULLIF(u.token_budget, 0)) * 100,
        1
    ) AS budget_used_pct,
    u.estimated_cost_usd,
    u.billing_cycle_start,
    CASE
        WHEN u.tokens_used_this_month >= u.token_budget THEN 'blocked'
        WHEN u.tokens_used_this_month >= (u.token_budget * 0.8) THEN 'warning'
        ELSE 'ok'
    END AS warning_level
FROM public.users u;


-- ─── Done! ───────────────────────────────────────────────────
-- Verify by running:
-- SELECT * FROM public.user_token_status;
-- SELECT * FROM public.token_usage_summary;