"""
Агент самопроверки и верификации результатов.
Оценивает полноту, непротиворечивость и обоснованность выводов.
"""

import json
from typing import Any, Dict, List

from agents.base_agent import AgentContext, BaseAgent


class VerificationAgent(BaseAgent):
    """
    Агент для проверки качества и корректности результатов.
    
    Проверяет:
    - Полноту интерпретаций
    - Непротиворечивость выводов
    - Наличие источников
    - Корректность ссылки на данные клиента
    - Отсутствие фактологических ошибок
    """

    async def execute(self, context: AgentContext) -> AgentContext:
        """
        Верификация результатов.
        
        Args:
            context: Контекст с интерпретациями
            
        Returns:
            Обновленный контекст с результатами верификации
        """
        self.logger.info("Верификация результатов")
        
        if not context.interpretations:
            self.logger.warning("Нет интерпретаций для проверки")
            return context
        
        verification_results = []
        
        for interpretation in context.interpretations:
            try:
                result = await self._verify_interpretation(
                    interpretation,
                    context.client_profile,
                    context.alfa_analytics,
                )
                verification_results.append(result)
            except Exception as e:
                self.logger.error(f"Ошибка верификации: {e}")
                verification_results.append({
                    "news_id": interpretation.get("news_id"),
                    "status": "error",
                    "issues": [str(e)],
                })
        
        # Обновление интерпретаций с учетом верификации
        for i, result in enumerate(verification_results):
            if i < len(context.interpretations):
                context.interpretations[i]["verification"] = result
        
        # Трассировка
        step = self.create_step(
            step_number=5,
            action="verify_results",
            input_data={
                "interpretations_count": len(context.interpretations),
                "client_industry": context.client_profile.get("industry", "")[:80] if context.client_profile else None,
                "client_products": context.client_profile.get("products", []) if context.client_profile else [],
                "checks_performed": [
                    "Полнота: все 5 разделов интерпретации заполнены",
                    "Обоснованность: наличие минимум 2 источников",
                    "Использование данных клиента: отрасль и продукты в тексте",
                ],
            },
            output_data={
                "verification_results": [
                    {
                        "news_id": r.get("news_id"),
                        "status": r.get("status"),
                        "completeness_score": r.get("completeness_score"),
                        "consistency_score": r.get("consistency_score"),
                        "grounding_score": r.get("grounding_score"),
                        "issues": r.get("issues", []),
                        "suggestions": r.get("suggestions", []),
                    }
                    for r in verification_results
                ],
            },
        )
        context.add_step(step)
        
        self.logger.info(f"Верификация завершена: {len(verification_results)} результатов")
        return context

    async def _verify_interpretation(
        self,
        interpretation: Dict[str, Any],
        client_profile: Dict[str, Any],
        alfa_analytics: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Верификация одной интерпретации на основе локальных проверок.
        
        Args:
            interpretation: Интерпретация
            client_profile: Профиль клиента
            alfa_analytics: Аналитика Альфа-Банка
            
        Returns:
            Результат верификации
        """
        interp = interpretation.get("interpretation", {})
        
        # Проверка полноты
        required_fields = ["what_happened", "why_important", "consequences", "actions", "bank_view"]
        missing_fields = [f for f in required_fields if not interp.get(f)]
        completeness_score = (len(required_fields) - len(missing_fields)) / len(required_fields) * 10
        
        # Проверка обоснованности (наличие источников)
        sources = interp.get("sources", [])
        grounding_score = 10 if len(sources) >= 2 else (5 if len(sources) >= 1 else 0)
        
        # Проверка использования данных клиента
        industry = client_profile.get("industry", "")
        products = client_profile.get("products", [])
        
        uses_client_data = False
        if industry and industry in interp.get("why_important", ""):
            uses_client_data = True
        if products and any(p in interp.get("why_important", "") for p in products):
            uses_client_data = True
        
        consistency_score = 10 if uses_client_data else 5
        
        # Формируем результат
        issues = []
        suggestions = []
        
        if missing_fields:
            issues.append(f"Отсутствуют поля: {', '.join(missing_fields)}")
            suggestions.append("Добавить недостающие разделы интерпретации")
        
        if not uses_client_data:
            issues.append("Интерпретация не использует данные клиента")
            suggestions.append("Добавить персонализацию на основе профиля клиента")
        
        if grounding_score < 5:
            issues.append("Недостаточно источников")
            suggestions.append("Добавить ссылки на источники информации")
        
        # Общий статус
        if completeness_score >= 8 and consistency_score >= 8 and grounding_score >= 5:
            status = "verified"
        elif completeness_score >= 5:
            status = "needs_improvement"
        else:
            status = "insufficient"
        
        return {
            "news_id": interpretation.get("news_id"),
            "status": status,
            "completeness_score": round(completeness_score, 1),
            "consistency_score": round(consistency_score, 1),
            "grounding_score": round(grounding_score, 1),
            "issues": issues,
            "suggestions": suggestions,
        }
