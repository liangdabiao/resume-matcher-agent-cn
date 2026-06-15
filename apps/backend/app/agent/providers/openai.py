import os
import logging

from openai import OpenAI
from typing import Any, Dict
from fastapi.concurrency import run_in_threadpool

from ..exceptions import ProviderError
from .base import Provider
from ...core import settings

logger = logging.getLogger(__name__)


class OpenAIProvider(Provider):
    def __init__(self, api_key: str | None = None, model_name: str = settings.LL_MODEL,
                 base_url: str | None = None, opts: Dict[str, Any] = None):
        if opts is None:
            opts = {}
        api_key = api_key or settings.LLM_API_KEY or os.getenv("LLM_API_KEY")
        if not api_key:
            raise ProviderError("LLM_API_KEY is missing")
        base_url = base_url or settings.LLM_BASE_URL
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model_name
        self.opts = opts
        self.instructions = ""

    def _generate_sync(self, prompt: str, options: Dict[str, Any]) -> str:
        try:
            # 使用chat.completions.create替代responses.create，以兼容代理服务器限制
            messages = []
            if self.instructions:
                messages.append({"role": "system", "content": self.instructions})
            messages.append({"role": "user", "content": prompt})
            
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                **options,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise ProviderError(f"OpenAI - error generating response: {e}") from e

    async def __call__(self, prompt: str, **generation_args: Any) -> str:
        allowed_options = {"temperature", "top_p", "max_tokens"}
        myopts = {
            key: value
            for key, value in self.opts.items()
            if key in allowed_options and value is not None
        }
        return await run_in_threadpool(self._generate_sync, prompt, myopts)
