"""
Клиент к разрешённому OpenAI-совместимому API хакатона.

Используется только внешний API, настроенный через `.env`:
`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`.

Никаких локальных LLM-сервисов и автоматического fallback здесь нет:
если ключ не задан или модель не входит в разрешённый список, клиент
работает в демо-режиме и возвращает `None`. Это осознанное ограничение
хакатона: лучше показать локальный разбор, чем незаметно уйти в
запрещённый провайдер.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://challenge.up.railway.app/v1"
DEFAULT_MODEL = "deepseek/deepseek-v4.1-flash"

# Модели, разрешённые условиями хакатона.
ALLOWED_MODELS = {
    "google/gemma-4-26b-a4b-it",
    "z-ai/glm-5.3-flash",
    "qwen/qwen3.6-35b-a3b",
    "deepseek/deepseek-v4.1-flash",
    "qwen/qwen3-vl-30b-a3b-instruct",
    "moonshotai/kimi-k2.6",
}

_PLACEHOLDER_KEYS = {
    "",
    "your_api_key_here",
    "вставьте ключ",
    "changeme",
    "sk-...",
}


def _load_dotenv() -> None:
    """Читает `.env` рядом с проектом, не переопределяя реальное окружение."""
    path = Path(__file__).resolve().parent.parent / ".env"
    if not path.exists():
        return
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)
    except Exception as exc:
        logger.debug("Не удалось прочитать .env: %s", exc)


def _clean_secret(value: Optional[str]) -> str:
    value = (value or "").strip().strip('"').strip("'")
    return "" if value.lower() in _PLACEHOLDER_KEYS else value


class LLMClient:
    """Единственный клиент к разрешённому внешнему LLM API."""

    def __init__(self) -> None:
        _load_dotenv()

        self.api_key = _clean_secret(os.getenv("LLM_API_KEY"))
        self.api_base = (
            os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL
        ).rstrip("/")
        self.api_model = os.getenv("LLM_MODEL") or DEFAULT_MODEL

        self.provider = ""
        self.enabled = False
        self.config_error = ""
        self.last_error = ""

        if not self.api_key:
            self.last_error = "LLM_API_KEY не задан"
            logger.info(
                "LLM: LLM_API_KEY не задан — доступен только локальный демо-режим"
            )
            return

        if self.api_model not in ALLOWED_MODELS:
            self.config_error = (
                f"Модель {self.api_model!r} не входит в разрешённый список"
            )
            self.last_error = self.config_error
            logger.error("LLM: %s", self.config_error)
            return

        self.provider = "api"
        self.enabled = True
        logger.info("LLM: провайдер api, модель %s", self.api_model)

    async def generate(
        self,
        prompt: str,
        timeout: float = 90.0,
        max_tokens: int = 900,
        temperature: float = 0.2,
    ) -> Optional[str]:
        """Возвращает текст ответа модели или None, если API недоступна."""
        if not self.enabled:
            return None

        try:
            text = await self._generate_api(
                prompt,
                timeout=timeout,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if text:
                self.last_error = ""
            else:
                self.last_error = "Пустой ответ модели"
            return text
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            logger.warning("Внешняя LLM недоступна: %s", exc)
            return None

    async def _generate_api(
        self,
        prompt: str,
        timeout: float,
        max_tokens: int,
        temperature: float,
    ) -> Optional[str]:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.api_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"] or ""
            return text.strip() or None
