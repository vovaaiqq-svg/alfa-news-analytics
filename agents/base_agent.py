"""
Базовый класс для всех агентов системы новостной аналитики.
Обеспечивает единый интерфейс для работы с LLM и инструментами.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


@dataclass
class AgentStep:
    """Шаг выполнения агента."""
    step_number: int
    action: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class AgentContext:
    """Контекст, передаваемый между агентами."""
    client_id: Optional[str] = None
    client_profile: Optional[Dict[str, Any]] = None
    news_items: List[Dict[str, Any]] = field(default_factory=list)
    ranked_news: List[Dict[str, Any]] = field(default_factory=list)
    interpretations: List[Dict[str, Any]] = field(default_factory=list)
    alfa_analytics: List[Dict[str, Any]] = field(default_factory=list)
    trace: List[AgentStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: AgentStep):
        """Добавить шаг в трассировку."""
        self.trace.append(step)

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            "client_id": self.client_id,
            "client_profile": self.client_profile,
            "news_items": self.news_items,
            "ranked_news": self.ranked_news,
            "interpretations": self.interpretations,
            "alfa_analytics": self.alfa_analytics,
            "trace": [
                {
                    "step_number": s.step_number,
                    "action": s.action,
                    "input_data": s.input_data,
                    "output_data": s.output_data,
                    "timestamp": s.timestamp.isoformat(),
                    "success": s.success,
                    "error_message": s.error_message,
                }
                for s in self.trace
            ],
            "metadata": self.metadata,
        }


class BaseAgent(ABC):
    """Базовый класс для всех агентов."""

    def __init__(self, model_name: str = "opencode/glm-5.3-flash-free", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentContext:
        """Выполнение основной задачи агента."""
        pass

    async def call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Вызов LLM через OpenCode API или в демо-режиме.
        
        Args:
            prompt: Промпт для модели
            system_prompt: Системный промпт
            temperature: Темперара генерации
            max_tokens: Максимальное количество токенов
            response_format: Формат ответа (JSON)
        
        Returns:
            Ответ модели в виде словаря
        """
        # Проверяем, доступен ли реальный API
        if await self._is_api_available():
            return await self._call_real_api(
                prompt, system_prompt, temperature, max_tokens, response_format
            )
        else:
            # Демо-режим
            return self._fallback_response(prompt)

    async def _is_api_available(self) -> bool:
        """Проверка доступности OpenCode API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://localhost:3000/v1/models",
                    timeout=2.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def _call_real_api(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict],
    ) -> Dict[str, Any]:
        """Вызов реального OpenCode API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:3000/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120.0,
            )
            response.raise_for_status()
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"text": content}

    def _fallback_response(self, prompt: str) -> Dict[str, Any]:
        """
        Резервный ответ для демонстрации при недоступности API.
        Возвращает структурированные данные для демонстрации работы системы.
        """
        # Определяем тип запроса по ключевым словам
        prompt_lower = prompt.lower()
        
        if "проанализируй профиль" in prompt_lower or "client_profile" in prompt_lower:
            return {
                "industry": "Информационные технологии",
                "business_scale": "Средний бизнес (выручка 2.5 млрд руб.)",
                "key_features": {
                    "okved": "Разработка ПО",
                    "employees": "50-100",
                    "company_age": "5-10 лет",
                    "growth_stage": "Растущий бизнес",
                },
                "products": ["RKO", "Кредиты", "Депозиты", "Зарплатный проект"],
                "regions": ["Москва"],
                "connections": [],
                "risk_factors": ["Зависимость от заемного финансирования", "Технологические риски"],
                "relevance_criteria": ["IT-новости", "Кредитные ставки", "Технологические тренды"],
            }
        
        elif "классифицируй" in prompt_lower or "классификац" in prompt_lower:
            return {
                "category": "technology",
                "key_facts": {
                    "who": "Регулятор / Компания",
                    "what": "Изменение в отрасли",
                    "when": "Сентябрь 2026",
                    "why": "Макроэкономические причины",
                },
                "business_impact": "positive",
                "affected_industries": ["IT", "Финансы"],
            }
        
        elif "оцени релевантность" in prompt_lower or "ранжир" in prompt_lower:
            return {
                "rankings": [
                    {
                        "news_id": "news_005",
                        "total_score": 9.2,
                        "industry_impact": 9,
                        "product_impact": 8,
                        "region_impact": 8,
                        "supply_chain_impact": 7,
                        "overall_significance": 10,
                        "reasoning": "IT-сектор напрямую связан с отраслью клиента",
                    },
                    {
                        "news_id": "news_001",
                        "total_score": 7.5,
                        "industry_impact": 6,
                        "product_impact": 9,
                        "region_impact": 7,
                        "supply_chain_impact": 5,
                        "overall_significance": 8,
                        "reasoning": "Ключевая ставка влияет на кредитные продукты клиента",
                    },
                    {
                        "news_id": "news_002",
                        "total_score": 6.8,
                        "industry_impact": 6,
                        "product_impact": 7,
                        "region_impact": 6,
                        "supply_chain_impact": 5,
                        "overall_significance": 7,
                        "reasoning": "Инфляция влияет на финансовое планирование",
                    },
                ]
            }
        
        elif "интерпретац" in prompt_lower or "interpretation" in prompt_lower:
            return {
                "what_happened": "Совет директоров Банка России сохранил ключевую ставку на уровне 14% годовых, что стало первой паузой в цикле смягчения денежно-кредитной политики.",
                "why_important": "Для компании с кредитными продуктами это означает сохранение высокой стоимости заемного финансирования. Период удешевления кредитов приостановлен, что влияет на финансовую нагрузку бизнеса.",
                "consequences": "Сохранение высоких ставок может ограничить возможности по рефинансированию существующих кредитов. Рекомендуется рассмотреть возможность досрочного погашения или реструктуризации кредитов.",
                "actions": "Рекомендуется: 1) Пересчитать график платежей и проверить ковенанты, 2) Сравнить рефинансирование с действующими условиями, 3) Зафиксировать ставку или выбрать кредит с досрочным погашением.",
                "bank_view": "Альфа-Банк оценивает это как сигнал о сохранении жесткой денежно-кредитной политики. Рекомендуем клиентам с кредитными продуктами активно управлять долговой нагрузкой.",
                "sources": ["Банк России", "Внутренняя аналитика Альфа-Банка"],
            }
        
        elif "верифик" in prompt_lower or "провер" in prompt_lower:
            return {
                "status": "verified",
                "completeness_score": 8.5,
                "consistency_score": 9.0,
                "grounding_score": 8.0,
                "issues": [],
                "suggestions": ["Добавить больше конкретных цифр", "Усилить ссылки на источники"],
            }
        
        # Общий ответ по умолчанию
        return {
            "text": "[DEMO MODE] Агент обработал запрос. В реальном режиме здесь будет ответ LLM на основе GLM-5.3-Flash или DeepSeek-V4.1-Flash.",
            "status": "demo",
        }

    def create_step(
        self,
        step_number: int,
        action: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AgentStep:
        """Создание шага трассировки."""
        return AgentStep(
            step_number=step_number,
            action=action,
            input_data=input_data,
            output_data=output_data,
            success=success,
            error_message=error_message,
        )
