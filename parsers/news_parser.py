"""
Парсер для сбора новостей из различных источников.
Поддерживает RSS, API и веб-скрейпинг.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import feedparser
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class NewsParser:
    """
    Универсальный парсер новостей.
    
    Поддерживает:
    - RSS-ленты
    - REST API
    - Веб-скрейпинг
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def parse_rss(
        self,
        url: str,
        max_items: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Парсинг RSS-ленты.
        
        Args:
            url: URL RSS-ленты
            max_items: Максимальное количество элементов
            
        Returns:
            Список новостей
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                
            feed = feedparser.parse(response.content)
            news = []
            
            for entry in feed.entries[:max_items]:
                news.append({
                    "id": f"rss_{hash(entry.get('link', ''))}",
                    "title": entry.get("title", ""),
                    "content": entry.get("summary", entry.get("description", "")),
                    "source": feed.feed.get("title", url),
                    "date": entry.get("published", ""),
                    "url": entry.get("link", ""),
                    "category": "general",
                })
            
            self.logger.info(f"Спарсено {len(news)} новостей из {url}")
            return news
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга RSS {url}: {e}")
            return []

    async def parse_api(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Парсинг REST API.
        
        Args:
            url: URL API
            headers: Заголовки запроса
            params: Параметры запроса
            
        Returns:
            Список новостей
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
            
            # Универсальная обработка ответа
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("items", data.get("articles", data.get("news", [])))
            else:
                items = []
            
            news = []
            for item in items:
                news.append({
                    "id": f"api_{hash(str(item))}",
                    "title": item.get("title", item.get("name", "")),
                    "content": item.get("content", item.get("description", item.get("text", ""))),
                    "source": item.get("source", url),
                    "date": item.get("publishedAt", item.get("date", item.get("published", ""))),
                    "url": item.get("url", item.get("link", "")),
                    "category": item.get("category", "general"),
                })
            
            self.logger.info(f"Спарсено {len(news)} новостей из API {url}")
            return news
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга API {url}: {e}")
            return []

    async def parse_html(
        self,
        url: str,
        selector: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """
        Веб-скрейпинг HTML-страницы.
        
        Args:
            url: URL страницы
            selector: CSS-селекторы для извлечения данных
            
        Returns:
            Список новостей
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            news = []
            
            # Пример селекторов:
            # {
            #     "container": ".news-item",
            #     "title": ".news-title",
            #     "content": ".news-content",
            #     "date": ".news-date",
            #     "link": ".news-link",
            # }
            
            containers = soup.select(selector.get("container", "article"))
            
            for container in containers:
                title_elem = container.select_one(selector.get("title", "h2"))
                content_elem = container.select_one(selector.get("content", "p"))
                date_elem = container.select_one(selector.get("date", "time"))
                link_elem = container.select_one(selector.get("link", "a"))
                
                if title_elem:
                    news.append({
                        "id": f"html_{hash(str(container))}",
                        "title": title_elem.get_text(strip=True),
                        "content": content_elem.get_text(strip=True) if content_elem else "",
                        "source": url,
                        "date": date_elem.get("datetime", "") if date_elem else "",
                        "url": link_elem.get("href", "") if link_elem else "",
                        "category": "general",
                    })
            
            self.logger.info(f"Спарсено {len(news)} новостей со страницы {url}")
            return news
            
        except Exception as e:
            self.logger.error(f"Ошибка скрейпинга {url}: {e}")
            return []

    def deduplicate(self, news: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Удаление дубликатов новостей.
        
        Args:
            news: Список новостей
            
        Returns:
            Уникальные новости
        """
        seen = set()
        unique = []
        
        for item in news:
            # Создание уникального ключа на основе заголовка и источника
            key = f"{item.get('title', '')}_{item.get('source', '')}"
            
            if key not in seen:
                seen.add(key)
                unique.append(item)
        
        self.logger.info(f"Удалено дубликатов: {len(news) - len(unique)}")
        return unique

    def filter_by_date(
        self,
        news: List[Dict[str, Any]],
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """
        Фильтрация новостей по дате.
        
        Args:
            news: Список новостей
            days: Количество дней
            
        Returns:
            Отфильтрованные новости
        """
        from datetime import timedelta
        from email.utils import parsedate_to_datetime
        
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered = []
        
        for item in news:
            try:
                date_str = item.get("date", "")
                if not date_str:
                    filtered.append(item)
                    continue
                
                item_date = None
                formats = [
                    "%Y-%m-%d",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%d.%m.%Y",
                ]
                
                # Пробуем стандартные форматы
                for fmt in formats:
                    try:
                        item_date = datetime.strptime(date_str[:19], fmt)
                        break
                    except ValueError:
                        continue
                
                # Пробуем RFC 822 (RSS)
                if item_date is None:
                    try:
                        dt = parsedate_to_datetime(date_str)
                        item_date = dt.replace(tzinfo=None)
                    except (TypeError, ValueError):
                        pass
                
                if item_date is not None:
                    if item_date >= cutoff_date:
                        item["parsed_date"] = item_date.isoformat()
                        filtered.append(item)
                else:
                    filtered.append(item)  # Не удалось распарсить — включаем
                    
            except Exception:
                filtered.append(item)
        
        self.logger.info(f"Отфильтровано по дате: {len(filtered)} из {len(news)}")
        return filtered

    async def collect_from_sources(
        self,
        sources: List[Dict[str, Any]],
        max_days: int = 7,
        max_total: int = 25,
    ) -> List[Dict[str, Any]]:
        """
        Сбор новостей из нескольких источников с дедупликацией и фильтрацией.
        
        Args:
            sources: Список источников (из config/news_sources.json)
            max_days: Максимальный возраст новости в днях
            max_total: Максимальное общее количество новостей
            
        Returns:
            Объединённый список новостей
        """
        all_news = []
        
        for source in sources:
            if not source.get("enabled", True):
                continue
                
            url = source.get("url", "")
            source_type = source.get("type", "rss")
            name = source.get("name", url)
            max_items = source.get("max_items", 20)
            
            try:
                if source_type == "rss":
                    news = await self.parse_rss(url, max_items=max_items)
                elif source_type == "api":
                    news = await self.parse_api(url, headers=source.get("headers"), params=source.get("params"))
                elif source_type == "html":
                    news = await self.parse_html(url, source.get("selector", {}))
                else:
                    self.logger.warning(f"Неизвестный тип источника: {source_type}")
                    continue
                
                # Добавляем имя источника
                for item in news:
                    item["source"] = name
                
                all_news.extend(news)
                self.logger.info(f"{name}: получено {len(news)} новостей")
                
            except Exception as e:
                self.logger.error(f"Ошибка сбора из {name}: {e}")
        
        # Дедупликация
        unique = self.deduplicate(all_news)
        
        # Фильтрация по дате
        filtered = self.filter_by_date(unique, days=max_days)
        
        # Ограничение количества
        if len(filtered) > max_total:
            filtered = filtered[:max_total]
        
        self.logger.info(f"Итого собрано: {len(filtered)} уникальных новостей из {len(sources)} источников")
        return filtered
