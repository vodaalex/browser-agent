from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── LLM ──────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    model_name: str = "claude-sonnet-4-5"
    max_tokens: int = 1024

    # ── Agent ────────────────────────────────────────────────────
    max_steps: int = 25
    compress_threshold: int = 200_000
    max_screenshots_in_context: int = 2

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

