import json
from typing import Any
import anthropic
from app.llm.base import LLMProvider, LLMMessage
from app.config import settings


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.chat_model = settings.ANTHROPIC_CHAT_MODEL
        self.extraction_model = settings.ANTHROPIC_EXTRACTION_MODEL

    def _split_messages(self, messages: list[LLMMessage]) -> tuple[str, list[dict]]:
        """Anthropic separates system prompt from user/assistant turns."""
        system_prompt = ""
        turns = []
        for m in messages:
            if m.role == "system":
                system_prompt += m.content + "\n"
            else:
                turns.append(m.to_dict())
        return system_prompt.strip(), turns

    async def chat_completion(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> str:
        system, turns = self._split_messages(messages)
        response = await self.client.messages.create(
            model=self.chat_model,
            system=system or "You are a helpful assistant.",
            messages=turns,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.content[0].text if response.content else ""

    async def structured_extraction(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> dict:
        system, turns = self._split_messages(messages)
        # Instruct Claude to output only JSON
        full_system = (system or "") + "\nOutput ONLY valid JSON. No markdown, no extra text."
        response = await self.client.messages.create(
            model=self.extraction_model,
            system=full_system,
            messages=turns,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.content[0].text if response.content else "{}"
        # Strip potential markdown code fences
        content = content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(content)

    async def embed_text(self, text: str) -> list[float]:
        # Anthropic does not expose a direct embedding API; fall back to a small OpenAI call
        # or raise NotImplementedError to be handled upstream.
        raise NotImplementedError(
            "Anthropic does not provide a public embeddings API. "
            "Set EMBEDDING_PROVIDER=openai or use another provider for embeddings."
        )
