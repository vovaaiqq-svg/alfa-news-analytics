"""
FastAPI приложение для сервиса новостной аналитики.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agents.orchestrator import AgentOrchestrator
from rag.retriever import AlfaAnalyticsRetriever

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Модели запросов/ответов
class ClientRequest(BaseModel):
    client_id: str
    # full=true — вернуть полные тексты новостей и OCR-аналитики (большой ответ)
    full: bool = False


class NewsItem(BaseModel):
    id: str
    title: str
    content: str
    source: str
    date: str
    category: str


class InterpretationResponse(BaseModel):
    news_id: str
    news_title: str
    relevance_score: float
    interpretation: Dict[str, Any]
    sources: Dict[str, Any]


class AnalyticsResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]


# Глобальные переменные
orchestrator: Optional[AgentOrchestrator] = None
retriever: Optional[AlfaAnalyticsRetriever] = None


def _slim_news(item: Dict[str, Any]) -> Dict[str, Any]:
    """Компактное представление новости (без полного текста)."""
    return {
        "id": item.get("id"),
        "title": item.get("title", ""),
        "source": item.get("source", ""),
        "category": item.get("category", ""),
        "date": item.get("date", ""),
        "url": item.get("url", ""),
        "is_real": item.get("is_real", False),
    }


def _slim_ranked(item: Dict[str, Any]) -> Dict[str, Any]:
    """Компактное представление ранжированной новости."""
    return {
        "id": item.get("id"),
        "title": item.get("title", ""),
        "source": item.get("source", ""),
        "category": item.get("category", ""),
        "relevance_score": item.get("relevance_score", 0),
        "relevance_reasoning": item.get("relevance_reasoning", ""),
    }


def _slim_analytics(item: Dict[str, Any]) -> Dict[str, Any]:
    """Компактное представление аналитики: метаданные + начало текста."""
    text = item.get("text") or item.get("content") or ""
    return {
        "id": item.get("id"),
        "title": item.get("title", ""),
        "category": item.get("category", ""),
        "date": item.get("date", ""),
        "source_file": item.get("source_file", ""),
        "summary": text[:400],
    }


def _summarize(data: Any, max_chars: int = 2000) -> Any:
    """
    Сжатие данных трассировки для читаемости.
    Длинные списки и строки обрезаются, структура сохраняется.
    """
    if data is None:
        return None
    if isinstance(data, dict):
        return {k: _summarize(v, max_chars // 2) for k, v in data.items()}
    if isinstance(data, list):
        if len(data) > 8:
            shown = [_summarize(x, max_chars // 8) for x in data[:8]]
            shown.append(f"... ещё {len(data) - 8} элементов")
            return shown
        return [_summarize(x, max_chars // 8) for x in data]
    if isinstance(data, str):
        if len(data) > max_chars:
            return data[:max_chars] + f"... (обрезано, всего {len(data)} символов)"
        return data
    return data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Инициализация при запуске.
    """
    global orchestrator, retriever
    
    logger.info("Инициализация сервиса...")
    
    # Инициализация оркестратора
    orchestrator = AgentOrchestrator(model_name="opencode/glm-5.3-flash-free")
    
    # Инициализация ретривера
    retriever = AlfaAnalyticsRetriever()
    await retriever.initialize()
    
    logger.info("Сервис готов к работе")
    yield
    
    # Очистка при завершении
    logger.info("Остановка сервиса...")


app = FastAPI(
    title="Альфа Хак - Новостная аналитика",
    description="Сервис персонализированной новостной аналитики для крупного бизнеса",
    version="1.0.0",
    lifespan=lifespan,
)

# Сжатие ответов (важно для публикации через туннель)
app.add_middleware(GZipMiddleware, minimum_size=1024)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Обработка ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return {"error": str(exc), "status": "error"}


@app.get("/")
async def root():
    """
    Корневой эндпоинт.
    """
    return {
        "service": "Альфа Хак - Новостная аналитика",
        "version": "1.0.0",
        "status": "running",
    }


