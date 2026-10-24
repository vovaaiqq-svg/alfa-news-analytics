"""
RAG система для работы с аналитическими материалами Альфа-Банка.
Обеспечивает поиск и извлечение релевантной аналитики.
"""

import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)


# --- Локальный морфологический поиск ---------------------------------------
# sentence-transformers в демо-контуре обычно недоступен, поэтому поиск по
# ключевым словам должен работать не только при точном совпадении форм:
# «ставкой» и «ставка» — одно и то же слово для пользователя.
_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]{3,}")
_STOPWORDS = {
    "а", "без", "более", "бы", "был", "была", "были", "было", "быть",
    "в", "вам", "вас", "ваш", "ваша", "ваше", "вашей", "вашего", "вашу",
    "весь", "во", "вот", "все", "всего", "всех", "вы", "где", "да",
    "даже", "для", "до", "его", "ее", "если", "есть", "еще", "же", "за",
    "здесь", "и", "из", "или", "им", "их", "к", "как", "какая", "какие",
    "какой", "когда", "кто", "ли", "либо", "мне", "может", "можете", "мы",
    "на", "надо", "над", "нам", "нас", "наш", "наша", "наше", "нашей",
    "нашего", "не", "него", "нее", "нет", "ни", "ним", "них", "но", "ну",
    "о", "об", "однако", "он", "она", "они", "оно", "от", "очень", "по",
    "под", "при", "про", "с", "со", "сейчас", "так", "также", "такой",
    "там", "те", "тем", "то", "того", "тоже", "той", "только", "том",
    "ты", "у", "уже", "хоть", "чего", "чей", "чем", "что", "чтобы",
    "чья", "эта", "эти", "это", "этого", "этой", "этом", "этот", "я",
    "будет", "будут", "видите", "вижу", "скажите", "расскажите",
    "расскажи", "объясни", "поясни", "покажите", "подскажите", "дайте",
    "хочу", "хотим", "знать",
    "нового", "новое", "новости", "новостей", "новость", "новый",
    "новые", "важно", "важное", "важные", "аналитика", "аналитике",
    "аналитику", "аналитики",
}


def _stem(word: str) -> str:
    """Устойчивая основа слова без внешних зависимостей.

    Первых четырёх букв достаточно, чтобы свести формы «ставка/ставкой»,
    «инфляция/инфляцией», «риски/рисками» к одному ключу. Это не
    лингвистически идеально, но предсказуемо и не требует словарей.
    """
    word = (word or "").lower().replace("ё", "е")
    return word[:4] if len(word) > 4 else word


def _stems(text: str) -> Set[str]:
    """Значимые основы текста; служебные слова и числа отбрасываются."""
    result: Set[str] = set()
    for token in _WORD_RE.findall((text or "").lower().replace("ё", "е")):
        if token in _STOPWORDS or token.isdigit():
            continue
        result.add(_stem(token))
    return result


def _stem_counts(text: str) -> Counter:
    """Частоты значимых основ — чтобы тема, раскрытая в тексте, весила больше."""
    counts: Counter = Counter()
    for token in _WORD_RE.findall((text or "").lower().replace("ё", "е")):
        if token in _STOPWORDS or token.isdigit():
            continue
        counts[_stem(token)] += 1
    return counts



