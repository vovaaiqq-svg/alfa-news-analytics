"""
Тесты распознавания темы вопроса и релевантности новостей.
"""

from agents.news_collector_agent import NewsCollectorAgent
from api.main import (
    _alfa_answer,
    _best_fragment,
    _is_off_topic,
    _news_content_score,
    _news_impact,
    _news_title_score,
    _query_stems,
    _text_score,
)


def test_programming_question_is_off_topic():
    assert _is_off_topic("Напиши алгоритм быстрой сортировки")
    assert _is_off_topic("Напиши код на Python")
    assert _is_off_topic("Расскажи анекдот")


def test_business_question_is_not_off_topic():
    assert not _is_off_topic("Что нового по ключевой ставке?")
    assert not _is_off_topic("Напиши, какие риски есть в логистике")


def test_generic_question_has_no_meaningful_stems():
    assert _query_stems("Что нового?") == []
    assert _query_stems("Какие новости бизнеса?") == []
    assert _query_stems("Что нового в моей отрасли?") == []
    assert _query_stems("Какие риски для бизнеса?") == []
    assert _query_stems("Какие события важны для моего бизнеса?") == []


def test_consumer_demand_is_matched_by_news_content():
    score, topics, repeat = _news_content_score(
        "Что происходит с потребительским спросом?",
        "Потребительский спрос восстановился. Спрос поддерживает розничные продажи.",
    )
    assert score > 0
    assert topics >= 2
    assert repeat >= 2


def test_alfa_rate_and_risk_answers_are_different():
    docs = [
        {
            "title": "Ключевая ставка",
            "category": "monetary_policy",
            "date": "2026-10-20",
            "text": "ЦБ сохранил ключевую ставку на уровне 16% годовых. "
                    "Высокая ставка удорожает кредиты и лизинг.",
        },
        {
            "title": "Риски для бизнеса",
            "category": "risks",
            "date": "2026-10-19",
            "text": "Главные риски — рост издержек, кассовые разрывы и "
                    "удорожание оборотного капитала.",
        },
    ]
    profile = {
        "industry": "Оптовая торговля",
        "region": "Курганская область",
        "products": ["Кредит"],
    }
    rate_answer = _alfa_answer("Что будет со ставкой?", docs, profile)
    risk_answer = _alfa_answer("Какие риски вы видите?", docs, profile)
    assert rate_answer != risk_answer
    assert "ставк" in rate_answer.lower()
    assert "риск" in risk_answer.lower()


def test_query_stems_find_news_terms():
    stems = set(_query_stems("Что нового по ключевой ставке?"))
    assert "ключев" in stems
    assert "ставк" in stems


def test_query_stems_do_not_confuse_contraband_with_control():
    assert "контр" not in _query_stems("Что нового по контрафакту?")
    assert "контра" in _query_stems("Что нового по контрафакту?")


def test_text_score_matches_relevant_news_only():
    assert _text_score(
        "Что нового по ключевой ставке?",
        "ЦБ сохранил ключевую ставку на прежнем уровне",
    ) > 0
    assert _text_score(
        "Что нового по логистике?",
        "Рынок логистики вырос на 10%",
    ) > 0
    assert _text_score(
        "Что нового по ключевой ставке?",
        "В РПЦ пояснили причину запрета священникам выступать публично",
    ) == 0


def test_rate_query_does_not_match_substrings_in_unrelated_news():
    question = "Что нового по ключевой ставке?"

    assert _news_title_score(
        question,
        "В «Самокате» появилась доставка из ресторанов",
    ) == 0
    score, topics, repeat = _news_content_score(
        question,
        "РСТ: стоимость визы в Черногорию составит 35 евро",
    )
    assert score == 0
    assert topics == 0
    assert repeat == 0


def test_news_filter_rejects_religion_and_crime():
    agent = NewsCollectorAgent()

    assert not agent._is_business_relevant({
        "title": "В РПЦ пояснили причину запрета священникам выступать публично // религия",
        "content": "В Московском патриархате пояснили, с чем связан запрет.",
    })
    assert not agent._is_business_relevant({
        "title": "В США все отмыто // Россиянина обвинили в легализации теневых денег",
        "content": "Во Флориде перед судом предстал россиянин.",
    })
    assert not agent._is_business_relevant({
        "title": "Анатолий Вороновский зачитался обвинением // Закончено уголовное дело о взятке бывшего депутата",
        "content": "Суд вынес приговор по делу о взятке.",
    })
    assert not agent._is_business_relevant({
        "title": "Минтруд предложил принимать цифровое удостоверение Max при выдаче пенсий",
        "content": "Пенсионеры смогут использовать удостоверение в мессенджере.",
    })
    assert not agent._is_business_relevant({
        "title": "Российские военные ударили по порту Черноморск и сухогрузу под Одессой",
        "content": "По данным местных властей, есть повреждения инфраструктуры.",
    })
    assert not agent._is_business_relevant({
        "title": "Юношеская сборная впервые с 2022 года сыграет на турнире ФИФА с гимном и флагом",
        "content": "Матч пройдет в субботу.",
    })


def test_news_filter_keeps_business_angle():
    agent = NewsCollectorAgent()

    assert agent._is_business_relevant({
        "title": "ЦБ не спешит // Пауза в снижении ключевой ставки может затянуться",
        "content": "Совет директоров Банка России сохранил ключевую ставку.",
    })
    assert agent._is_business_relevant({
        "title": "Банк отозвал лицензию из-за отмывания денег",
        "content": "Регулятор применил меры к кредитной организации.",
    })


def test_best_fragment_skips_ocr_table():
    text = (
        "Заголовок аналитики. "
        "IMOEX 003 26254 (14 net) —__ Ключевая ставка so eet reer et "
        "3500 003 26232 01.2025 18.02.2025 17.04.2025 12.2025 2.07.2025. "
        "ЦБ сохранил ключевую ставку на уровне 14,0%, риторика стала жёстче."
    )
    fragment = _best_fragment(text, {"ставк"}, 300)
    assert "IMOEX" not in fragment
    assert "14,0%" in fragment


def test_news_impact_mentions_client_profile():
    impact = _news_impact(
        {"title": "Продажи выросли", "content": "Потребительский спрос восстановился."},
        {"consequences": ""},
        {"industry": "Оптовая торговля", "region": "Курганская область"},
    )
    assert "Оптовая торговля" in impact
    assert "Курганская область" in impact
