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
                "interpretations": [
                    {
                        "news_id": i.get("news_id"),
                        "news_title": i.get("news_title", "")[:80],
                        "relevance_score": i.get("relevance_score", 0),
                        "used_alfa_analytics": i.get("sources", {}).get("alfa_analytics", []),
                        "has_all_sections": all(i.get("interpretation", {}).get(k) for k in ["what_happened", "why_important", "consequences", "actions", "bank_view"]),
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
            "relevance_score": news_item.get("relevance_score", 0),
            "interpretation": interpretation,
            "sources": {
                "news": news_item.get("source", ""),
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
        if category == "monetary_policy":
            why_important += " Изменение ключевой ставки напрямую влияет на стоимость заемного финансирования."
            if "Кредитные продукты" in products:
                why_important += " У вас есть кредитные продукты, поэтому изменение ставки критически важно."
        
        elif category == "inflation":
            why_important += " Инфляция влияет на издержки и ценообразование."
        
        elif category == "currency":
            why_important += " Изменение валютного курса влияет на стоимость импорта и экспорта."
            if has_fts:
                why_important += " У вас есть внешнеэкономическая деятельность, поэтому курс валют особенно важен."
        
        elif category == "agriculture":
            why_important += " Сельскохозяйственные новости влияют на цены на сырье и продукты."
        
        elif category == "technology":
            why_important += " Технологические новости влияют на конкурентоспособность и инновации."
        
        # Последствия
        consequences_parts = []
        
        if risk_factors:
            consequences_parts.append(f"Факторы риска: {', '.join(risk_factors)}.")
        
        if category == "monetary_policy":
            consequences_parts.append("Сохранение высоких ставок может ограничить возможности по рефинансированию кредитов.")
            consequences_parts.append("Рекомендуется рассмотреть досрочное погашение или реструктуризацию кредитов.")
        
        elif category == "inflation":
            consequences_parts.append("Инфляция может привести к росту издержек и снижению маржинальности.")
            consequences_parts.append("Рекомендуется пересмотреть ценообразование и контракты с поставщиками.")
        
        elif category == "currency":
            consequences_parts.append("Изменение курса может повлиять на стоимость импортных товаров и услуг.")
            consequences_parts.append("Рекомендуется рассмотреть хеджирование валютных рисков.")
        
        elif category == "agriculture":
            consequences_parts.append("Изменение цен на сельхозпродукцию может повлиять на издержки.")
            consequences_parts.append("Рекомендуется рассмотреть долгосрочные контракты с поставщиками.")
        
        elif category == "technology":
            consequences_parts.append("Технологические изменения могут создать новые возможности или угрозы.")
            consequences_parts.append("Рекомендуется следить за технологическими трендами и инновациями.")
        
        consequences = " ".join(consequences_parts) if consequences_parts else "Последствия зависят от конкретных условий вашего бизнеса."
        
        # Рекомендации
        actions_parts = []
        
        if category == "monetary_policy":
            actions_parts.append("Пересмотреть кредитный портфель")
            actions_parts.append("Рассмотреть альтернативные источники финансирования")
            actions_parts.append("Обратиться к персональному менеджеру для оптимизации условий")
        
        elif category == "inflation":
            actions_parts.append("Пересмотреть ценообразование")
            actions_parts.append("Оптимизировать издержки")
            actions_parts.append("Рассмотреть долгосрочные контракты с поставщиками")
        
        elif category == "currency":
            actions_parts.append("Рассмотреть хеджирование валютных рисков")
            actions_parts.append("Диверсифицировать поставщиков")
            actions_parts.append("Пересмотреть контракты с иностранными контрагентами")
        
        elif category == "agriculture":
            actions_parts.append("Рассмотреть долгосрочные контракты с поставщиками")
            actions_parts.append("Диверсифицировать каналы сбыта")
            actions_parts.append("Следить за ценами на сырье")
        
        elif category == "technology":
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
        
        return {
            "what_happened": what_happened,
            "why_important": why_important,
            "consequences": consequences,
            "actions": actions,
            "bank_view": bank_view,
            "sources": sources,
        }

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
