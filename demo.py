"""
Демонстрация работы агентной системы без запуска сервера.
"""

import asyncio
import json
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from agents.orchestrator import AgentOrchestrator


async def main():
    """
    Запуск демонстрации агентной системы.
    """
    print("=" * 60)
    print("Альфа Хак - Новостная аналитика для крупного бизнеса")
    print("=" * 60)
    print()
    
    # Инициализация оркестратора
    orchestrator = AgentOrchestrator()
    
    # Демо-клиент из синтетической базы; в локальном кейсе может быть U_84.
    client_id = "U_84"
    print(f"Запуск анализа для клиента: {client_id}")
    print("-" * 60)
    
    try:
        context = await orchestrator.run(client_id)
        
        # Вывод результатов
        print()
        print("=" * 60)
        print("РЕЗУЛЬТАТЫ АНАЛИЗА")
        print("=" * 60)
        
        # Профиль клиента
        print()
        print("1. ПРОФИЛЬ КЛИЕНТА")
        print("-" * 40)
        if context.client_profile:
            print(f"Отрасль: {context.client_profile.get('industry', 'N/A')}")
            print(f"Продукты: {', '.join(context.client_profile.get('products', []))}")
            print(f"Регион: {context.client_profile.get('region', 'N/A')}")
        
        # Собранные новости
        print()
        print("2. СОБРАННЫЕ НОВОСТИ")
        print("-" * 40)
        print(f"Всего собрано новостей: {len(context.news_items)}")
        print(f"Аналитических материалов: {len(context.alfa_analytics)}")
        
        # Ранжированные новости
        print()
        print("3. ТОП-5 ЗНАЧИМЫХ НОВОСТЕЙ")
        print("-" * 40)
        for i, news in enumerate(context.ranked_news[:5], 1):
            print(f"{i}. {news.get('title', 'N/A')}")
            print(f"   Релевантность: {news.get('relevance_score', 0):.1f}/10")
        
        # Интерпретации
        print()
        print("4. ПЕРСОНАЛИЗИРОВАННЫЕ ИНТЕРПРЕТАЦИИ")
        print("-" * 40)
        for i, interp in enumerate(context.interpretations[:3], 1):
            print(f"{i}. {interp.get('news_title', 'N/A')}")
            print(f"   Релевантность: {interp.get('relevance_score', 0):.1f}/10")
            
            interpretation = interp.get('interpretation', {})
            if interpretation:
                print(f"   Что произошло: {interpretation.get('what_happened', 'N/A')[:100]}...")
        
        # Трассировка
        print()
        print("5. ТРАССИРОВКА РАБОТЫ АГЕНТОВ")
        print("-" * 40)
        for step in context.trace:
            status = "✓" if step.success else "✗"
            print(f"Шаг {step.step_number}: {step.action} {status}")
        
        print()
        print("=" * 60)
        print("Анализ завершен успешно!")
        print("=" * 60)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
