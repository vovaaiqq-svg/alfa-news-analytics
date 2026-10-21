"""
Тесты для агентной системы.
"""

import asyncio
import pytest
from agents.orchestrator import AgentOrchestrator


@pytest.mark.asyncio
async def test_full_pipeline():
    """
    Тест полного пайплайна агентной системы.
    """
    orchestrator = AgentOrchestrator(model_name="opencode/glm-5.3-flash-free")
    
    # Запуск анализа для реального клиента
    context = await orchestrator.run("U_67")
    
    # Проверка результатов
    assert context.client_id == "U_67"
    assert context.client_profile is not None
    assert len(context.news_items) > 0
    assert len(context.ranked_news) > 0
    assert len(context.interpretations) > 0
    assert len(context.trace) == 5  # 5 агентов


@pytest.mark.asyncio
async def test_client_profile_agent():
    """
    Тест агента анализа профиля клиента.
    """
    from agents.client_profile_agent import ClientProfileAgent
    from agents.base_agent import AgentContext
    
    agent = ClientProfileAgent(model_name="opencode/glm-5.3-flash-free")
    context = AgentContext(client_id="CLIENT_001")
    
    result = await agent.execute(context)
    
    assert result.client_profile is not None
    assert "industry" in result.client_profile
    assert "products" in result.client_profile


@pytest.mark.asyncio
async def test_news_collector_agent():
    """
    Тест агента сбора новостей.
    """
    from agents.news_collector_agent import NewsCollectorAgent
    from agents.base_agent import AgentContext
    
    agent = NewsCollectorAgent(model_name="opencode/glm-5.3-flash-free")
    context = AgentContext()
    
    result = await agent.execute(context)
    
    assert len(result.news_items) > 0
    assert len(result.alfa_analytics) > 0


@pytest.mark.asyncio
async def test_ranking_agent():
    """
    Тест агента ранжирования.
    """
    from agents.ranking_agent import RankingAgent
    from agents.base_agent import AgentContext
    
    agent = RankingAgent(model_name="opencode/glm-5.3-flash-free")
    context = AgentContext()
    
    # Подготовка тестовых данных
    context.client_profile = {
        "industry": "IT",
        "products": ["RKO", "LOA", "DEP"],
        "regions": ["Москва"],
        "connections": [],
        "risk_factors": [],
    }
    context.news_items = [
        {
            "id": "news_001",
            "title": "Тестовая новость",
            "content": "Содержание новости",
            "classification": {"category": "technology"},
        }
    ]
    
    result = await agent.execute(context)
    
    assert len(result.ranked_news) > 0
    assert "relevance_score" in result.ranked_news[0]


@pytest.mark.asyncio
async def test_interpretation_agent():
    """
    Тест агента интерпретации.
    """
    from agents.interpretation_agent import InterpretationAgent
    from agents.base_agent import AgentContext
    
    agent = InterpretationAgent(model_name="opencode/glm-5.3-flash-free")
    context = AgentContext()
    
    # Подготовка тестовых данных
    context.client_profile = {
        "industry": "IT",
        "products": ["RKO", "LOA"],
        "regions": ["Москва"],
    }
    context.ranked_news = [
        {
            "id": "news_001",
            "title": "Тестовая новость",
            "content": "Содержание",
            "relevance_score": 8.0,
            "source": "Тест",
        }
    ]
    context.alfa_analytics = [
        {
            "id": "alfa_001",
            "title": "Тестовая аналитика",
            "content": "Содержание аналитики",
            "category": "technology",
        }
    ]
    
    result = await agent.execute(context)
    
    assert len(result.interpretations) > 0
    assert "interpretation" in result.interpretations[0]


@pytest.mark.asyncio
async def test_verification_agent():
    """
    Тест агента верификации.
    """
    from agents.verification_agent import VerificationAgent
    from agents.base_agent import AgentContext
    
    agent = VerificationAgent(model_name="opencode/glm-5.3-flash-free")
    context = AgentContext()
    
    # Подготовка тестовых данных
    context.client_profile = {
        "industry": "IT",
        "products": ["RKO"],
    }
    context.interpretations = [
        {
            "news_id": "news_001",
            "news_title": "Тестовая новость",
            "interpretation": {
                "what_happened": "Что-то произошло",
                "why_important": "Это важно",
            },
        }
    ]
    context.alfa_analytics = []
    
    result = await agent.execute(context)
    
    assert len(result.interpretations) > 0
    assert "verification" in result.interpretations[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
