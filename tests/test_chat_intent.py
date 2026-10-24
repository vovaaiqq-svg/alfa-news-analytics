"""
Тесты распознавания темы вопроса и релевантности новостей.
"""

from agents.news_collector_agent import NewsCollectorAgent
from api.main import _is_off_topic, _query_stems, _text_score


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


def test_query_stems_find_news_terms():
    stems = set(_query_stems("Что нового по ключевой ставке?"))
    assert "ключе" in stems
    assert "ставк" in stems


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


def test_news_filter_rejects_religion_and_crime():
    agent = NewsCollectorAgent(model_name="opencode/glm-5.3-flash-free")

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
    agent = NewsCollectorAgent(model_name="opencode/glm-5.3-flash-free")

    assert agent._is_business_relevant({
        "title": "ЦБ не спешит // Пауза в снижении ключевой ставки может затянуться",
        "content": "Совет директоров Банка России сохранил ключевую ставку.",
    })
    assert agent._is_business_relevant({
        "title": "Банк отозвал лицензию из-за отмывания денег",
        "content": "Регулятор применил меры к кредитной организации.",
    })
