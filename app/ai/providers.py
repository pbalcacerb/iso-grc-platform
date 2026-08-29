"""Proveedores de IA conmutables (API compatible OpenAI).

WP0: permite alternar entre SiliconFlow (desarrollo/demo) y
Azure OpenAI (producción) mediante la variable AI_PROVIDER.
"""
from __future__ import annotations

import json

import httpx

from app.config import settings


class SiliconFlowProvider:
    """Proveedor de desarrollo/demo."""

    name = "siliconflow"

    def __init__(self) -> None:
        self.base_url = settings.SILICONFLOW_BASE_URL.rstrip("/")
        self.api_key = settings.SILICONFLOW_API_KEY
        self.chat_model = settings.CHAT_MODEL
        self.embedding_model = settings.SF_EMBEDDING_MODEL

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat_json(self, prompt: str) -> dict:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.chat_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        # Algunos modelos envuelven el JSON en una clave "response"
        if isinstance(data, dict) and isinstance(data.get("response"), dict):
            data = data["response"]
        return data

    def embed(self, text: str) -> list[float]:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{self.base_url}/embeddings",
                headers=self._headers(),
                json={"model": self.embedding_model, "input": text},
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]


class AzureOpenAIProvider:
    """Proveedor de producción (residencia de datos, DPA enterprise)."""

    name = "azure_openai"

    def __init__(self) -> None:
        self.endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        self.api_key = settings.AZURE_OPENAI_API_KEY
        self.api_version = settings.AZURE_OPENAI_API_VERSION
        self.chat_model = settings.AZURE_CHAT_DEPLOYMENT
        self.embedding_model = settings.AZURE_EMBEDDING_DEPLOYMENT

    def is_configured(self) -> bool:
        return bool(self.api_key and self.endpoint)

    def _headers(self) -> dict[str, str]:
        return {"api-key": self.api_key, "Content-Type": "application/json"}

    def chat_json(self, prompt: str) -> dict:
        url = (
            f"{self.endpoint}/openai/deployments/{self.chat_model}"
            f"/chat/completions?api-version={self.api_version}"
        )
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                url,
                headers=self._headers(),
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)

    def embed(self, text: str) -> list[float]:
        url = (
            f"{self.endpoint}/openai/deployments/{self.embedding_model}"
            f"/embeddings?api-version={self.api_version}"
        )
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                url,
                headers=self._headers(),
                json={"input": text, "dimensions": settings.EMBEDDING_DIM},
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]


def get_provider():
    """Devuelve el proveedor activo según AI_PROVIDER."""
    if settings.AI_PROVIDER == "azure_openai":
        return AzureOpenAIProvider()
    if settings.AI_PROVIDER == "off":
        provider = SiliconFlowProvider()
        provider.api_key = ""
        return provider
    return SiliconFlowProvider()