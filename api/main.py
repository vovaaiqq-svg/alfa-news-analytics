"""
FastAPI приложение для сервиса новостной аналитики.
"""

import logging
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agents.orchestrator import AgentOrchestrator
from rag.retriever import AlfaAnalyticsRetriever
from services.client_data import count_similar, find_client_row, iter_client_rows
from services.industry import (
    PRODUCT_OPTIONS,
    infer_industry,
    meta_payload,
    revenue_by_key,
)
from services.profile_store import (
    get_custom_profile,
    load_custom_profiles,
    register_account,
    save_custom_profile,
    save_feedback,
    to_public_profile,
    verify_account,
)

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


class RegisterRequest(BaseModel):
    legal_entity: str
    industry: str
    custom_industry: str = ""
    region: str
    scale: str
    city: str = ""
    employees: str = ""
    company_age: str = ""
    growth_stage: str = ""
    products: List[str] = []
    has_fts: bool = False
    fts_country: str = ""
    has_factoring: bool = False
    login: str
    password: str


class LoginRequest(BaseModel):
    login: str
    password: str


class ProfileUpdateRequest(BaseModel):
    legal_entity: Optional[str] = None
    industry: Optional[str] = None
    custom_industry: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    scale: Optional[str] = None
    employees: Optional[str] = None
    company_age: Optional[str] = None
    growth_stage: Optional[str] = None
    products: Optional[List[str]] = None
    has_fts: Optional[bool] = None
    fts_country: Optional[str] = None
    has_factoring: Optional[bool] = None


class ChatRequest(BaseModel):
    agent: str
    client_id: str
    question: str
    history: List[Dict[str, str]] = []


class FeedbackRequest(BaseModel):
    client_id: str = ""
    rating: Optional[int] = None
    category: str = ""
    text: str


# Глобальные переменные
orchestrator: Optional[AgentOrchestrator] = None
retriever: Optional[AlfaAnalyticsRetriever] = None
analysis_cache: Dict[str, Any] = {}


