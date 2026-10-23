"""
Агент генерации персонализированной интерпретации событий.
Объясняет влияние новостей на бизнес клиента с учетом контекста и аналитики Альфа-Банка.
"""

import json
from typing import Any, Dict, List

from agents.base_agent import AgentContext, BaseAgent


class InterpretationAgent(BaseAgent):
    """
    Агент для создания персонализированных интерпретаций значимых событий.
    
    Формирует ответы на вопросы:
    1. Что произошло?
    2. Почему это важно для этой компании?
    3. Какие последствия возможны?
    4. Какие действия могут быть релевантны?
    5. Как это оценивает банк?
    6. На чем основан вывод?
    """

    async def execute(self, context: AgentContext) -> AgentContext:
        """
        Генерация персонализированных интерпретаций.
        
        Args:
            context: Контекст с профилем клиента и ранжированными новостями
            
        Returns:
            Обновленный контекст с интерпретациями
        """
        self.logger.info("Генерация персонализированных интерпретаций")
        
        if not context.ranked_news:
            self.logger.warning("Нет новостей для интерпретации")
            return context
        
        interpretations = []
        
        for news_item in context.ranked_news[:5]:  # Топ-5 новостей
            try:
                interpretation = await self._generate_interpretation(
                    news_item,
                    context.client_profile,
                    context.alfa_analytics,
                )
                interpretations.append(interpretation)
            except Exception as e:
                self.logger.error(f"Ошибка интерпретации новости {news_item['id']}: {e}")
        
        context.interpretations = interpretations

        # Карточки по аналитике Альфа-Банка (для блока «Риски и возможности»)
        context.metadata["analytics_insights"] = self.build_analytics_insights(
            context.alfa_analytics,
            context.client_profile or {},
            limit=2,
        )
        
        # Трассировка
        step = self.create_step(
            step_number=4,
            action="generate_interpretations",
            input_data={
                "news_count": len(context.ranked_news),
                "client_industry": context.client_profile.get("industry", "")[:80] if context.client_profile else None,
                "client_products": context.client_profile.get("products", []) if context.client_profile else [],
                "client_region": context.client_profile.get("region", "") if context.client_profile else "",
                "client_has_fts": context.client_profile.get("has_fts", False) if context.client_profile else False,
                "risk_factors": context.client_profile.get("risk_factors", []) if context.client_profile else [],
                "alfa_analytics_available": len(context.alfa_analytics),
            },
            output_data={
                "interpretations_count": len(interpretations),
                "analytics_insights_count": len(context.metadata.get("analytics_insights", [])),
                "interpretations": [
                    {
                        "news_id": i.get("news_id"),
                        "news_title": i.get("news_title", "")[:80],
                        "relevance_score": i.get("relevance_score", 0),
                        "used_alfa_analytics": i.get("sources", {}).get("alfa_analytics", []),
                        "has_all_sections": all(i.get("interpretation", {}).get(k) for k in ["what_happened", "why_important", "consequences", "actions", "bank_view", "risks", "opportunities"]),
                        "risks_count": len(i.get("interpretation", {}).get("risks", [])),
                        "opportunities_count": len(i.get("interpretation", {}).get("opportunities", [])),
                    }
                    for i in interpretations
                ],
            },
        )
        context.add_step(step)
        
        self.logger.info(f"Сгенерировано {len(interpretations)} интерпретаций")
        return context

    async def _generate_interpretation(
        self,
        news_item: Dict[str, Any],
        client_profile: Dict[str, Any],
        alfa_analytics: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Генерация интерпретации для одной новости на основе реальных данных.
        
        Args:
            news_item: Новость
            client_profile: Профиль клиента
            alfa_analytics: Аналитические материалы Альфа-Банка
            
        Returns:
            Персонализированная интерпретация
        """
        # Поиск релевантной аналитики Альфа-Банка
        relevant_analytics = self._find_relevant_analytics(
            news_item,
            alfa_analytics,
        )
        
        # Генерация интерпретации на основе реальных данных
        interpretation = self._generate_local_interpretation(
            news_item,
            client_profile,
            relevant_analytics,
        )
        
        return {
            "news_id": news_item["id"],
            "news_title": news_item.get("title", ""),
            "news_url": news_item.get("url", ""),
            "news_source": news_item.get("source", ""),
            "news_date": news_item.get("date", ""),
            "news_category": news_item.get("category", ""),
            "relevance_score": news_item.get("relevance_score", 0),
            "interpretation": interpretation,
            "sources": {
                "news": news_item.get("source", ""),
                "news_url": news_item.get("url", ""),
                "alfa_analytics": [a.get("title", "") for a in relevant_analytics],
            },
        }
    
    def _generate_local_interpretation(
        self,
        news_item: Dict[str, Any],
        client_profile: Dict[str, Any],
        relevant_analytics: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Локальная генерация интерпретации на основе реальных данных клиента.
        """
        # Извлекаем данные клиента
        industry = client_profile.get("industry", "")
        products = client_profile.get("products", [])
        region = client_profile.get("region", "")
        has_fts = client_profile.get("has_fts", False)
        fts_country = client_profile.get("fts_country", "")
        revenue = client_profile.get("revenue", "")
        workers = client_profile.get("workers", "")
        risk_factors = client_profile.get("risk_factors", [])
        
        # Извлекаем данные новости
        title = news_item.get("title", "")
        content = news_item.get("content", "")
        category = news_item.get("category", "")
        source = news_item.get("source", "")
        forced_advice_category = news_item.get("forced_advice_category")
        advice_category = forced_advice_category or category
        category_text = f"{title} {content}".lower()
        if not forced_advice_category:
            if "лизинг" in category_text:
                advice_category = "leasing"
            elif "ключев" in category_text and "ставк" in category_text:
                advice_category = "monetary_policy"
            elif any(word in category_text for word in ("fesco", "рейс", "доставк", "логист", "перевозк")):
                advice_category = "trade"
            elif any(word in category_text for word in ("гчп", "концесс", "инфраструктурн")):
                advice_category = "macro_outlook"
            elif "инвестиц" in category_text and ("млрд" in category_text or "экономик" in category_text):
                advice_category = "macro_outlook"
            elif category in {"banking", "macro_outlook"}:
                advice_category = "monetary_policy"
        
        # Формируем интерпретацию
        what_happened = f"{title}. {content}"
        
        # Почему это важно для компании
        why_important_parts = []
        
        if industry:
            why_important_parts.append(f"Для компании из отрасли «{industry}»")
        
        if products:
            why_important_parts.append(f"с продуктами: {', '.join(products)}")
        
        if region:
            why_important_parts.append(f"в регионе {region}")
        
        if has_fts and fts_country:
            why_important_parts.append(f"с внешнеэкономической деятельностью (страна: {fts_country})")
        
        why_important = " ".join(why_important_parts) + "." if why_important_parts else "Для вашей компании."
        
        # Добавляем специфику по категории
        if advice_category == "monetary_policy":
            why_important += " Изменение ключевой ставки напрямую влияет на стоимость заемного финансирования."
            if "Кредитные продукты" in products:
                why_important += " У вас есть кредитные продукты, поэтому изменение ставки критически важно."
        
        elif advice_category == "inflation":
            why_important += " Инфляция влияет на издержки и ценообразование."
        
        elif advice_category == "currency":
            why_important += " Изменение валютного курса влияет на стоимость импорта и экспорта."
            if has_fts:
                why_important += " У вас есть внешнеэкономическая деятельность, поэтому курс валют особенно важен."
        
        elif advice_category == "agriculture":
            why_important += " Сельскохозяйственные новости влияют на цены на сырье и продукты."

        elif advice_category == "leasing":
            why_important += " Лизинг чувствителен к стоимости фондирования и готовности клиентов обновлять парк."

        elif advice_category == "trade":
            why_important += " Логистика и скорость поставок напрямую влияют на выручку и оборачиваемость."

        elif advice_category == "macro_outlook":
            why_important += " Макроусловия определяют стоимость капитала и горизонт планирования."
        
        elif advice_category == "technology":
            why_important += " Технологические новости влияют на конкурентоспособность и инновации."
        
        # Последствия
        consequences_parts = []
        
        if risk_factors:
            consequences_parts.append(f"Факторы риска: {', '.join(risk_factors)}.")
        
        if advice_category == "monetary_policy":
            consequences_parts.append("Сохранение высоких ставок может ограничить возможности по рефинансированию кредитов.")
            consequences_parts.append("Рекомендуется рассмотреть досрочное погашение или реструктуризацию кредитов.")
        
        elif advice_category == "inflation":
            consequences_parts.append("Инфляция может привести к росту издержек и снижению маржинальности.")
            consequences_parts.append("Рекомендуется пересмотреть ценообразование и контракты с поставщиками.")
        
        elif advice_category == "currency":
            consequences_parts.append("Изменение курса может повлиять на стоимость импортных товаров и услуг.")
            consequences_parts.append("Рекомендуется рассмотреть хеджирование валютных рисков.")
        
        elif advice_category == "agriculture":
            consequences_parts.append("Изменение цен на сельхозпродукцию может повлиять на издержки.")
            consequences_parts.append("Рекомендуется рассмотреть долгосрочные контракты с поставщиками.")

        elif advice_category == "leasing":
            consequences_parts.append("Высокие ставки удорожают лизинг и могут замедлить обновление парка.")
            consequences_parts.append("Клиенты чаще сравнивают лизинг с покупкой и откладывают сделки.")

        elif advice_category == "trade":
            consequences_parts.append("Сбои в логистике могут привести к кассовым разрывам и потере клиентов.")
            consequences_parts.append("Рост тарифов снижает маржу в краткосрочных контрактах.")

        elif advice_category == "macro_outlook":
            consequences_parts.append("Макронеопределённость усложняет бюджетирование и инвестиционные решения.")
            consequences_parts.append("Стоимость капитала может ограничить запуск новых проектов.")
        
        elif advice_category == "technology":
            consequences_parts.append("Технологические изменения могут создать новые возможности или угрозы.")
            consequences_parts.append("Рекомендуется следить за технологическими трендами и инновациями.")
        
        consequences = " ".join(consequences_parts) if consequences_parts else "Последствия зависят от конкретных условий вашего бизнеса."
        
        # Рекомендации
        actions_parts = []
        
        if advice_category == "monetary_policy":
            actions_parts.append("Пересмотреть кредитный портфель")
            actions_parts.append("Рассмотреть альтернативные источники финансирования")
            actions_parts.append("Обратиться к персональному менеджеру для оптимизации условий")
        
        elif advice_category == "inflation":
            actions_parts.append("Пересмотреть ценообразование")
            actions_parts.append("Оптимизировать издержки")
            actions_parts.append("Рассмотреть долгосрочные контракты с поставщиками")
        
        elif advice_category == "currency":
            actions_parts.append("Рассмотреть хеджирование валютных рисков")
            actions_parts.append("Диверсифицировать поставщиков")
            actions_parts.append("Пересмотреть контракты с иностранными контрагентами")
        
        elif advice_category == "agriculture":
            actions_parts.append("Рассмотреть долгосрочные контракты с поставщиками")
            actions_parts.append("Диверсифицировать каналы сбыта")
            actions_parts.append("Следить за ценами на сырье")

        elif advice_category == "leasing":
            actions_parts.append("Пересчитать ставки и графики по новым сделкам")
            actions_parts.append("Предложить клиентам trade-in и рассрочку")
            actions_parts.append("Зафиксировать условия с поставщиками оборудования")

        elif advice_category == "trade":
            actions_parts.append("Диверсифицировать маршруты и перевозчиков")
            actions_parts.append("Пересмотреть страховой запас на складе")
            actions_parts.append("Зафиксировать тарифы на ключевые направления")

        elif advice_category == "macro_outlook":
            actions_parts.append("Пересмотреть инвестиционный бюджет")
            actions_parts.append("Проверить доступные меры господдержки")
            actions_parts.append("Подготовить сценарии ликвидности")
        
        elif advice_category == "technology":
            actions_parts.append("Инвестировать в технологические инновации")
            actions_parts.append("Обучать сотрудников новым технологиям")
            actions_parts.append("Следить за конкурентами и их технологическими решениями")
        
        actions = "Рекомендуется: " + ", ".join(actions_parts) + "." if actions_parts else "Рекомендуется проконсультироваться с персональным менеджером."
        
        # Позиция банка
        bank_view_parts = []
        
        if relevant_analytics:
            bank_view_parts.append("Согласно аналитике Альфа-Банка:")
            for analytics in relevant_analytics[:2]:
                bank_view_parts.append(f"- {analytics.get('title', '')}")
        
        bank_view_parts.append("Альфа-Банк рекомендует клиентам активно управлять рисками и использовать возможности, которые создают макроэкономические изменения.")
        
        bank_view = " ".join(bank_view_parts)
        
        # Источники
        sources = [source]
        if relevant_analytics:
            sources.extend([a.get("title", "") for a in relevant_analytics[:2]])

        # Риски / возможности в формате для карточек
        advice = self._build_advice(
            category=advice_category,
            client_profile=client_profile,
            title=title,
        )
        
        return {
            "what_happened": what_happened,
            "why_important": why_important,
            "consequences": consequences,
            "actions": actions,
            "bank_view": bank_view,
            "sources": sources,
            "risks": advice["risks"],
            "risk_actions": advice["risk_actions"],
            "opportunities": advice["opportunities"],
            "opportunity_actions": advice["opportunity_actions"],
        }

    def _build_advice(
        self,
        category: str,
        client_profile: Dict[str, Any],
        title: str = "",
    ) -> Dict[str, List[str]]:
        """
        Формирует конкретные риски и возможности по категории события.
        Это не общие фразы, а прикладные сценарии для бизнеса клиента.
        """
        industry = client_profile.get("industry", "")
        products = client_profile.get("products", [])
        region = client_profile.get("region", "")
        has_fts = client_profile.get("has_fts", False)
        has_credit = "Кредитные продукты" in products
        has_leasing = "Лизинговые продукты" in products

        advice_map = {
            "monetary_policy": {
                "risks": [
                    "Удорожание заёмного финансирования и обслуживания кредитного портфеля.",
                    "Снижение инвестиционной активности и спроса у клиентов.",
                    "Давление на маржинальность при высокой стоимости денег.",
                ],
                "risk_actions": [
                    "Пересчитать кредитный портфель и график платежей.",
                    "Зафиксировать ставки по действующим кредитам, где это возможно.",
                    "Сформировать резерв ликвидности на 3–6 месяцев.",
                ],
                "opportunities": [
                    "Размещение свободной ликвидности по повышенным ставкам.",
                    "Уход конкурентов с дорогим финансированием освобождает долю рынка.",
                    "Рост спроса клиентов на реструктуризацию и хеджирование.",
                ],
                "opportunity_actions": [
                    "Пересмотреть депозитную политику и разместить свободные средства.",
                    "Предложить клиентам программы рассрочки и лизинга.",
                    "Подготовить сценарии рефинансирования для ключевых клиентов.",
                ],
            },
            "leasing": {
                "risks": [
                    "Удорожание фондирования повышает лизинговые платежи для клиентов.",
                    "Клиенты откладывают обновление парка и оборудования.",
                    "Растут требования к авансу и обеспечению по новым сделкам.",
                ],
                "risk_actions": [
                    "Пересчитать ставки и графики по новым лизинговым сделкам.",
                    "Предложить клиентам trade-in и рассрочку платежей.",
                    "Зафиксировать условия с поставщиками оборудования.",
                ],
                "opportunities": [
                    "При дорогих кредитах лизинг выигрывает у прямой покупки.",
                    "Растёт спрос на подержанную технику и trade-in.",
                    "Клиенты ищут предсказуемые фиксированные платежи.",
                ],
                "opportunity_actions": [
                    "Запустить программу trade-in для ключевых сегментов.",
                    "Подготовить предложения с фиксированной ставкой.",
                    "Сфокусироваться на клиентах, обновляющих парк.",
                ],
            },
            "inflation": {
                "risks": [
                    "Рост себестоимости закупок, логистики и фонда оплаты труда.",
                    "Сжатие маржи при фиксированных ценах в долгосрочных контрактах.",
                    "Рост дебиторской задолженности и кассовых разрывов.",
                ],
                "risk_actions": [
                    "Пересмотреть цены и условия долгосрочных контрактов.",
                    "Индексировать закупочные договоры и аренду.",
                    "Оптимизировать складские запасы и логистику.",
                ],
                "opportunities": [
                    "Клиенты готовы платить за скорость и надёжность поставок.",
                    "Инфляционный рост цен позволяет увеличить средний чек.",
                    "Появляется спрос на инструменты защиты сбережений.",
                ],
                "opportunity_actions": [
                    "Упаковать премиальные условия сервиса.",
                    "Предложить клиентам депозиты и инвестиционные продукты.",
                    "Пересмотреть ассортимент в пользу маржинальных позиций.",
                ],
            },
            "currency": {
                "risks": [
                    "Валютные колебания увеличивают стоимость импорта и оборудования.",
                    "Курсовые разницы давят на маржу и отчётность.",
                    "Неопределённость усложняет планирование закупок.",
                ],
                "risk_actions": [
                    "Хеджировать валютные риски и зафиксировать курс в контрактах.",
                    "Диверсифицировать поставщиков и валюты расчётов.",
                    "Создать валютный резерв на 3 месяца.",
                ],
                "opportunities": [
                    "Ослабление рубля повышает конкурентоспособность экспорта.",
                    "Клиенты с валютной выручкой могут нарастить обороты.",
                    "Растёт спрос на валютный контроль и хеджирование.",
                ],
                "opportunity_actions": [
                    "Предложить экспортёрам валютные депозиты и хеджи.",
                    "Пересмотреть ценовую политику для импортных категорий.",
                    "Подготовить сценарии для разных курсов.",
                ],
            },
            "agriculture": {
                "risks": [
                    "Рост цен на сырьё, удобрения и ГСМ.",
                    "Погодные риски и сезонность выручки.",
                    "Логистические ограничения и потери при хранении.",
                ],
                "risk_actions": [
                    "Заключить долгосрочные контракты на поставку.",
                    "Застраховать урожай и запасы.",
                    "Диверсифицировать каналы сбыта.",
                ],
                "opportunities": [
                    "Рост спроса на продовольствие и агротехнологии.",
                    "Экспортные ниши для продукции с высокой добавленной стоимостью.",
                    "Льготное финансирование и меры господдержки.",
                ],
                "opportunity_actions": [
                    "Подготовить экспортные контракты.",
                    "Использовать льготные программы финансирования.",
                    "Инвестировать в хранение и переработку.",
                ],
            },
            "technology": {
                "risks": [
                    "Технологическое отставание от конкурентов.",
                    "Киберриски и зависимость от внешних подрядчиков.",
                    "Рост стоимости ИТ-инфраструктуры и кадров.",
                ],
                "risk_actions": [
                    "Провести аудит ИТ-инфраструктуры и доступов.",
                    "Диверсифицировать поставщиков ПО.",
                    "Обучить сотрудников кибергигиене.",
                ],
                "opportunities": [
                    "Автоматизация снижает издержки и ошибки.",
                    "Новые цифровые каналы продаж и удержания клиентов.",
                    "Рост спроса на ИИ-решения и аналитику.",
                ],
                "opportunity_actions": [
                    "Запустить пилот автоматизации на одном процессе.",
                    "Оцифровать клиентский путь.",
                    "Инвестировать в данные и аналитику.",
                ],
            },
            "regulation": {
                "risks": [
                    "Новые требования увеличивают операционные издержки.",
                    "Риск штрафов и приостановки деятельности.",
                    "Необходимость перестройки процессов и документооборота.",
                ],
                "risk_actions": [
                    "Провести комплаенс-аудит.",
                    "Обновить регламенты и назначить ответственных.",
                    "Согласовать план с юристами и банком.",
                ],
                "opportunities": [
                    "Раннее соответствие требованиям даёт преимущество.",
                    "Появляются новые рынки и партнёры.",
                    "Можно предложить клиентам комплаенс-услуги.",
                ],
                "opportunity_actions": [
                    "Подготовить дорожную карту соответствия.",
                    "Упаковать опыт в отдельную услугу.",
                    "Выйти на новые сегменты.",
                ],
            },
            "real_estate": {
                "risks": [
                    "Высокие ставки давят на ипотеку и инвестиционный спрос.",
                    "Рост стоимости строительства и материалов.",
                    "Замедление продаж и рост сроков окупаемости.",
                ],
                "risk_actions": [
                    "Пересмотреть график проектов и бюджет.",
                    "Оптимизировать себестоимость строительства.",
                    "Использовать рассрочку и субсидированные программы.",
                ],
                "opportunities": [
                    "Снижение конкуренции на земельном рынке.",
                    "Спрос на аренду и готовое жильё.",
                    "Новые ниши в коммерческой недвижимости.",
                ],
                "opportunity_actions": [
                    "Искать площадки с дисконтом.",
                    "Развивать арендные продукты.",
                    "Предложить клиентам рассрочку.",
                ],
            },
            "ecommerce": {
                "risks": [
                    "Рост стоимости логистики и возвратов.",
                    "Усиление конкуренции и демпинга на маркетплейсах.",
                    "Зависимость от одной площадки.",
                ],
                "risk_actions": [
                    "Пересчитать юнит-экономику.",
                    "Диверсифицировать каналы продаж.",
                    "Оптимизировать возвраты и упаковку.",
                ],
                "opportunities": [
                    "Рост онлайн-спроса в регионах.",
                    "Новые ниши и товарные категории.",
                    "Собственный канал продаж повышает маржу.",
                ],
                "opportunity_actions": [
                    "Запустить D2C-канал.",
                    "Расширить географию доставки.",
                    "Инвестировать в удержание клиентов.",
                ],
            },
            "trade": {
                "risks": [
                    "Рост логистических издержек и тарифов на перевозку.",
                    "Срывы поставок и зависимость от одного маршрута.",
                    "Замедление спроса и рост складских запасов.",
                ],
                "risk_actions": [
                    "Диверсифицировать маршруты и перевозчиков.",
                    "Зафиксировать тарифы на ключевые направления.",
                    "Пересмотреть страховой запас и складскую логистику.",
                ],
                "opportunities": [
                    "Новые маршруты и партнёры снижают стоимость доставки.",
                    "Растёт спрос на быстрые и предсказуемые поставки.",
                    "Можно предложить клиентам гибкие условия.",
                ],
                "opportunity_actions": [
                    "Протестировать новый маршрут на одном направлении.",
                    "Запустить тариф с фиксированной стоимостью.",
                    "Инвестировать в складскую инфраструктуру.",
                ],
            },
            "macro_outlook": {
                "risks": [
                    "Рост стоимости капитала и конкуренция за инвестиции.",
                    "Неопределённость бюджета и сроков проектов.",
                    "Давление на маржу из-за макроусловий.",
                ],
                "risk_actions": [
                    "Пересмотреть инвестиционный бюджет.",
                    "Разбить проекты на этапы и зафиксировать приоритеты.",
                    "Сформировать резерв ликвидности.",
                ],
                "opportunities": [
                    "Господдержка и инфраструктурные проекты открывают спрос.",
                    "Доступ к долгосрочному финансированию.",
                    "Рост деловой активности в регионах.",
                ],
                "opportunity_actions": [
                    "Проверить доступные меры господдержки.",
                    "Подготовить заявку на финансирование.",
                    "Искать партнёров в инфраструктурных проектах.",
                ],
            },
            "commodities": {
                "risks": [
                    "Волатильность цен на сырьё и материалы.",
                    "Рост транспортных расходов.",
                    "Зависимость от экспортных пошлин и логистики.",
                ],
                "risk_actions": [
                    "Хеджировать цены на ключевое сырьё.",
                    "Диверсифицировать поставщиков.",
                    "Пересмотреть условия контрактов.",
                ],
                "opportunities": [
                    "Рост цен на продукцию увеличивает выручку.",
                    "Новые рынки сбыта.",
                    "Спрос на переработку и глубокую переработку.",
                ],
                "opportunity_actions": [
                    "Зафиксировать цены на пике.",
                    "Искать экспортные контракты.",
                    "Инвестировать в переработку.",
                ],
            },
        }

        advice = advice_map.get(category, {
            "risks": [
                "Изменение рыночной конъюнктуры может повлиять на спрос и издержки.",
                "Возможны изменения условий работы с контрагентами.",
                "Планирование бюджета усложняется из-за неопределённости.",
            ],
            "risk_actions": [
                "Пересмотреть бюджет и чувствительность к ключевым факторам.",
                "Проверить договоры с контрагентами.",
                "Обсудить с менеджером Альфа-Банка меры поддержки.",
            ],
            "opportunities": [
                "Изменения открывают новые ниши и партнёрства.",
                "Можно пересмотреть продуктовую линейку.",
                "Появляется повод пересобрать отношения с клиентами.",
            ],
            "opportunity_actions": [
                "Провести сценарный анализ.",
                "Обсудить с менеджером Альфа-Банка меры поддержки.",
                "Запустить пилот на одном сегменте.",
            ],
        })

        risks = list(advice["risks"])
        risk_actions = list(advice["risk_actions"])
        opportunities = list(advice["opportunities"])
        opportunity_actions = list(advice["opportunity_actions"])

        # Дополняем профилем клиента
        if has_credit:
            risks.insert(0, "Кредитная нагрузка: рост ставок увеличивает стоимость обслуживания долга.")
            risk_actions.insert(0, "Пересчитать график платежей и рассмотреть рефинансирование.")
        if has_leasing:
            risks.append("Лизинговые платежи могут вырасти вслед за стоимостью фондирования.")
            opportunities.append("Лизинг остаётся доступной альтернативой покупке оборудования.")
        if has_fts:
            risks.append("Внешнеэкономические расчёты чувствительны к курсу и логистике.")
            opportunities.append("Экспортные контракты могут стать драйвером выручки.")
        if region:
            opportunities.append(f"Регион присутствия «{region}» можно использовать для локальных партнёрств.")

        # Убираем дубли и ограничиваем длину
        def uniq(items: List[str], limit: int = 3) -> List[str]:
            seen = set()
            result = []
            for item in items:
                key = item.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    result.append(item.strip())
            return result[:limit]

        return {
            "risks": uniq(risks),
            "risk_actions": uniq(risk_actions),
            "opportunities": uniq(opportunities),
            "opportunity_actions": uniq(opportunity_actions),
        }

    def build_analytics_insights(
        self,
        alfa_analytics: List[Dict[str, Any]],
        client_profile: Dict[str, Any],
        limit: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Превращает аналитические сводки Альфа-Банка в такие же карточки
        «риски / возможности», как и новости.
        """
        insights = []
        for item in alfa_analytics[:limit]:
            title = item.get("title", "")
            text = item.get("text") or item.get("content") or item.get("summary") or ""
            category = item.get("category", "macro_outlook")
            analytics_categories = {
                "macro_outlook": "monetary_policy",
                "labor_market": "monetary_policy",
                "bonds": "monetary_policy",
                "consumption": "trade",
                "industry": "commodities",
            }
            advice_category = analytics_categories.get(category, category)
            pseudo_news = {
                "id": item.get("id", title),
                "title": title,
                "content": text,
                "category": advice_category,
                "forced_advice_category": advice_category,
                "source": "Альфа-Банк",
                "url": "",
                "date": item.get("date", ""),
            }
            interpretation = self._generate_local_interpretation(
                pseudo_news,
                client_profile,
                [item],
            )
            insights.append({
                "analytics_id": item.get("id", title),
                "title": title,
                "category": category,
                "date": item.get("date", ""),
                "summary": text[:700],
                "source_file": item.get("source_file", ""),
                "interpretation": interpretation,
                "sources": {
                    "analytics": title,
                    "source_file": item.get("source_file", ""),
                },
            })
        return insights

    def _find_relevant_analytics(
        self,
        news_item: Dict[str, Any],
        alfa_analytics: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Поиск релевантной аналитики Альфа-Банка для новости.
        
        Args:
            news_item: Новость
            alfa_analytics: Все аналитические материалы
            
        Returns:
            Релевантные аналитические материалы
        """
        news_category = news_item.get("classification", {}).get("category", "")
        
        # Простой поиск по категории
        relevant = [
            a for a in alfa_analytics
            if a.get("category") == news_category
        ]
        
        # Если не нашли, берем общие макро-обзоры
        if not relevant:
            relevant = [
                a for a in alfa_analytics
                if a.get("category") in ["macro_outlook", "monetary_policy"]
            ]
        
        return relevant[:2]  # Максимум 2 материала
