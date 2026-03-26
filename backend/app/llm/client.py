from functools import lru_cache
from app.config import settings
from app.llm.base import LLMProvider


@lru_cache()
def get_llm_client() -> LLMProvider:
    """Factory — reads LLM_PROVIDER from env and returns the right provider instance."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "groq":
        from app.llm.providers.groq_provider import GroqProvider
        return GroqProvider()

    if provider == "openai":
        from app.llm.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()

    if provider == "anthropic":
        from app.llm.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider()

    if provider == "gemini":
        from app.llm.providers.gemini_provider import GeminiProvider
        return GeminiProvider()

    raise ValueError(
        f"Unknown LLM_PROVIDER '{settings.LLM_PROVIDER}'. "
        "Valid values: groq | openai | anthropic | gemini"
    )


@lru_cache()
def get_embedding_client() -> LLMProvider | None:
    """
    Returns a provider capable of generating embeddings, or None if disabled.
    Default: lmstudio (bge-small-en-v1.5 running locally via LM Studio on port 1234).
    """
    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider == "none" or not provider:
        return None
    if provider == "huggingface":
        from app.llm.providers.huggingface_provider import HuggingFaceEmbeddingProvider
        return HuggingFaceEmbeddingProvider()
    if provider == "lmstudio":
        from app.llm.providers.lmstudio_provider import LMStudioEmbeddingProvider
        return LMStudioEmbeddingProvider()
    if provider == "openai":
        from app.llm.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    raise ValueError(f"Unknown EMBEDDING_PROVIDER '{settings.EMBEDDING_PROVIDER}'. Valid: huggingface | lmstudio | openai | none")