@app.post("/api/analyze", response_model=Dict[str, Any])
async def analyze_client(request: ClientRequest):
    """
    Запуск полного анализа для клиента.
    
    Args:
        request: Запрос с client_id
        
    Returns:
        Результаты анализа с интерпретациями
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Сервис не инициализирован")
    
    try:
        logger.info(f"Запуск анализа для клиента: {request.client_id}")
        
        # Запуск оркестратора
        context = await orchestrator.run(request.client_id)
        
        # Отладка
        logger.info(f"Результат: новостей={len(context.news_items)}, аналитики={len(context.alfa_analytics)}, интерпретаций={len(context.interpretations)}")
        
        # Формирование ответа
        if request.full:
            news_items = context.news_items
            ranked_news = context.ranked_news
            alfa_analytics = context.alfa_analytics
        else:
            news_items = [_slim_news(n) for n in context.news_items]
            ranked_news = [_slim_ranked(n) for n in context.ranked_news]
            alfa_analytics = [_slim_analytics(a) for a in context.alfa_analytics]

        response = {
            "client_id": context.client_id,
            "client_profile": context.client_profile,
            "news_items": news_items,
            "ranked_news": ranked_news,
            "interpretations": context.interpretations,
            "alfa_analytics": alfa_analytics,
            "trace": [
                {
                    "step_number": step.step_number,
                    "action": step.action,
                    "success": step.success,
                    "error_message": step.error_message,
                    "timestamp": step.timestamp.isoformat(),
                    "input_data": _summarize(step.input_data, max_chars=2000),
                    "output_data": _summarize(step.output_data, max_chars=3000),
                }
                for step in context.trace
            ],
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Ошибка анализа: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/clients", response_model=List[Dict[str, Any]])
async def get_clients():
    """
    Получение списка доступных клиентов из реальных данных.
    """
    import csv
    import os
    from pathlib import Path
    
    clients = []
    seen_ids = set()
    
    # Путь к реальным данным: env-переменная → файл кейса → синтетика
    env_path = os.getenv("CLIENT_DATA_CSV")
    if env_path and Path(env_path).exists():
        data_path = Path(env_path)
    else:
        data_path = Path(__file__).resolve().parent.parent.parent / "пример" / "extracted" / "df_Uid_data_hack.csv"
    
    # Fallback на синтетические данные
    if not data_path.exists():
        data_path = Path(__file__).resolve().parent / "data" / "client_profiles" / "clients.csv"
    
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            first_line = f.readline()
            delimiter = ";" if first_line.count(";") >= first_line.count(",") else ","
            f.seek(0)
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                client_id = row.get("SYNTHETIC_U", "")
                if client_id and client_id not in seen_ids:
                    seen_ids.add(client_id)
                    clients.append({
                        "id": client_id,
                        "industry": row.get("MAINOKVED_NAME", "")[:50],
                        "region": row.get("REGION", ""),
                        "city": row.get("CITY", ""),
                        "revenue": row.get("REVENUE_COMPANY", ""),
                        "products": [
                            p for p, v in [
                                ("RKO", row.get("CL_PRODUCT_RKO_MARK")),
                                ("Кредиты", row.get("CL_PRODUCT_LOA_MARK")),
                                ("Депозиты", row.get("CL_PRODUCT_DEP_MARK")),
                                ("Гарантии", row.get("CL_PRODUCT_GAR_MARK")),
                            ] if v and v != "0.0" and v != "0"
                        ],
                    })
                    if len(clients) >= 50:  # Ограничение для списка
                        break
    except Exception as e:
        logger.error(f"Ошибка загрузки клиентов: {e}")
    
    return clients


@app.get("/api/analytics/search", response_model=AnalyticsResponse)
async def search_analytics(
    query: str = Query(..., description="Поисковый запрос"),
    top_k: int = Query(3, description="Количество результатов"),
    category: Optional[str] = Query(None, description="Фильтр по категории"),
):
    """
    Поиск по аналитическим материалам Альфа-Банка.
    """
    if not retriever:
        raise HTTPException(status_code=503, detail="Ретривер не инициализирован")
    
    try:
        results = await retriever.search(query, top_k=top_k, category=category)
        return AnalyticsResponse(query=query, results=results)
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """
    Проверка состояния сервиса.
    """
    return {
        "status": "healthy",
        "orchestrator_ready": orchestrator is not None,
        "retriever_ready": retriever is not None,
    }


# Статические файлы (фронтенд)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/app")
async def get_app():
    """
    Получение главной страницы приложения.
    """
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
