from __future__ import annotations

import json
from typing import Any

import httpx

from app.settings import settings


class LlmClient:
    def __init__(self) -> None:
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def json_chat(self, system: str, user: str, schema_name: str, schema: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("LLM API key is not configured")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)


llm_client = LlmClient()
