"""
LM Studio local embedding provider.
LM Studio serves an OpenAI-compatible API at http://127.0.0.1:1234/v1.
Used here exclusively for embeddings (bge-small-en-v1.5, dim=384).
Chat/extraction still go through Groq.
"""
from typing import Any
from openai import AsyncOpenAI
from app.llm.base import LLMProvider, LLMMessage
from app.config import settings


class LMStudioEmbeddingProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key="lm-studio",          # LM Studio ignores the key but client requires a value
            base_url=settings.LMSTUDIO_BASE_URL,
        )
        self.model = settings.LMSTUDIO_EMBEDDING_MODEL

    async def embed_text(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    # ── Chat/extraction not used on this provider ─────────────────────────────
    async def chat_completion(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> str:
        raise NotImplementedError("LMStudioEmbeddingProvider is for embeddings only.")

    async def structured_extraction(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> dict:
        raise NotImplementedError("LMStudioEmbeddingProvider is for embeddings only.")
