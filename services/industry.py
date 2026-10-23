"""
Справочники для регистрации и определение отрасли по ключевым словам.
"""

from typing import Any, Dict, List, Optional

INDUSTRY_OPTIONS: List[Dict[str, str]] = [
    {
        "key": "construction",
        "label": "Строительство и недвижимость",
        "okved": "Строительство жилых и нежилых зданий",
        "code": "41.20",
    },
    {
        "key": "it",
        "label": "Информационные технологии",
        "okved": "Разработка компьютерного программного обеспечения",
        "code": "62.01",
    },
    {
        "key": "trade",
        "label": "Оптовая и розничная торговля",
        "okved": "Торговля оптовая неспециализированная",
        "code": "46.90",
    },
    {
        "key": "manufacturing",
        "label": "Производство и промышленность",
        "okved": "Производство прочих готовых изделий",
        "code": "32.99",
    },
    {
        "key": "finance",
        "label": "Финансы и страхование",
        "okved": "Деятельность по предоставлению финансовых услуг",
        "code": "64.99",
    },
    {
        "key": "logistics",
        "label": "Логистика и транспорт",
        "okved": "Деятельность грузового автомобильного транспорта",
        "code": "49.41",
    },
    {
        "key": "agriculture",
        "label": "Сельское хозяйство",
        "okved": "Выращивание зерновых культур",
        "code": "01.11",
    },
    {
        "key": "services",
        "label": "Услуги для бизнеса",
        "okved": "Консультирование по вопросам коммерческой деятельности и управления",
        "code": "70.22",
    },
    {
        "key": "energy",
        "label": "Энергетика",
        "okved": "Производство электроэнергии",
        "code": "35.11",
    },
    {
        "key": "medicine",
        "label": "Медицина и фармацевтика",
        "okved": "Общая врачебная практика",
        "code": "86.21",
    },
    {
        "key": "other",
        "label": "Другая сфера",
        "okved": "Консультирование по вопросам коммерческой деятельности и управления",
        "code": "70.22",
    },
]

# Ключевые слова для «другой сферы» — агент сам относит бизнес к отрасли.
INDUSTRY_KEYWORDS: Dict[str, List[str]] = {
    "construction": ["строит", "недвиж", "девелоп", "ремонт", "здани", "коттедж"],
    "it": ["it", "ит", "софт", "программ", "разработ", "цифров", "сайт", "прилож", "данн", "ии", "ai"],
    "trade": ["торгов", "магазин", "опт", "розниц", "продаж", "маркетплейс", "товар"],
    "manufacturing": ["производ", "завод", "фабрик", "металл", "оборуд", "станк", "промышл", "издел"],
    "finance": ["банк", "финанс", "страх", "кредит", "инвест", "лизинг", "платеж"],
    "logistics": ["логист", "транспорт", "перевоз", "склад", "доставк", "груз", "курьер"],
    "agriculture": ["сельск", "агро", "ферм", "растение", "животновод", "урожай", "зерн"],
    "services": ["услуг", "консалт", "юрид", "бухгал", "маркетинг", "реклам", "обучен", "персонал"],
    "energy": ["энерг", "нефт", "газ", "электр", "солнеч", "ветров", "тепло"],
    "medicine": ["медиц", "фарм", "клиник", "лечен", "здоров", "препарат", "аптек"],
}

REGIONS: List[str] = [
    "Москва",
    "Московская область",
    "Санкт-Петербург",
    "Ленинградская область",
    "Свердловская область",
    "Новосибирская область",
    "Республика Татарстан",
    "Краснодарский край",
    "Нижегородская область",
    "Самарская область",
    "Челябинская область",
    "Ростовская область",
    "Республика Башкортостан",
    "Пермский край",
    "Воронежская область",
    "Тюменская область",
    "Красноярский край",
    "Курганская область",
    "Иркутская область",
    "Приморский край",
    "Другая область",
]

REVENUE_OPTIONS: List[Dict[str, Any]] = [
    {"key": "small", "label": "До 300 млн ₽", "amount": 200_000_000, "scale": "Малый бизнес"},
    {"key": "medium", "label": "300 млн – 1 млрд ₽", "amount": 700_000_000, "scale": "Средний бизнес"},
    {"key": "medium_plus", "label": "1–5 млрд ₽", "amount": 3_000_000_000, "scale": "Средний бизнес"},
    {"key": "large", "label": "5–15 млрд ₽", "amount": 10_000_000_000, "scale": "Крупный бизнес"},
    {"key": "xlarge", "label": "15+ млрд ₽", "amount": 25_000_000_000, "scale": "Крупный бизнес"},
]

EMPLOYEES_OPTIONS: List[str] = ["до 15", "16-100", "101-250", "251-1000", "1000+"]

COMPANY_AGE_OPTIONS: List[str] = ["до 3 лет", "3-5", "5-10", "10-16", "16-25", "25+"]

GROWTH_STAGE_OPTIONS: List[str] = [
    "Начальный этап",
    "Растущий бизнес",
    "Зрелый бизнес",
    "Бизнес в новой реальности",
]

PRODUCT_OPTIONS: List[Dict[str, str]] = [
    {"key": "rko", "label": "РКО", "field": "CL_PRODUCT_RKO_MARK"},
    {"key": "loans", "label": "Кредиты", "field": "CL_PRODUCT_LOA_MARK"},
    {"key": "deposits", "label": "Депозиты", "field": "CL_PRODUCT_DEP_MARK"},
    {"key": "guarantees", "label": "Гарантии", "field": "CL_PRODUCT_GAR_MARK"},
    {"key": "leasing", "label": "Лизинг", "field": "CL_PRODUCT_LEA_MARK"},
    {"key": "payroll", "label": "Зарплатный проект", "field": "CL_PRODUCT_ZPP_MARK"},
]


def industry_by_key(key: str) -> Dict[str, str]:
    for item in INDUSTRY_OPTIONS:
        if item["key"] == key:
            return item
    return INDUSTRY_OPTIONS[-1]


def infer_industry(selected_key: str, custom_text: str = "") -> Dict[str, str]:
    """
    Возвращает отрасль по выбранному пункту.
    Для «Другой сферы» пытается определить отрасль по ключевым словам.
    """
    selected_key = (selected_key or "").strip()
    custom_text = (custom_text or "").strip()

    if selected_key and selected_key != "other":
        return industry_by_key(selected_key)

    if not custom_text:
        return industry_by_key("other")

    text = custom_text.lower().replace("ё", "е")
    for key, words in INDUSTRY_KEYWORDS.items():
        if any(word in text for word in words):
            result = dict(industry_by_key(key))
            result["detected_from"] = custom_text
            return result

    result = dict(industry_by_key("other"))
    result["okved"] = custom_text[:120]
    result["detected_from"] = custom_text
    return result


def revenue_by_key(key: str) -> Dict[str, Any]:
    for item in REVENUE_OPTIONS:
        if item["key"] == key:
            return item
    return REVENUE_OPTIONS[1]


def meta_payload() -> Dict[str, Any]:
    """Справочники для фронтенда."""
    return {
        "industries": INDUSTRY_OPTIONS,
        "regions": REGIONS,
        "revenue_options": REVENUE_OPTIONS,
        "employees": EMPLOYEES_OPTIONS,
        "company_age": COMPANY_AGE_OPTIONS,
        "growth_stages": GROWTH_STAGE_OPTIONS,
        "products": PRODUCT_OPTIONS,
    }
