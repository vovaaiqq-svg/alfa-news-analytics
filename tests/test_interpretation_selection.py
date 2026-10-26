"""
Тесты выбора аналитики Альфа-Банка и разделения источников.

Проверяем два важных свойства:
1. Аналитика банка не привязывается к любой новости только по категории.
2. В блоке позиции банка есть реальный фрагмент аналитики, а разбор
   явно отделён от него.
"""

from agents.interpretation_agent import InterpretationAgent


def test_commodity_analytics_are_not_cross_linked():
    agent = InterpretationAgent()
    news = {
        "id": "news_oil",
        "title": "Нефть Brent обновила полугодовой максимум",
        "content": "Цена нефти выросла на фоне ограничения поставок.",
        "classification": {"category": "commodities"},
        "category": "commodities",
    }
    analytics = [
        {
            "id": "alfa_gold",
            "title": "Обзор рынка золота, август 2026",
            "category": "commodities",
            "text": "Золото выросло за август, драгметалл показал лучший результат.",
        }
    ]

    assert agent._find_relevant_analytics(news, analytics) == []


def test_bank_view_contains_expert_excerpt_and_local_disclaimer():
    agent = InterpretationAgent()
    news = {
        "id": "news_rate",
        "title": "ЦБ сохранил ключевую ставку",
        "content": "Инфляция остаётся повышенной, ставка сохранена.",
        "classification": {"category": "inflation"},
        "category": "inflation",
    }
    analytics = [
        {
            "id": "alfa_rate",
            "title": "Ключевая ставка ЦБ РФ",
            "category": "monetary_policy",
            "text": "Ставка сохранена на уровне 14,0%, риторика стала жёстче. "
                    "Инфляция замедляется медленнее прогноза.",
        }
    ]

    relevant = agent._find_relevant_analytics(news, analytics)
    assert relevant

    interpretation = agent._generate_local_interpretation(
        news,
        {"industry": "Оптовая торговля", "products": ["Кредиты"]},
        relevant,
    )
    assert "14,0%" in interpretation["bank_view"]
    assert "локальными правилами" in interpretation["bank_view"]
    assert interpretation["generation_mode"] == "local"
