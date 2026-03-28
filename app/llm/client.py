import anthropic

from app.config import Settings, settings
from app.log import logger


class LLMClient:
    def __init__(self, cfg: Settings | None = None):
        self._cfg = cfg or settings
        self._client = anthropic.AsyncAnthropic(api_key=self._cfg.anthropic_api_key)
        self.model = self._cfg.model_name
        self.max_tokens = self._cfg.max_tokens

    async def create_message(
        self,
        *,
        messages: list[dict],
        system: str,
        tools: list[dict] | None = None,
        max_tokens: int | None = None,
        model_override: str | None = None,
    ):
        model = model_override or self.model
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens or self.max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        logger.debug("LLM request: model=%s, messages=%d", model, len(messages))
        return await self._client.messages.create(**kwargs)

