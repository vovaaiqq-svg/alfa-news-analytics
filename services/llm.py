"""
Клиент к LLM для ответов агентов.

Приоритет:
1. OpenAI-совместимый API из `.env` / переменных окружения:
   `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`.
2. Локальный OpenCode на этой машине (если API-ключ не задан).
3. Локальная сборка ответа в API, если LLM недоступна.

Ключ никогда не логируется и не попадает в ответы. В репозиторий его
нужно передавать только через `.env` (файл уже в .gitignore).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_PLACEHOLDER_KEYS = {
    "",
    "your_api_key_here",
    "вставьте ключ",
    "changeme",
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
    """Единый клиент для внешнего API и локального OpenCode."""

    def __init__(self) -> None:
        _load_dotenv()

        self.api_key = _clean_secret(
            os.getenv("LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("API_KEY")
        )
        self.api_base = (
            os.getenv("LLM_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://challenge.up.railway.app/v1"
        ).rstrip("/")
        self.api_model = (
            os.getenv("LLM_MODEL")
            or os.getenv("MODEL_NAME")
            or "deepseek/deepseek-v4.1-flash"
        )

        self.base_url = os.getenv("OPENCODE_URL", "").rstrip("/")
        self.password = os.getenv("OPENCODE_PASSWORD", "")
        self.model = os.getenv("OPENCODE_MODEL", "deepseek-v4.1-flash-free")
        self.session_id: Optional[str] = None
        self._session_lock = asyncio.Lock()
        self._load_service_config()

        if self.api_key:
            self.provider = "api"
        elif self.base_url and self.password:
            self.provider = "opencode"
        else:
            self.provider = ""

        self.enabled = bool(self.provider)
        if self.enabled:
            model = self.api_model if self.provider == "api" else self.model
            logger.info("LLM: провайдер %s, модель %s", self.provider, model)

    def _load_service_config(self) -> None:
        """Читает адрес/пароль фонового OpenCode, не требуя переменных окружения."""
        state_path = Path.home() / ".local" / "state" / "opencode" / "service.json"
        config_path = Path.home() / ".config" / "opencode" / "service.json"

        if not self.base_url and state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                self.base_url = str(state.get("url") or "").rstrip("/")
            except Exception as exc:
                logger.debug("Не удалось прочитать %s: %s", state_path, exc)

        if not self.password:
            for path in (config_path, state_path):
                if not path.exists():
                    continue
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    password = data.get("password")
                    if password:
                        self.password = str(password)
                        break
                except Exception as exc:
                    logger.debug("Не удалось прочитать %s: %s", path, exc)

    def _opencode_auth(self) -> httpx.BasicAuth:
        return httpx.BasicAuth("opencode", self.password)

    async def _ensure_session(self, client: httpx.AsyncClient) -> str:
        if self.session_id:
            return self.session_id

        async with self._session_lock:
            if self.session_id:
                return self.session_id

            response = await client.post(
                f"{self.base_url}/api/session",
                json={
                    "title": "alfa-business-chat",
                    "model": {"id": self.model, "providerID": "opencode"},
                },
                auth=self._opencode_auth(),
            )
            response.raise_for_status()
            self.session_id = response.json()["data"]["id"]
            return self.session_id

    async def _generate_api(self, prompt: str, timeout: float) -> Optional[str]:
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
                    "temperature": 0.2,
                    "max_tokens": 900,
                },
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"] or ""
            return text.strip() or None

    async def _generate_opencode(self, prompt: str, timeout: float) -> Optional[str]:
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    session_id = await self._ensure_session(client)
                    response = await client.post(
                        f"{self.base_url}/api/session/{session_id}/generate",
                        json={"prompt": prompt},
                        auth=self._opencode_auth(),
                    )
                    # Сессия могла исчезнуть после перезапуска OpenCode.
                    if response.status_code == 404 and attempt == 0:
                        self.session_id = None
                        continue
                    response.raise_for_status()
                    text = (response.json().get("data") or {}).get("text") or ""
                    return text.strip() or None
            except Exception as exc:
                self.session_id = None
                logger.warning(
                    "OpenCode недоступен (попытка %s): %s", attempt + 1, exc
                )
        return None

    async def generate(self, prompt: str, timeout: float = 90.0) -> Optional[str]:
        """Возвращает текст ответа модели или None, если LLM недоступна."""
        if not self.enabled:
            return None

        if self.provider == "api":
            try:
                text = await self._generate_api(prompt, timeout)
                if text:
                    return text
            except Exception as exc:
                logger.warning("Внешняя LLM недоступна: %s", exc)

            # Если внешний API не ответил, но локальный OpenCode есть —
            # сохраняем работоспособность чата, а не уходим в пустой ответ.
            if self.base_url and self.password:
                logger.info("Пробую локальный OpenCode после ошибки внешнего API")
                return await self._generate_opencode(prompt, timeout)
            return None

        return await self._generate_opencode(prompt, timeout)


# Совместимость с прежним именем в api/main.py.
OpenCodeLLM = LLMClient
