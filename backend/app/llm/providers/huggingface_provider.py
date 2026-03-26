"""
Hugging Face Inference API embedding provider.
Uses the Hugging Face Hub library to grab embeddings remotely.
"""
import os
from typing import Any
from huggingface_hub import AsyncInferenceClient
from app.llm.base import LLMProvider, LLMMessage
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class HuggingFaceEmbeddingProvider(LLMProvider):
    def __init__(self):
        # Prevent any expired system cached tokens from being loaded implicitly
        os.environ.pop("HF_TOKEN", None)
        
        self.model = settings.HUGGINGFACE_EMBEDDING_MODEL
        
        self.client = AsyncInferenceClient(
            token=settings.HUGGINGFACE_API_KEY,
        )

    async def embed_text(self, text: str) -> list[float]:
        try:
            # Note: feature_extraction currently expects list output for single strings in many HF API formats
            # Returning the pooled single vector
            result = await self.client.feature_extraction(
                text,
                model=self.model,
            )
            # HF AsyncInferenceClient feature_extraction returns a nested list or numpy array depending on the model
            # For bge models, it's typically a list of floats, but sometimes padded or nested like [[...]]
            
            # Since huggingface_hub sometimes returns a single list for a single string, or a nested list:
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
                # if returned as [[float, float...]], extract the first
                return result[0]
            
            return result
        except Exception as e:
            logger.error(f"HF Embedding failed: {e}")
            raise e

    # ── Chat/extraction not used on this provider ─────────────────────────────
    async def chat_completion(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> str:
        raise NotImplementedError("HuggingFaceEmbeddingProvider is configured for embeddings only here.")

    async def structured_extraction(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> dict:
        raise NotImplementedError("HuggingFaceEmbeddingProvider is configured for embeddings only here.")
