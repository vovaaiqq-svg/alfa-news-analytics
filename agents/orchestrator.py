"""
Оркестратор агентной системы.
Управляет последовательным выполнением агентов и передачей контекста.
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base_agent import AgentContext
from agents.client_profile_agent import ClientProfileAgent
from agents.news_collector_agent import NewsCollectorAgent
from agents.ranking_agent import RankingAgent
from agents.interpretation_agent import InterpretationAgent
from agents.verification_agent import VerificationAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Оркестратор для управления агентной системой.
    
    Координирует выполнение агентов в правильной последовательности:
    1. Анализ профиля клиента
    2. Сбор и классификация новостей
    3. Ранжирование по значимости
    4. Генерация интерпретаций
    5. Верификация результатов
    """

    def __init__(self, model_name: str = ""):
        self.model_name = model_name
        self.agents = []
        self.logger = logging.getLogger(self.__class__.__name__)

    async def run(
        self,
        client_id: str,
        custom_news: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentContext:
        """
        Запуск полного пайплайна агентной системы.
        
        Args:
            client_id: Идентификатор клиента
            custom_news: Опциональный список новостей для обработки
            
        Returns:
            Итоговый контекст с результатами
        """
        self.logger.info(f"Запуск оркестратора для клиента: {client_id}")
        
        # Инициализация контекста
        context = AgentContext(client_id=client_id)
        
        # Шаг 1: Анализ профиля клиента
        self.logger.info("Шаг 1: Анализ профиля клиента")
        profile_agent = ClientProfileAgent(model_name=self.model_name)
        context = await profile_agent.execute(context)
        
        if not context.client_profile:
            self.logger.error("Не удалось получить профиль клиента")
            return context
        
        # Шаг 2: Сбор и классификация новостей
        self.logger.info("Шаг 2: Сбор и классификация новостей")
        collector_agent = NewsCollectorAgent(model_name=self.model_name)
        context = await collector_agent.execute(context)
        
        # Шаг 3: Ранжирование новостей
        self.logger.info("Шаг 3: Ранжирование новостей")
        ranking_agent = RankingAgent(model_name=self.model_name)
        context = await ranking_agent.execute(context)
        
        # Шаг 4: Генерация интерпретаций
        self.logger.info("Шаг 4: Генерация интерпретаций")
        interpretation_agent = InterpretationAgent(model_name=self.model_name)
        context = await interpretation_agent.execute(context)
        
        # Шаг 5: Верификация результатов
        self.logger.info("Шаг 5: Верификация результатов")
        verification_agent = VerificationAgent(model_name=self.model_name)
        context = await verification_agent.execute(context)
        
        self.logger.info("Оркестратор завершил работу")
        return context

    async def run_with_trace(
        self,
        client_id: str,
    ) -> Dict[str, Any]:
        """
        Запуск с полной трассировкой для отладки.
        
        Args:
            client_id: Идентификатор клиента
            
        Returns:
            Результаты с полной трассировкой
        """
        context = await self.run(client_id)
        return context.to_dict()