def _slim_news(item: Dict[str, Any]) -> Dict[str, Any]:
    """Компактное представление новости (без полного текста)."""
    return {
        "id": item.get("id"),
        "title": item.get("title", ""),
        "source": item.get("source", ""),
        "category": item.get("category", ""),
        "date": item.get("date", ""),
        "url": item.get("url", ""),
        "excerpt": str(item.get("content", ""))[:500],
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


def _get_raw_profile(client_id: str) -> Optional[Dict[str, Any]]:
    """Кастомный профиль → CSV → None."""
    raw = get_custom_profile(client_id)
    if raw:
        return raw
    try:
        return find_client_row(client_id)
    except Exception:
        return None


def _registration_raw(
    request: RegisterRequest,
    client_id: str,
) -> tuple[Dict[str, Any], Dict[str, str], Dict[str, Any]]:
    industry = infer_industry(request.industry, request.custom_industry)
    scale = revenue_by_key(request.scale)

    raw: Dict[str, Any] = {
        "SYNTHETIC_U": client_id,
        "ORG_TYPE": "ООО",
        "MAINOKVED_NAME": industry["okved"],
        "MAINOKVED_CODE": industry["code"],
        "REGION": request.region,
        "CITY": request.city or "",
        "REVENUE_COMPANY": str(scale["amount"]),
        "AMOUNT_WORKERS_FNS_GRADATION": request.employees or "16-100",
        "COMPANY_AGE_YEARS_GRADATION": request.company_age or "5-10",
        "ECO_MARK_LABEL": request.growth_stage or "Растущий бизнес",
        "CL_TYPE": "Новый клиент",
        "FTS_FLAG": "1" if request.has_fts else "0",
        "FTS_COUNTRY_NAME": request.fts_country if request.has_fts else "",
        "FACTORING_MARK": "1" if request.has_factoring else "0",
        "_LEGAL_ENTITY": request.legal_entity.strip(),
        "_INDUSTRY_KEY": industry["key"],
        "_INDUSTRY_LABEL": industry["label"],
        "_CUSTOM_INDUSTRY": request.custom_industry.strip(),
        "_SCALE_LABEL": scale["scale"],
        "_SOURCE": "профиль пользователя (регистрация)",
        "_CREATED_AT": datetime.now().isoformat(timespec="seconds"),
    }

    selected_products = set(request.products)
    for option in PRODUCT_OPTIONS:
        raw[option["field"]] = "1" if option["key"] in selected_products else "0"

    return raw, industry, scale


def _apply_profile_updates(
    raw: Dict[str, Any],
    request: ProfileUpdateRequest,
) -> Dict[str, Any]:
    updated = dict(raw)

    if request.legal_entity is not None:
        updated["_LEGAL_ENTITY"] = request.legal_entity.strip()

    if request.region is not None:
        updated["REGION"] = request.region
    if request.city is not None:
        updated["CITY"] = request.city

    if request.industry is not None or request.custom_industry is not None:
        industry_key = request.industry or updated.get("_INDUSTRY_KEY", "other")
        custom_text = (
            request.custom_industry
            if request.custom_industry is not None
            else updated.get("_CUSTOM_INDUSTRY", "")
        )
        industry = infer_industry(industry_key, custom_text or "")
        updated["MAINOKVED_NAME"] = industry["okved"]
        updated["MAINOKVED_CODE"] = industry["code"]
        updated["_INDUSTRY_KEY"] = industry["key"]
        updated["_INDUSTRY_LABEL"] = industry["label"]
        updated["_CUSTOM_INDUSTRY"] = custom_text or ""

    if request.scale:
        scale = revenue_by_key(request.scale)
        updated["REVENUE_COMPANY"] = str(scale["amount"])
        updated["_SCALE_LABEL"] = scale["scale"]

    if request.employees is not None:
        updated["AMOUNT_WORKERS_FNS_GRADATION"] = request.employees
    if request.company_age is not None:
        updated["COMPANY_AGE_YEARS_GRADATION"] = request.company_age
    if request.growth_stage is not None:
        updated["ECO_MARK_LABEL"] = request.growth_stage

    if request.products is not None:
        selected_products = set(request.products)
        for option in PRODUCT_OPTIONS:
            updated[option["field"]] = "1" if option["key"] in selected_products else "0"

    if request.has_fts is not None:
        updated["FTS_FLAG"] = "1" if request.has_fts else "0"
        if not request.has_fts:
            updated["FTS_COUNTRY_NAME"] = ""
    if request.fts_country is not None:
        updated["FTS_COUNTRY_NAME"] = request.fts_country
    if request.has_factoring is not None:
        updated["FACTORING_MARK"] = "1" if request.has_factoring else "0"

    updated["_SOURCE"] = "профиль пользователя (изменён)"
    updated["_UPDATED_AT"] = datetime.now().isoformat(timespec="seconds")
    return updated


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]{4,}", (text or "").lower())


# Служебные слова в вопросах: без них общий вопрос («что нового?») не должен
# считаться нерелевантным и уходить в пустой ответ.
_GENERIC_QUERY_TOKENS = {
    "этот", "этого", "этому", "этим", "этом",
    "меня", "наше", "нашего", "ваше", "вашего", "моего",
    "моей", "моем", "моих", "мое",
    "есть", "сейчас", "можно", "надо", "нужно", "дела", "деле",
    "мира", "мире", "миру",
}
_GENERIC_QUERY_PREFIXES = (
    "новост", "новог", "новое", "новы", "важн", "каки", "како",
    "проис", "скажи", "расск", "подск", "подро", "кратк", "свеж",
    "бизнес", "отрасл", "сфер", "компан", "регион", "област", "рынк",
    "интерес", "риск", "возможност", "аналитик",
)


def _query_stems(question: str) -> List[str]:
    """Основы значимых слов вопроса — для поиска по новостям.

    Отбрасывает служебные слова, чтобы «что нового?» оставался общим
    запросом, а «что нового по ставке?» искал именно ставку.
    """
    stems: List[str] = []
    for token in set(_tokens(question)):
        if token in _GENERIC_QUERY_TOKENS:
            continue
        if any(token.startswith(prefix) for prefix in _GENERIC_QUERY_PREFIXES):
            continue
        stems.append(token[:5])
    return stems


def _text_score(question: str, text: str) -> int:
    haystack = (text or "").lower()
    return sum(len(stem) for stem in _query_stems(question) if stem in haystack)


