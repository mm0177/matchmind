from abc import ABC, abstractmethod
from typing import Any


class LLMMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> str:
        """Send a chat completion request and return the assistant's text response."""
        ...

    @abstractmethod
    async def structured_extraction(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> dict:
        """Send a request and return a JSON-parsed dict (for persona extraction)."""
        ...

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Return a vector embedding for the given text."""
        ...
