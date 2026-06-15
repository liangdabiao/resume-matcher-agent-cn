from typing import Any, Dict

from ..core import settings
from .strategies.wrapper import JSONWrapper, MDWrapper
from .providers.base import Provider
from .providers.openai import OpenAIProvider


class AgentManager:
    def __init__(
        self,
        strategy: str | None = None,
        model: str = settings.LL_MODEL,
    ) -> None:
        match strategy:
            case "md":
                self.strategy = MDWrapper()
            case "json":
                self.strategy = JSONWrapper()
            case _:
                self.strategy = JSONWrapper()
        self.model = model

    async def _get_provider(self, **kwargs: Any) -> Provider:
        opts = {
            "temperature": kwargs.get("temperature", 0),
            "top_p": kwargs.get("top_p", 0.9),
        }
        api_key = kwargs.get("llm_api_key", settings.LLM_API_KEY)
        base_url = kwargs.get("llm_base_url", settings.LLM_BASE_URL)
        model = kwargs.get("model", self.model)
        return OpenAIProvider(
            model_name=model,
            api_key=api_key,
            base_url=base_url,
            opts=opts,
        )

    async def run(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        provider = await self._get_provider(**kwargs)
        return await self.strategy(prompt, provider, **kwargs)