# Явно посторонние запросы: код, стихи, погода и т.п.
# Агенты отвечают только по своим источникам, а не как универсальный чат.
_OFF_TOPIC_STRONG = (
    "алгоритм", "сортировк", "напиши код", "написать код", "код на",
    "python", "javascript", "typescript", "стих", "анекдот", "шутк",
    "рецепт", "погод", "переведи", "сочинение", "эссе",
)
_OFF_TOPIC_SOFT = ("напиши", "написать", "реализуй", "функцию", "домашн", "контрольн")
_SCOPE_MARKERS = (
    "новост", "бизнес", "компани", "ставк", "инфляц", "рынок", "риск",
    "возможност", "аналитик", "отрасл", "регион", "банк", "кредит",
    "лизинг", "спрос", "поставк", "логист", "экспорт", "импорт",
    "налог", "бюджет", "валют", "курс", "сотрудник", "персонал",
)


def _is_off_topic(question: str) -> bool:
    """Посторонний запрос (код, стихи, погода), а не бизнес/новости."""
    text = (question or "").lower()
    if any(marker in text for marker in _OFF_TOPIC_STRONG):
        return True
    if any(marker in text for marker in _SCOPE_MARKERS):
        return False
    return any(marker in text for marker in _OFF_TOPIC_SOFT)


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


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
        analysis_cache[request.client_id] = context
        
        # Отладка
        logger.info(f"Результат: новостей={len(context.news_items)}, аналитики={len(context.alfa_analytics)}, интерпретаций={len(context.interpretations)}")

        raw_profile = (context.client_profile or {}).get("raw_data", {})
        profile_display = to_public_profile(raw_profile)
        
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
            "profile_display": profile_display,
            "news_items": news_items,
            "ranked_news": ranked_news,
            "interpretations": context.interpretations,
            "analytics_insights": context.metadata.get("analytics_insights", []),
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
    Список клиентов: сначала профили, созданные пользователями, затем CSV кейса.
    """
    clients: List[Dict[str, Any]] = []
    seen_ids = set()

    try:
        for client_id, row in load_custom_profiles().items():
            if client_id in seen_ids:
                continue
            seen_ids.add(client_id)
            profile = to_public_profile(row)
            clients.append({
                "id": client_id,
                "legal_entity": profile.get("legal_entity", ""),
                "industry": profile.get("industry", "")[:50],
                "region": profile.get("region", ""),
                "city": profile.get("city", ""),
                "revenue": profile.get("revenue", ""),
                "revenue_label": profile.get("revenue_label", ""),
                "scale": profile.get("scale", ""),
                "products": profile.get("products", []),
                "is_custom": True,
            })

        for row in iter_client_rows(limit=200):
            client_id = row.get("SYNTHETIC_U", "")
            if not client_id or client_id in seen_ids:
                continue
            seen_ids.add(client_id)
            clients.append({
                "id": client_id,
                "legal_entity": f"Компания {client_id}",
                "industry": row.get("MAINOKVED_NAME", "")[:50],
                "region": row.get("REGION", ""),
                "city": row.get("CITY", ""),
                "revenue": row.get("REVENUE_COMPANY", ""),
                "revenue_label": to_public_profile(row).get("revenue_label", ""),
                "scale": to_public_profile(row).get("scale", ""),
                "products": to_public_profile(row).get("products", []),
                "is_custom": False,
            })
            if len(clients) >= 50:
                break
    except Exception as e:
        logger.error(f"Ошибка загрузки клиентов: {e}")

    return clients


@app.get("/api/meta")
async def get_meta():
    """Справочники для формы регистрации и редактирования профиля."""
    return meta_payload()


@app.post("/api/register")
async def register_user(request: RegisterRequest):
    """Создание профиля компании и демо-аккаунта."""
    legal_entity = (request.legal_entity or "").strip()
    login = (request.login or "").strip()
    if len(legal_entity) < 2:
        raise HTTPException(status_code=422, detail="Укажите название юридического лица")
    if len(login) < 3:
        raise HTTPException(status_code=422, detail="Логин должен быть не короче 3 символов")
    if len(request.password or "") < 4:
        raise HTTPException(status_code=422, detail="Пароль должен быть не короче 4 символов")
    if not request.industry:
        raise HTTPException(status_code=422, detail="Выберите сферу деятельности")
    if not request.region:
        raise HTTPException(status_code=422, detail="Выберите регион")

    client_id = f"U_{uuid.uuid4().hex[:8].upper()}"
    raw, industry, scale = _registration_raw(request, client_id)

    try:
        save_custom_profile(client_id, raw)
        register_account(login, request.password, client_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.error(f"Ошибка регистрации: {exc}")
        raise HTTPException(status_code=500, detail="Не удалось создать профиль")

    try:
        similar = count_similar(industry["okved"], request.region)
    except Exception:
        similar = 0

    logger.info(f"Зарегистрирован клиент {client_id} ({legal_entity})")
    return {
        "client_id": client_id,
        "profile": to_public_profile(raw),
        "industry": industry,
        "scale": scale,
        "similar_clients": similar,
        "note": (
            f"Найдено {similar} похожих компаний в базе. "
            "Отрасль определена по ключевым словам, профиль дополнен."
            if similar
            else "Профиль создан. Отрасль определена по ключевым словам, характеристики дополнены."
        ),
    }


@app.post("/api/login")
async def login_user(request: LoginRequest):
    """Демо-вход. Логин demo / пароль demo открывает профиль U_84."""
    login = (request.login or "").strip().lower()
    password = request.password or ""

    if login == "demo" and password == "demo":
        raw = _get_raw_profile("U_84")
        if raw is None:
            raw = next(iter_client_rows(limit=1), None)
        if raw is None:
            raise HTTPException(status_code=404, detail="Демо-профиль не найден")
        return {
            "client_id": raw.get("SYNTHETIC_U", "U_84"),
            "profile": to_public_profile(raw),
            "demo": True,
        }

    client_id = verify_account(login, password)
    if not client_id:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    raw = _get_raw_profile(client_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    return {
        "client_id": client_id,
        "profile": to_public_profile(raw),
        "demo": False,
    }


@app.get("/api/profile/{client_id}")
async def get_profile(client_id: str):
    """Профиль компании для страницы «Профиль»."""
    raw = _get_raw_profile(client_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    return {
        "client_id": client_id,
        "profile": to_public_profile(raw),
    }


@app.patch("/api/profile/{client_id}")
async def update_profile(client_id: str, request: ProfileUpdateRequest):
    """Редактирование профиля. Изменения сразу учитываются агентами."""
    raw = _get_raw_profile(client_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    updated = _apply_profile_updates(raw, request)
    save_custom_profile(client_id, updated)
    analysis_cache.pop(client_id, None)

    return {
        "client_id": client_id,
        "profile": to_public_profile(updated),
    }


@app.post("/api/chat")
async def chat_with_agent(request: ChatRequest):
    """
    Диалог с одним из двух агентов:
    - alfa — только аналитика Альфа-Банка;
    - news — только внешние новости.
    """
    question = (request.question or "").strip()
    if len(question) < 2:
        raise HTTPException(
            status_code=422,
            detail="Введите вопрос подробнее — хотя бы пару слов.",
        )
    if request.agent not in {"alfa", "news"}:
        raise HTTPException(status_code=422, detail="Неизвестный агент")

    # Агенты работают только по своим источникам. Посторонние задачи
    # (код, стихи, погода) не должны превращаться в случайную новостную выдачу.
    if _is_off_topic(question):
        if request.agent == "news":
            answer = (
                "Я отвечаю только по внешним новостям и их влиянию на ваш бизнес — "
                "код, стихи и другие посторонние задачи вне моей темы.\n\n"
                "Спросите, например: «Что нового по ключевой ставке?», "
                "«Какие риски в логистике?» или «Что нового в моей отрасли?»."
            )
        else:
            answer = (
                "Я — Альфа-агент: отвечаю только по аналитике и продуктам Альфа-Банка. "
                "Код и другие посторонние задачи вне моей темы.\n\n"
                "Спросите про кредитные продукты, лизинг, РКО или риски для вашей отрасли."
            )
        return {
            "agent": request.agent,
            "answer": answer,
            "sources": [],
            "mode": "demo",
        }

    context = analysis_cache.get(request.client_id)
    if context is None:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Сервис не инициализирован")
        context = await orchestrator.run(request.client_id)
        analysis_cache[request.client_id] = context

    raw = _get_raw_profile(request.client_id) or {}
    profile = to_public_profile(raw)
    industry = profile.get("industry", "")
    sources: List[Dict[str, Any]] = []

    if request.agent == "alfa":
        if not retriever:
            raise HTTPException(status_code=503, detail="База аналитики не инициализирована")
        results = await retriever.search(
            f"{question} {industry}".strip(),
            top_k=3,
        )
        if not results:
            results = context.alfa_analytics[:3]

        blocks = []
        for item in results[:3]:
            title = item.get("title", "Аналитическая сводка")
            text = (
                item.get("text")
                or item.get("content")
                or item.get("summary")
                or ""
            )
            blocks.append(f"• «{title}» — {_truncate(text, 320)}")
            sources.append({
                "type": "Альфа-Банк",
                "title": title,
                "url": "",
                "date": item.get("date", ""),
            })

        answer = "По аналитике Альфа-Банка:\n\n" + "\n\n".join(blocks)
        if industry:
            answer += f"\n\nДля вашей отрасли «{industry}» это значит: проверьте влияние на маржу, ликвидность и условия по банковским продуктам."
        answer += "\n\nДемо-режим: ответ собран локально по материалам Альфа-Банка, без внешней LLM."
    else:
        interpretations = {
            item.get("news_id"): item for item in context.interpretations
        }
        query_stems = _query_stems(question)
        scored = []
        if query_stems:
            for item in context.news_items:
                title = item.get("title", "")
                # Тема должна быть в заголовке: совпадение по случайному слову
                # глубоко в тексте даёт нерелевантные «ставки» и «ключевые».
                title_score = _text_score(question, title)
                if not title_score:
                    continue
                full_score = _text_score(question, f"{title} {item.get('content', '')}")
                scored.append((title_score, full_score, item))
            scored.sort(key=lambda pair: (pair[0], pair[1]), reverse=True)

            # Ни одного содержательного совпадения — честно говорим об этом
            # и не подставляем случайные новости «для вида».
            if not scored:
                return {
                    "agent": request.agent,
                    "answer": (
                        f"По запросу «{_truncate(question, 120)}» в свежих внешних "
                        "новостях ничего значимого не нашёл. Я не подставляю случайные "
                        "материалы: попробуйте спросить про ключевую ставку, инфляцию, "
                        "отрасль, регион или логистику."
                    ),
                    "sources": [],
                    "mode": "demo",
                }

        # Общий вопрос («что нового?») — дайджест по профилю клиента.
        if not query_stems:
            ranked_ids = [item.get("id") for item in context.ranked_news]
            by_id = {item.get("id"): item for item in context.news_items}
            scored = [(1, 1, by_id[news_id]) for news_id in ranked_ids if news_id in by_id]

        blocks = []
        for _, _, item in scored[:3]:
            item_id = item.get("id")
            interp = interpretations.get(item_id, {})
            interpretation = interp.get("interpretation", {})
            meaning = interpretation.get("why_important") or interp.get("relevance_reasoning") or ""
            blocks.append(
                "• «{title}» — {source}, {date}.\n  {summary}\n  Что это значит для вас: {meaning}".format(
                    title=item.get("title", ""),
                    source=item.get("source", ""),
                    date=item.get("date", ""),
                    summary=_truncate(item.get("content", ""), 260),
                    meaning=_truncate(meaning, 300) or "событие связано с вашей отраслью и регионом.",
                )
            )
            sources.append({
                "type": "Новость",
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "date": item.get("date", ""),
            })

        if blocks:
            answer = "По внешним новостям:\n\n" + "\n\n".join(blocks)
            answer += "\n\nДемо-режим: ответ собран локально по свежим RSS-новостям, без внешней LLM."
        else:
            answer = (
                "Пока не удалось собрать новости по этому запросу. "
                "Попробуйте переформулировать вопрос или обновить анализ на странице профиля."
            )

    return {
        "agent": request.agent,
        "answer": answer,
        "sources": sources,
        "mode": "demo",
    }


@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Обратная связь по качеству ответов."""
    text = (request.text or "").strip()
    if len(text) < 2:
        raise HTTPException(status_code=422, detail="Напишите отзыв")
    try:
        save_feedback({
            "client_id": request.client_id,
            "rating": request.rating,
            "category": request.category,
            "text": text,
        })
    except Exception as exc:
        logger.error(f"Ошибка сохранения отзыва: {exc}")
        raise HTTPException(status_code=500, detail="Не удалось сохранить отзыв")
    return {"status": "ok"}


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
