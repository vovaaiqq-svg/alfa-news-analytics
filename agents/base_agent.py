"""
Базовые структуры агентной системы новостной аналитики.

Здесь нет вызовов LLM: агенты работают с локальными эвристиками, а
генерация текста вынесена в отдельный сервис `services.llm.LLMClient`.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


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

    def __init__(self, model_name: str = ""):
        self.model_name = model_name
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_step(
        self,
        step_number: int,
        action: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AgentStep:
        """Создаёт шаг трассировки с единым форматом."""
        return AgentStep(
            step_number=step_number,
            action=action,
            input_data=input_data,
            output_data=output_data,
            success=success,
            error_message=error_message,
        )

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentContext:
        """Выполнение основной задачи агента."""
        pass