class AlfaAnalyticsRetriever:
    """
    Ретривер для поиска аналитических материалов Альфа-Банка.
    
    Использует семантический поиск для нахождения релевантных материалов.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.analytics_data: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    async def initialize(self, data_path: Optional[str] = None):
        """
        Инициализация ретривера.
        
        Args:
            data_path: Путь к файлу с аналитикой (JSON)
        """
        try:
            # Загрузка данных
            if data_path and Path(data_path).exists():
                with open(data_path, "r", encoding="utf-8") as f:
                    self.analytics_data = json.load(f)
            else:
                # Загрузка из встроенных данных
                self.analytics_data = self._load_default_analytics()
            
            # Попытка загрузить модель для эмбеддингов
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                try:
                    self.logger.info(f"Загрузка модели: {self.model_name}")
                    self.model = SentenceTransformer(self.model_name)
                    
                    # Создание эмбеддингов
                    if self.analytics_data:
                        texts = [
                            f"{item.get('title', '')} {item.get('content', '')}"
                            for item in self.analytics_data
                        ]
                        self.logger.info("Создание эмбеддингов для аналитики...")
                        self.embeddings = self.model.encode(texts, convert_to_numpy=True)
                        self.logger.info(f"Эмбеддинги созданы для {len(self.analytics_data)} материалов")
                except Exception as e:
                    self.logger.warning(f"Не удалось загрузить sentence-transformers: {e}")
                    self.model = None
                    self.embeddings = None
            else:
                self.logger.info("sentence-transformers недоступен, используется поиск по ключевым словам")
                self.model = None
                self.embeddings = None
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации ретривера: {e}")
            # Используем простой поиск по ключевым словам как fallback
            self.analytics_data = self._load_default_analytics()
            self.model = None
            self.embeddings = None

    def _load_default_analytics(self) -> List[Dict[str, Any]]:
        """
        Загрузка реальных аналитических материалов Альфа-Банка из JSON-файла.
        """
        import json
        from pathlib import Path
        
        analytics_path = Path(__file__).resolve().parent.parent / "data" / "alfa_analytics" / "alfa_analytics.json"
        
        if analytics_path.exists():
            try:
                with open(analytics_path, "r", encoding="utf-8") as f:
                    analytics = json.load(f)
                self.logger.info(f"Загружено {len(analytics)} реальных аналитических материалов")
                return analytics
            except Exception as e:
                self.logger.warning(f"Ошибка загрузки реальной аналитики: {e}")
        
        # Fallback на синтетические данные
        self.logger.warning("Используются синтетические аналитические данные")
        return self._load_synthetic_analytics()
    
    def _load_synthetic_analytics(self) -> List[Dict[str, Any]]:
        """Синтетические данные для демонстрации."""
        return [
            {
                "id": "alfa_001",
                "title": "Ключевая ставка ЦБ РФ: ставка без изменения на 14,0%, риторика стала жестче",
                "content": "Банк России сохранил ключевую ставку на уровне 14,0%. Риторика регулятора стала более жесткой, что указывает на возможное продление периода высоких ставок.",
                "date": "2026-09-11",
                "category": "monetary_policy",
                "tags": ["ключевая ставка", "ЦБ РФ", "денежно-кредитная политика", "кредиты"],
            },
            {
                "id": "alfa_002",
                "title": "Обзор рынка золота, август 2026",
                "content": "Цена золота достигла исторических максимумов на фоне геополитической напряженности. Прогнозируем дальнейший рост цен.",
                "date": "2026-08-31",
                "category": "commodities",
                "tags": ["золото", "драгоценные металлы", "товары", "инвестиции"],
            },
            {
                "id": "alfa_003",
                "title": "Тактический взгляд на 3-й квартал 2026 года",
                "content": "Прогнозируем умеренный рост экономики России во втором полугодии 2026 года. Ключевые риски связаны с внешней конъюнктурой.",
                "date": "2026-07-15",
                "category": "macro_outlook",
                "tags": ["макроэкономика", "прогноз", "риски", "финансирование"],
            },
            {
                "id": "alfa_004",
                "title": "Инфляция 25–31 августа: основные выводы",
                "content": "Инфляция продолжает замедляться, однако базовая инфляция остается повышенной. Ключевые драйверы — продовольственные товары и услуги.",
                "date": "2026-09-01",
                "category": "inflation",
                "tags": ["инфляция", "цены", "издержки", "потребительские товары"],
            },
        ]

    async def search(
        self,
        query: str,
        top_k: int = 3,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Семантический поиск релевантной аналитики.
        
        Args:
            query: Поисковый запрос
            top_k: Количество результатов
            category: Фильтр по категории
            
        Returns:
            Релевантные аналитические материалы
        """
        if not self.analytics_data:
            return []
        
        # Фильтрация по категории
        data = self.analytics_data
        if category:
            data = [item for item in data if item.get("category") == category]
        
        if not data:
            return []
        
        # Семантический поиск
        if self.model is not None and self.embeddings is not None and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
                
                # Вычисление косинусного сходства
                similarities = np.dot(self.embeddings, query_embedding) / (
                    np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
                )
                
                # Получение топ-K результатов
                top_indices = np.argsort(similarities)[-top_k:][::-1]
                
                results = []
                for idx in top_indices:
                    if idx < len(self.analytics_data):
                        item = self.analytics_data[idx]
                        item["relevance_score"] = float(similarities[idx])
                        results.append(item)
                
                return results
                
            except Exception as e:
                self.logger.error(f"Ошибка семантического поиска: {e}")
        
        # Fallback: поиск по ключевым словам
        return self._keyword_search(query, data, top_k)

    def _keyword_search(
        self,
        query: str,
        data: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        Поиск по основам слов с весами полей.

        Заголовок и теги важнее полного текста: иначе служебные слова и
        многократно повторённые общие термины («ставка» в дисклеймере)
        перетягивают выдачу. Материалы без единого содержательного
        совпадения не возвращаются — вызывающий код сам решает, что сказать.
        """
        query_stems = _stems(query)
        if not query_stems:
            return []

        scored_items = []
        for item in data:
            title_stems = _stems(item.get("title", ""))
            tag_stems = _stems(" ".join(item.get("tags", []) or []))
            content_counts = _stem_counts(str(item.get("content", ""))[:8000])

            title_hits = len(query_stems & title_stems)
            tag_hits = len(query_stems & tag_stems)
            # Повтор темы в тексте полезен, но не должен перебивать заголовок.
            content_hits = sum(
                min(content_counts.get(stem, 0), 3) for stem in query_stems
            )

            # Заголовок — самый сильный сигнал, затем теги, затем текст.
            score = title_hits * 6 + tag_hits * 3 + content_hits
            if title_hits:
                score += 2

            if score > 0:
                scored_items.append((score, item))

        scored_items.sort(key=lambda pair: pair[0], reverse=True)
        return [
            {**item, "relevance_score": float(score)}
            for score, item in scored_items[:top_k]
        ]
