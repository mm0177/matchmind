import json
from typing import Any
import google.generativeai as genai
from app.llm.base import LLMProvider, LLMMessage
from app.config import settings


class GeminiProvider(LLMProvider):
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.chat_model = genai.GenerativeModel(settings.GEMINI_CHAT_MODEL)
        self.extraction_model_name = settings.GEMINI_EXTRACTION_MODEL

    def _to_gemini_history(self, messages: list[LLMMessage]) -> tuple[str, list[dict]]:
        """Convert to Gemini's format: system instruction + contents list."""
        system_parts = []
        history = []
        for m in messages:
            if m.role == "system":
                system_parts.append(m.content)
            elif m.role == "user":
                history.append({"role": "user", "parts": [m.content]})
            elif m.role == "assistant":
                history.append({"role": "model", "parts": [m.content]})
        return "\n".join(system_parts), history

    async def chat_completion(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> str:
        system_instruction, history = self._to_gemini_history(messages)
        model = genai.GenerativeModel(
            settings.GEMINI_CHAT_MODEL,
            system_instruction=system_instruction or None,
        )
        # Split off the last user message to send as the active prompt
        if history and history[-1]["role"] == "user":
            last_user = history[-1]["parts"][0]
            past = history[:-1]
        else:
            last_user = ""
            past = history

        chat = model.start_chat(history=past)
        response = await chat.send_message_async(
            last_user,
            generation_config=genai.GenerationConfig(
                temperature=temperature, max_output_tokens=max_tokens
            ),
        )
        return response.text or ""

    async def structured_extraction(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> dict:
        system_instruction, history = self._to_gemini_history(messages)
        full_system = (system_instruction or "") + "\nOutput ONLY valid JSON. No markdown."
        model = genai.GenerativeModel(
            self.extraction_model_name,
            system_instruction=full_system,
        )
        if history and history[-1]["role"] == "user":
            last_user = history[-1]["parts"][0]
            past = history[:-1]
        else:
            last_user = ""
            past = history

        chat = model.start_chat(history=past)
        response = await chat.send_message_async(
            last_user,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text or "{}")

    async def embed_text(self, text: str) -> list[float]:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
        )
        return result["embedding"]
