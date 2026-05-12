"""
Token Tracker Service
----------------------
Tracks token usage per user per billing cycle.

Rules:
- Every OpenAI API call returns usage.prompt_tokens + usage.completion_tokens
- We capture these across all 5 agents and sum them per analysis
- Running monthly total stored in Supabase users table
- At 80%  → warning returned in API response (analysis still completes)
- At 100% → analysis blocked with reset date shown
- Monthly reset happens automatically via Stripe invoice.paid webhook
  OR via the manual reset function if not using Stripe

Tier budgets (tokens per month):
  starter  →   500,000
  pro      → 2,000,000
  agency   → 8,000,000
"""

from config import (
    TIER_TOKEN_BUDGETS,
    TOKEN_WARNING_THRESHOLD,
    INPUT_COST_PER_TOKEN,
    OUTPUT_COST_PER_TOKEN,
)
from models.schemas import (
    AgentTokenUsage,
    AnalysisTokenUsage,
    TokenWarningLevel,
)


# ---------- Cost Calculation ----------

def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate USD cost from token counts using GPT-4o pricing."""
    return round(
        (input_tokens * INPUT_COST_PER_TOKEN) +
        (output_tokens * OUTPUT_COST_PER_TOKEN),
        6
    )


def build_agent_usage(agent_name: str, response) -> AgentTokenUsage:
    """
    Extract token usage from an OpenAI API response object.
    Handles both APIs:
      - Chat Completions API: usage.prompt_tokens / usage.completion_tokens
      - Responses API:        usage.input_tokens  / usage.output_tokens

    Usage:
        response = client.chat.completions.create(...)   # Chat Completions
        response = client.responses.create(...)          # Responses API
        usage = build_agent_usage("scorer", response)    # works for both
    """
    usage = response.usage

    # Responses API uses input_tokens / output_tokens
    # Chat Completions uses prompt_tokens / completion_tokens
    _in = getattr(usage, "input_tokens", None)
    input_tokens = _in if _in is not None else getattr(usage, "prompt_tokens", 0)

    _out = getattr(usage, "output_tokens", None)
    output_tokens = _out if _out is not None else getattr(usage, "completion_tokens", 0)

    cost = calculate_cost(input_tokens, output_tokens)

    return AgentTokenUsage(
        agent_name=agent_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
    )


def aggregate_token_usage(agent_usages: list[AgentTokenUsage]) -> AnalysisTokenUsage:
    """
    Sum token usage across all agents into one AnalysisTokenUsage object.
    Called after all 5 agents complete.
    """
    total_input = sum(a.input_tokens for a in agent_usages)
    total_output = sum(a.output_tokens for a in agent_usages)
    total_cost = calculate_cost(total_input, total_output)

    return AnalysisTokenUsage(
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_tokens=total_input + total_output,
        total_cost_usd=total_cost,
        per_agent=agent_usages,
    )


# ---------- Budget Checking ----------

def check_token_budget(
    tier: str,
    tokens_used_this_month: int,
    tokens_about_to_use: int = 0,
) -> tuple[TokenWarningLevel, str | None]:
    """
    Check where a user stands against their monthly token budget.

    Args:
        tier: subscription tier string
        tokens_used_this_month: tokens already used this billing cycle
        tokens_about_to_use: estimated tokens for the upcoming analysis

    Returns:
        (warning_level, warning_message | None)

    Logic:
        - If already at/over budget → BLOCKED
        - If this analysis would push over budget → BLOCKED
        - If usage >= 80% of budget → WARNING (but allow)
        - Otherwise → OK
    """
    budget = TIER_TOKEN_BUDGETS.get(tier, TIER_TOKEN_BUDGETS["starter"])

    # Agency tier has a very large budget — effectively unlimited
    if budget == -1:
        return TokenWarningLevel.OK, None

    projected = tokens_used_this_month + tokens_about_to_use
    usage_pct = tokens_used_this_month / budget

    # Already at or over budget
    if tokens_used_this_month >= budget:
        remaining_formatted = _format_tokens(budget - tokens_used_this_month)
        return (
            TokenWarningLevel.BLOCKED,
            f"You've used 100% of your monthly token budget ({_format_tokens(budget)} tokens). "
            f"Your budget resets at the start of your next billing cycle. "
            f"Upgrade your plan for immediate access."
        )

    # This analysis would push them over
    if projected > budget:
        return (
            TokenWarningLevel.BLOCKED,
            f"This analysis would exceed your monthly token budget. "
            f"You have {_format_tokens(budget - tokens_used_this_month)} tokens remaining "
            f"but this analysis requires approximately {_format_tokens(tokens_about_to_use)} tokens. "
            f"Your budget resets at the start of your next billing cycle."
        )

    # At or above warning threshold (80%)
    if usage_pct >= TOKEN_WARNING_THRESHOLD:
        used_pct = round(usage_pct * 100, 1)
        remaining = budget - tokens_used_this_month
        return (
            TokenWarningLevel.WARNING,
            f"⚠️ You've used {used_pct}% of your monthly token budget. "
            f"{_format_tokens(remaining)} tokens remaining this cycle. "
            f"Your budget resets at the start of your next billing cycle."
        )

    return TokenWarningLevel.OK, None


def get_budget_summary(tier: str, tokens_used: int) -> dict:
    """Return a full budget summary dict for the usage status endpoint."""
    budget = TIER_TOKEN_BUDGETS.get(tier, TIER_TOKEN_BUDGETS["starter"])

    if budget == -1:
        return {
            "token_budget": -1,
            "tokens_used_this_month": tokens_used,
            "tokens_remaining": -1,
            "token_usage_pct": 0.0,
            "warning_level": TokenWarningLevel.OK,
            "warning_message": None,
        }

    remaining = max(0, budget - tokens_used)
    usage_pct = round(min(tokens_used / budget, 1.0), 4)
    warning_level, warning_message = check_token_budget(tier, tokens_used)

    return {
        "token_budget": budget,
        "tokens_used_this_month": tokens_used,
        "tokens_remaining": remaining,
        "token_usage_pct": usage_pct,
        "warning_level": warning_level,
        "warning_message": warning_message,
    }


# ---------- DB Persistence ----------

async def save_token_usage_to_db(
    user_id: str,
    analysis_id: str,
    token_usage: AnalysisTokenUsage,
    supabase_client,
) -> None:
    """
    Persist token usage to Supabase:
    1. Update analyses row with token counts and cost
    2. Atomically increment users.tokens_used_this_month
    3. Update users.estimated_cost_usd
    """
    try:
        # Update the analysis record
        supabase_client.table("analyses").update({
            "tokens_input": token_usage.total_input_tokens,
            "tokens_output": token_usage.total_output_tokens,
            "tokens_total": token_usage.total_tokens,
            "cost_usd": token_usage.total_cost_usd,
        }).eq("id", analysis_id).execute()

        # Atomically increment user's monthly token total and cost
        supabase_client.rpc("increment_token_usage", {
            "p_user_id": user_id,
            "p_tokens": token_usage.total_tokens,
            "p_cost": token_usage.total_cost_usd,
        }).execute()

    except Exception as e:
        # Non-fatal — log but don't fail the response
        print(f"[TokenTracker] Failed to save token usage for {user_id}: {e}")


# ---------- Helpers ----------

def _format_tokens(n: int) -> str:
    """Format token count for human-readable messages."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)