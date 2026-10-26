"""
Тесты для агентной системы.
"""

import pytest
from agents.news_collector_agent import NewsCollectorAgent
from agents.orchestrator import AgentOrchestrator


def _fixture_news():
    return [
        {
            "id": "fixture_rate",
            "title": "ЦБ сохранил ключевую ставку на уровне 14%",
            "content": (
                "Совет директоров Банка России сохранил ключевую ставку "
                "на уровне 14% годовых. Риторика регулятора остаётся жёсткой."
            ),
            "source": "Банк России",
            "date": "2026-09-11",
            "category": "monetary_policy",
            "url": "https://www.cbr.ru/press/",
            "is_real": False,
        }
    ]


def _fixture_analytics():
    return [
        {
            "id": "fixture_alfa_rate",
            "title": "Ключевая ставка ЦБ РФ",
            "category": "monetary_policy",
            "date": "2026-09-11",
            "source_file": "fixture.pdf",
            "text": (
                "ЦБ сохранил ключевую ставку на уровне 14,0%. "
                "Инфляция замедляется медленнее прогноза."
            ),
        }
    ]


@pytest.mark.asyncio
async def test_full_pipeline(monkeypatch):
    """
    Тест полного пайплайна агентной системы на синтетических данных.
    """
    async def fake_external(self):
        return _fixture_news()

    async def fake_analytics(self):
        return _fixture_analytics()

    monkeypatch.setattr(NewsCollectorAgent, "_collect_external_news", fake_external)
    monkeypatch.setattr(NewsCollectorAgent, "_collect_alfa_analytics", fake_analytics)

    orchestrator = AgentOrchestrator()
    context = await orchestrator.run("CLIENT_001")

    assert context.client_id == "CLIENT_001"
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
    
    agent = ClientProfileAgent()
    context = AgentContext(client_id="CLIENT_001")
    
    result = await agent.execute(context)
    
    assert result.client_profile is not None
    assert "industry" in result.client_profile
    assert "products" in result.client_profile


@pytest.mark.asyncio
async def test_news_collector_agent(monkeypatch):
    """
    Тест агента сбора новостей на синтетических данных.
    """
    from agents.base_agent import AgentContext

    async def fake_external(self):
        return _fixture_news()

    async def fake_analytics(self):
        return _fixture_analytics()

    monkeypatch.setattr(NewsCollectorAgent, "_collect_external_news", fake_external)
    monkeypatch.setattr(NewsCollectorAgent, "_collect_alfa_analytics", fake_analytics)

    agent = NewsCollectorAgent()
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
    
    agent = RankingAgent()
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
    
    agent = InterpretationAgent()
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
    
    agent = VerificationAgent()
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
