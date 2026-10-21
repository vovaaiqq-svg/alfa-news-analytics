"""
Агент ранжирования и отбора значимых новостей.
Сопоставляет новости с бизнес-контекстом клиента и определяет их значимость.
"""

import json
from typing import Any, Dict, List

from agents.base_agent import AgentContext, BaseAgent


class RankingAgent(BaseAgent):
    """
    Агент для ранжирования новостей по значимости для конкретного клиента.
    
    Учитывает:
    - Отрасль клиента
    - Банковские продукты
    - Регионы присутствия
    - Внешнеэкономическую деятельность
    - Макроэкономические факторы
    """

    async def execute(self, context: AgentContext) -> AgentContext:
        """
        Ранжирование новостей по значимости для клиента.
        
        Args:
            context: Контекст с профилем клиента и новостями
            
        Returns:
            Обновленный контекст с ранжированными новостями
        """
        self.logger.info("Ранжирование новостей по значимости")
        
        if not context.client_profile or not context.news_items:
            self.logger.warning("Недостаточно данных для ранжирования")
            return context
        
        # Оценка релевантности каждой новости
        ranked_news = await self._rank_news(
            context.news_items,
            context.client_profile,
        )
        
        # Фильтрация топ-N самых значимых
        top_news = ranked_news[:10]
        
        context.ranked_news = top_news
        
        # Трассировка
        step = self.create_step(
            step_number=3,
            action="rank_news",
            input_data={
                "total_news": len(context.news_items),
                "client_industry": context.client_profile.get("industry", "")[:80],
                "client_products": context.client_profile.get("products", []),
                "client_region": context.client_profile.get("region", ""),
                "client_has_fts": context.client_profile.get("has_fts", False),
                "relevance_criteria": context.client_profile.get("relevance_criteria", []),
            },
            output_data={
                "ranked_count": len(ranked_news),
                "top_news": [
                    {
                        "id": n["id"],
                        "title": n.get("title", "")[:80],
                        "relevance_score": n.get("relevance_score", 0),
                        "reasoning": n.get("relevance_reasoning", ""),
                    }
                    for n in top_news[:5]
                ],
            },
        )
        context.add_step(step)
        
        self.logger.info(f"Отобрано {len(top_news)} значимых новостей")
        return context

    async def _rank_news(
        self,
        news_items: List[Dict[str, Any]],
        client_profile: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Оценка релевантности новостей для клиента на основе локальных эвристик.
        
        Args:
            news_items: Список новостей
            client_profile: Профиль клиента
            
        Returns:
            Новости с оценками релевантности, отсортированные по убыванию
        """
        # Получаем критерии релевантности из профиля клиента
        relevance_criteria = client_profile.get("relevance_criteria", []) or client_profile.get("analysis", {}).get("relevance_criteria", [])
        industry = client_profile.get("industry", "") or client_profile.get("raw_data", {}).get("MAINOKVED_NAME", "")
        products = client_profile.get("products", [])
        region = client_profile.get("region", "") or client_profile.get("raw_data", {}).get("REGION", "")
        has_fts = client_profile.get("has_fts", False)
        
        ranked_items = []
        
        for news_item in news_items:
            score = 0.0
            reasoning_parts = []
            
            # Оценка по категории новости
            category = news_item.get("category", "")
            classification = news_item.get("classification", {})
            news_category = classification.get("category", category)
            
            # Проверяем соответствие критериям релевантности
            for criterion in relevance_criteria:
                criterion_lower = criterion.lower()
                
                # Проверяем категорию новости
                if news_category and news_category.lower() in criterion_lower:
                    score += 2.0
                    reasoning_parts.append(f"Категория '{news_category}' соответствует критерию '{criterion}'")
                
                # Проверяем содержание новости
                content = news_item.get("content", "").lower()
                title = news_item.get("title", "").lower()
                
                if criterion_lower in content or criterion_lower in title:
                    score += 1.5
                    reasoning_parts.append(f"Содержание соответствует критерию '{criterion}'")
            
            # Оценка по отрасли
            if industry:
                industry_lower = industry.lower()
                content = news_item.get("content", "").lower()
                title = news_item.get("title", "").lower()
                
                # Проверяем ключевые слова отрасли
                if "компьютер" in industry_lower or "программ" in industry_lower or "it" in industry_lower:
                    if any(word in content or word in title for word in ["it", "технолог", "программ", "компьютер", "цифров"]):
                        score += 2.0
                        reasoning_parts.append("Новость относится к IT-отрасли")
                
                elif "торгов" in industry_lower:
                    if any(word in content or word in title for word in ["торгов", "розниц", "опт", "магазин"]):
                        score += 2.0
                        reasoning_parts.append("Новость относится к торговой отрасли")
                
                elif "производ" in industry_lower or "обработк" in industry_lower:
                    if any(word in content or word in title for word in ["производ", "завод", "фабрик", "промышленн"]):
                        score += 2.0
                        reasoning_parts.append("Новость относится к производству")
                
                elif "строитель" in industry_lower:
                    if any(word in content or word in title for word in ["строитель", "недвижим", "жиль"]):
                        score += 2.0
                        reasoning_parts.append("Новость относится к строительству")
                
                elif "транспорт" in industry_lower or "перевозк" in industry_lower:
                    if any(word in content or word in title for word in ["транспорт", "перевозк", "логистик"]):
                        score += 2.0
                        reasoning_parts.append("Новость относится к транспорту")
                
                elif "сельск" in industry_lower or "растениевод" in industry_lower:
                    if any(word in content or word in title for word in ["сельск", "зерн", "урожай", "агр"]):
                        score += 2.0
                        reasoning_parts.append("Новость относится к сельскому хозяйству")
            
            # Оценка по банковским продуктам
            if products:
                content = news_item.get("content", "").lower()
                title = news_item.get("title", "").lower()
                
                if "Кредитные продукты" in products:
                    if any(word in content or word in title for word in ["кредит", "ставк", "заём", "ипотек"]):
                        score += 2.5
                        reasoning_parts.append("Новость влияет на кредитные продукты")
                
                if "Депозитные продукты" in products:
                    if any(word in content or word in title for word in ["депозит", "вклад", "сбережен"]):
                        score += 2.0
                        reasoning_parts.append("Новость влияет на депозитные продукты")
                
                if "Банковские гарантии" in products:
                    if any(word in content or word in title for word in ["гарант", "тендер", "закупк"]):
                        score += 2.0
                        reasoning_parts.append("Новость влияет на банковские гарантии")
                
                if "Лизинговые продукты" in products:
                    if any(word in content or word in title for word in ["лизинг", "аренд"]):
                        score += 2.0
                        reasoning_parts.append("Новость влияет на лизинговые продукты")
            
            # Оценка по ВЭД
            if has_fts:
                content = news_item.get("content", "").lower()
                title = news_item.get("title", "").lower()
                
                if any(word in content or word in title for word in ["экспорт", "импорт", "валют", "санкц", "международ"]):
                    score += 2.0
                    reasoning_parts.append("Новость относится к внешнеэкономической деятельности")
            
            # Оценка по макроэкономике (всегда актуально)
            content = news_item.get("content", "").lower()
            title = news_item.get("title", "").lower()
            
            if any(word in content or word in title for word in ["цб", "ключевая ставк", "инфляц", "ввп", "макроэконом"]):
                score += 1.5
                reasoning_parts.append("Новость относится к макроэкономике")
            
            # Нормализация оценки (максимум 10)
            score = min(score, 10.0)
            
            # Если нет совпадений, ставим минимальную оценку
            if score == 0:
                score = 1.0
                reasoning_parts.append("Нет прямых совпадений с критериями клиента")
            
            ranked_items.append({
                **news_item,
                "relevance_score": round(score, 1),
                "relevance_reasoning": "; ".join(reasoning_parts) if reasoning_parts else "Общая новость",
            })
        
        # Сортировка по убыванию значимости
        ranked_items.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return ranked_items
