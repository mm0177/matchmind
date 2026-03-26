import json
from typing import Any
from groq import AsyncGroq
from app.llm.base import LLMProvider, LLMMessage
from app.config import settings


class GroqProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.chat_model = settings.GROQ_CHAT_MODEL
        self.extraction_model = settings.GROQ_EXTRACTION_MODEL

    async def chat_completion(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> str:
        response = await self.client.chat.completions.create(
            model=self.chat_model,
            messages=[m.to_dict() for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    async def structured_extraction(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> dict:
        # Groq supports response_format json_object for many models
        response = await self.client.chat.completions.create(
            model=self.extraction_model,
            messages=[m.to_dict() for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        # Strip any accidental markdown fences
        content = content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(content)

    async def embed_text(self, text: str) -> list[float]:
        # Groq does not offer an embeddings endpoint.
        # Embedding is handled by the configured EMBEDDING_PROVIDER (default: openai).
        raise NotImplementedError(
            "Groq does not provide an embeddings API. "
            "Set EMBEDDING_PROVIDER=openai and supply OPENAI_API_KEY for vector embeddings."
        )
