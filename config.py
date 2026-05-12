from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # OpenAI — required
    openai_api_key: str

    # App
    app_env: str = "development"
    frontend_url: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"   # silently ignore SUPABASE_*, STRIPE_* etc.


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Kept for reference / token_tracker compatibility
TIER_LIMITS = {
    "starter": 20,
    "pro": 100,
    "agency": -1,
}

TIER_TOKEN_BUDGETS = {
    "starter":   500_000,
    "pro":     2_000_000,
    "agency":  8_000_000,
}

TOKEN_WARNING_THRESHOLD = 0.80

# GPT-4o pricing (per token)
INPUT_COST_PER_TOKEN  = 0.0000025   # $2.50 / 1M input tokens
OUTPUT_COST_PER_TOKEN = 0.00001     # $10.00 / 1M output tokens

OPENAI_MODEL = "gpt-4o-mini"
