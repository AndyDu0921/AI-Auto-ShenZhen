from __future__ import annotations

import json
from typing import Any

from app.config import Settings


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        if not settings.use_mock_llm and settings.llm_api_key:
            from openai import OpenAI

            self._client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        if not self._client:
            raise RuntimeError("LLM client is not enabled")
        completion = self._client.chat.completions.create(
            model=self.settings.llm_model,
            messages=messages,
            temperature=temperature,
        )
        return completion.choices[0].message.content or ""

    def chat_json(self, messages: list[dict[str, str]], temperature: float = 0.1) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("LLM client is not enabled")
        try:
            completion = self._client.chat.completions.create(
                model=self.settings.llm_model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            content = completion.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception:
            raw = self.chat(messages, temperature=temperature)
            return self._best_effort_json(raw)

    @staticmethod
    def _best_effort_json(raw: str) -> dict[str, Any]:
        raw = raw.strip()
        if not raw:
            return {}
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {"raw": raw}
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return {"raw": raw}
