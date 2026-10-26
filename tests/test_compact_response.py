"""Проверки компактного ответа /api/analyze для публичного туннеля."""

import gzip
import json
from datetime import datetime

from agents.base_agent import AgentContext, AgentStep
from api.main import _build_analyze_response


def _large_text(size: int = 6000) -> str:
    return ("рыночная аналитика и OCR-текст " * (size // 30 + 1))[:size]


def _interpretation(news_id: str) -> dict:
    text = _large_text()
    return {
        "news_id": news_id,
        "news_title": "Тестовая новость " + news_id,
        "news_url": "https://example.test/news",
        "news_source": "Тест",
        "news_date": "2026-10-26",
        "news_category": "monetary_policy",
        "relevance_score": 5.0,
        "interpretation": {
            "what_happened": text,
            "why_important": text,
            "consequences": text,
            "actions": text,
            "bank_view": text,
            "sources": [text, text, text],
            "risks": [text, text, text],
            "risk_actions": [text, text, text],
            "opportunities": [text, text, text],
            "opportunity_actions": [text, text, text],
            "generation_mode": "local",
        },
        "sources": {
            "news": "Тест",
            "news_url": "https://example.test/news",
            "alfa_analytics": [text, text, text],
        },
        "related_analytics": [
            {
                "id": "a1",
                "title": text,
                "source_file": "fixture.pdf",
                "date": "2026-10-20",
            }
        ],
        "verification": {
            "status": "verified",
            "completeness_score": 10,
            "consistency_score": 10,
            "grounding_score": 10,
            "issues": [text, text],
            "suggestions": [text, text],
        },
    }


def _analytics_insight(analytics_id: str) -> dict:
    text = _large_text()
    return {
        "analytics_id": analytics_id,
        "title": "Аналитическая сводка " + analytics_id,
        "category": "macro_outlook",
        "date": "2026-10-20",
        "summary": text,
        "source_file": "fixture.pdf",
        "interpretation": _interpretation(analytics_id)["interpretation"],
        "sources": {"analytics": "Тест", "source_file": "fixture.pdf"},
        "bank_view": text,
        "verification": {"status": "verified"},
    }


def test_compact_analyze_response_fits_tunnel_limit():
    context = AgentContext(
        client_id="TEST",
        client_profile={
            "client_id": "TEST",
            "raw_data": {"field": _large_text()},
            "industry": "Оптовая торговля",
            "business_scale": "Крупный бизнес",
            "products": ["Кредиты", "РКО"],
            "region": "Курганская область",
            "has_fts": False,
            "risk_factors": [_large_text(200) for _ in range(5)],
            "relevance_criteria": [_large_text(200) for _ in range(5)],
        },
        news_items=[
            {
                "id": f"news_{i}",
                "title": _large_text(500),
                "content": _large_text(),
                "source": "Тест",
                "date": "2026-10-26",
                "category": "monetary_policy",
                "url": "https://example.test/news",
            }
            for i in range(10)
        ],
        ranked_news=[
            {
                "id": f"news_{i}",
                "title": _large_text(500),
                "source": "Тест",
                "category": "monetary_policy",
                "relevance_score": 5.0,
                "relevance_reasoning": _large_text(),
            }
            for i in range(10)
        ],
        interpretations=[
            _interpretation(f"news_{i}") for i in range(3)
        ],
        alfa_analytics=[
            {
                "id": f"alfa_{i}",
                "title": _large_text(500),
                "category": "macro_outlook",
                "date": "2026-10-20",
                "source_file": "fixture.pdf",
                "text": _large_text(),
            }
            for i in range(9)
        ],
        trace=[
            AgentStep(
                step_number=i,
                action=f"step_{i}",
                input_data={"payload": _large_text()},
                output_data={"payload": _large_text()},
                timestamp=datetime.now(),
            )
            for i in range(1, 6)
        ],
        metadata={
            "analytics_insights": [
                _analytics_insight("alfa_1"),
                _analytics_insight("alfa_2"),
            ],
            "verification_summary": {"checked": 3, "verified": 3, "pass_rate": 1.0},
        },
    )

    response = _build_analyze_response(
        context,
        {"legal_entity": "ООО Тест", "industry": "Оптовая торговля"},
        full=False,
    )
    raw = json.dumps(response, ensure_ascii=False).encode("utf-8")
    compressed = gzip.compress(raw, 9)

    assert len(response["news_items"]) == 3
    assert response["news_count"] == 10
    assert len(response["ranked_news"]) == 1
    assert len(response["interpretations"]) == 3
    assert len(response["analytics_insights"]) == 1
    for item in response["interpretations"]:
        interpretation = item["interpretation"]
        assert len(interpretation["what_happened"]) <= 200
        assert len(interpretation["bank_view"]) <= 220
        assert len(interpretation["risks"]) <= 2
    assert len(compressed) < 15_000
    assert len(raw) < 40_000
