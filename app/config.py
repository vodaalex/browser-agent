from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── LLM ──────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    model_name: str = "claude-sonnet-4-5"
    planner_model_name: str = "claude-sonnet-4-5"
    # Routing: Haiku for text-only decision steps (no screenshot in last result)
    action_model_name: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 800        # Sonnet vision steps
    action_max_tokens: int = 600 # Haiku text steps — shorter output, faster

    # ── Agent ────────────────────────────────────────────────────
    max_steps: int = 30
    compress_threshold: int = 20_000
    max_screenshots_in_context: int = 1

    # ── Browser ──────────────────────────────────────────────────
    headless: bool = False
    viewport_width: int = 1280
    viewport_height: int = 800
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # ── Server ───────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

