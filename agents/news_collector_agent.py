"""
Агент сбора и классификации новостей.
Собирает новости из внешних источников и классифицирует их.
"""

import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List

from agents.base_agent import AgentContext, BaseAgent


class NewsCollectorAgent(BaseAgent):
    """
    Агент для сбора и первичной обработки новостей.
    
    Функции:
    - Сбор новостей из внешних источников
    - Сбор аналитических материалов Альфа-Банка
    - Классификация по темам
    - Извлечение ключевой информации
    """

    async def execute(self, context: AgentContext) -> AgentContext:
        """
        Сбор и классификация новостей.
        
        Args:
            context: Текущий контекст
            
        Returns:
            Обновленный контекст с новостями
        """
        self.logger.info("Сбор новостей и аналитических материалов")
        
        # Сбор внешних новостей
        external_news = await self._collect_external_news()
        
        # Сбор аналитики Альфа-Банка
        alfa_analytics = await self._collect_alfa_analytics()
        
        # Классификация и извлечение ключевой информации
        classified_news = await self._classify_news(external_news)
        
        context.news_items = classified_news
        context.alfa_analytics = alfa_analytics
        
        # Трассировка
        step = self.create_step(
            step_number=2,
            action="collect_and_classify_news",
            input_data={
                "sources": ["внешние новости", "аналитика Альфа-Банка"],
                "news_categories": ["monetary_policy", "inflation", "currency", "commodities", "technology", "agriculture", "regulation", "real_estate", "ecommerce", "automotive", "pharma", "tourism"],
            },
            output_data={
                "news_count": len(classified_news),
                "news_titles": [{"id": n["id"], "title": n["title"][:80], "category": n.get("category", "")} for n in classified_news],
                "analytics_count": len(alfa_analytics),
                "analytics_titles": [{"id": a["id"], "title": a["title"][:80], "category": a.get("category", ""), "source_file": a.get("source_file", "")} for a in alfa_analytics],
            },
        )
        context.add_step(step)
        
        self.logger.info(f"Собрано {len(classified_news)} новостей, {len(alfa_analytics)} аналитических материалов")
        return context

    async def _collect_external_news(self) -> List[Dict[str, Any]]:
        """
        Сбор новостей из внешних источников (RSS).
        При недоступности сети — fallback на локальные демо-данные.
        """
        from pathlib import Path
        from parsers.news_parser import NewsParser
        
        # 1. Пробуем собрать реальные новости из RSS
        sources_path = Path(__file__).resolve().parent.parent / "config" / "news_sources.json"
        try:
            if sources_path.exists():
                with open(sources_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                parser = NewsParser()
                settings = config.get("settings", {})
                sources = config.get("external_sources", [])
                
                real_news = await parser.collect_from_sources(
                    sources,
                    max_days=settings.get("max_days_lookback", 7),
                    max_total=settings.get("max_total_news", 25),
                )
                
                if real_news:
                    # Фильтруем нерелевантные для бизнеса темы
                    relevant_news = [
                        n for n in real_news
                        if self._is_business_relevant(n)
                    ]
                    
                    # У RSS не всегда есть анонс: подтягиваем описание со страницы.
                    await parser.enrich_content(relevant_news, limit=15)

                    # Присваиваем уникальные ID
                    for i, item in enumerate(relevant_news):
                        if not item.get("id"):
                            item["id"] = f"rss_{i:03d}"
                        item.setdefault("category", "general")
                        item["is_real"] = True
                    
                    self.logger.info(
                        f"Собрано {len(real_news)} реальных новостей из RSS, "
                        f"после фильтрации бизнес-релевантности: {len(relevant_news)}"
                    )
                    return relevant_news
        except Exception as e:
            self.logger.warning(f"Не удалось собрать реальные новости: {e}")
        
        # 2. Fallback: локальные демо-данные
        self.logger.info("Используются локальные демо-новости")
        news = [
            {
                "id": "news_001",
                "title": "ЦБ РФ сохранил ключевую ставку на уровне 14%",
                "content": "Совет директоров Банка России принял решение сохранить ключевую ставку на уровне 14% годовых. Это первая пауза в цикле смягчения денежно-кредитной политики после десяти последовательных снижений ставки, начавшегося в июне 2025 года. Риторика регулятора стала более жесткой.",
                "source": "Банк России",
                "date": "2026-09-11",
                "category": "monetary_policy",
                "url": "https://www.cbr.ru/press/",
            },
            {
                "id": "news_002",
                "title": "Инфляция в России замедлилась до 6.2% годовых",
                "content": "По данным Росстата, инфляция в августа 2026 года составила 6.2% в годовом выражении, что ниже прогнозов рынка. Базовая инфляция остается повышенной. Ключевые драйверы — продовольственные товары и услуги.",
                "source": "Росстат",
                "date": "2026-09-15",
                "category": "inflation",
                "url": "https://rosstat.gov.ru/",
            },
            {
                "id": "news_003",
                "title": "Рубль укрепился к доллару на 2%",
                "content": "Курс рубля к доллару укрепился на 2% на торгах Московской биржи на фоне роста цен на нефть и снижения импорта. Официальный курс ЦБ составил 78.5 рубля за доллар.",
                "source": "Московская биржа",
                "date": "2026-09-16",
                "category": "currency",
                "url": "https://www.moex.com/",
            },
            {
                "id": "news_004",
                "title": "Экспорт зерна побил рекорд",
                "content": "Россия экспортировала рекордные 60 млн тонн зерна в текущем сельскохозяйственном году. Основные направления экспорта — Ближний Восток и Северная Африка.",
                "source": "Минсельхоз",
                "date": "2026-09-17",
                "category": "agriculture",
                "url": "https://mcx.gov.ru/",
            },
            {
                "id": "news_005",
                "title": "IT-сектор показал рост 15%",
                "content": "Российский IT-сектор показал рост выручки на 15% за первое полугодие 2026 года. Основные драйверы — импортозамещение и государственные контракты.",
                "source": "Ассоциация предприятий компьютерных и информационных технологий",
                "date": "2026-09-18",
                "category": "technology",
                "url": "https://www.apkit.ru/",
            },
            {
                "id": "news_006",
                "title": "ЦБ РФ ужесточил макропруденциальные требования",
                "content": "Банк России ввел повышенные коэффициенты риска для ипотечных кредитов с низким взносом. Мера направлена на охлаждение перегретого рынка недвижимости.",
                "source": "Банк России",
                "date": "2026-09-10",
                "category": "regulation",
                "url": "https://www.cbr.ru/press/",
            },
            {
                "id": "news_007",
                "title": "Нефть Brent превысила $90 за баррель",
                "content": "Цена нефти марки Brent превысила $90 за баррель на фоне сокращения добычи ОПЕК+ и роста спроса. Это максимум с начала года.",
                "source": "Reuters",
                "date": "2026-09-14",
                "category": "commodities",
                "url": "https://www.reuters.com/",
            },
            {
                "id": "news_008",
                "title": "Золото достигло исторического максимума",
                "content": "Цена золота достигла исторического максимума $2,850 за унцию на фоне геополитической напряженности и ослабления доллара.",
                "source": "Bloomberg",
                "date": "2026-09-13",
                "category": "commodities",
                "url": "https://www.bloomberg.com/",
            },
            {
                "id": "news_009",
                "title": "Ключевая ставка ЦБ РФ: прогнозы на 2026 год",
                "content": "Аналитики ожидают, что ЦБ РФ может начать снижение ключевой ставки в конце 2026 года при условии замедления инфляции до целевого уровня 4%.",
                "source": "Интерфакс",
                "date": "2026-09-12",
                "category": "monetary_policy",
                "url": "https://www.interfax.ru/",
            },
            {
                "id": "news_010",
                "title": "Рынок недвижимости: цены выросли на 20%",
                "content": "Цены на первичном рынке недвижимости выросли на 20% за год. Основной драйнер — дефицит предложения и высокий спрос.",
                "source": "ЦИАН",
                "date": "2026-09-11",
                "category": "real_estate",
                "url": "https://www.cian.ru/",
            },
            {
                "id": "news_011",
                "title": "Электронная коммерция выросла на 25%",
                "content": "Обьем рынка электронной коммерции в России вырос на 25% за первое полугодие 2026 года. Лидеры — маркетплейсы и доставка еды.",
                "source": "Data Insight",
                "date": "2026-09-10",
                "category": "ecommerce",
                "url": "https://www.datainsight.ru/",
            },
            {
                "id": "news_012",
                "title": "Автопром: продажи выросли на 10%",
                "content": "Продажи легковых автомобилей в России выросли на 10% за 8 месяцев 2026 года. Лидеры — Lada и китайские бренды.",
                "source": "Ассоциация европейского бизнеса",
                "date": "2026-09-09",
                "category": "automotive",
                "url": "https://www.aebrus.ru/",
            },
            {
                "id": "news_013",
                "title": "Сельское хозяйство: рекордный урожай",
                "content": "Россия собрала рекордный урожай зерновых — 145 млн тонн. Это на 10% больше прошлого года.",
                "source": "Минсельхоз",
                "date": "2026-09-08",
                "category": "agriculture",
                "url": "https://mcx.gov.ru/",
            },
            {
                "id": "news_014",
                "title": "Фармацевтика: рост производства 12%",
                "content": "Производство лекарственных средств в России выросло на 12% за первое полугодие 2026 года.",
                "source": "Минпромторг",
                "date": "2026-09-07",
                "category": "pharma",
                "url": "https://minpromtorg.gov.ru/",
            },
            {
                "id": "news_015",
                "title": "Туризм: рост внутреннего туризма 30%",
                "content": "Внутренний туризм в России вырос на 30% за летний сезон 2026 года. Популярные направления — Кавказ, Алтай и Байкал.",
                "source": "Ростуризм",
                "date": "2026-09-06",
                "category": "tourism",
                "url": "https://www.russiatourism.ru/",
            },
        ]
        
        # Помечаем локальные данные
        for i, item in enumerate(news):
            item.setdefault("id", f"demo_{i:03d}")
            item.setdefault("category", "general")
            item["is_real"] = False
        
        return news

    async def _collect_alfa_analytics(self) -> List[Dict[str, Any]]:
        """
        Сбор аналитических материалов Альфа-Банка из JSON-файла (OCR-извлечение).
        """
        import json
        from pathlib import Path
        
        analytics_path = Path(__file__).resolve().parent.parent / "data" / "alfa_analytics" / "alfa_analytics.json"
        self.logger.info(f"Путь к аналитике: {analytics_path}, существует: {analytics_path.exists()}")
        
        if analytics_path.exists():
            try:
                with open(analytics_path, "r", encoding="utf-8") as f:
                    analytics = json.load(f)
                self.logger.info(f"Загружено {len(analytics)} аналитических материалов из {analytics_path}")
                return analytics
            except Exception as e:
                self.logger.warning(f"Ошибка загрузки аналитики: {e}")
        
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
                "content": "Цена золота достигла исторических максимумус на фоне геополитической напряженности. Прогнозируем дальнейший рост цен.",
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

    async def _classify_news(self, news: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Классификация новостей: локальные эвристики + LLM (если доступен).
        
        Args:
            news: Список новостей
            
        Returns:
            Классифицированные новости с ключевыми фактами
        """
        if not news:
            return []
        
        classified = []
        
        for item in news:
            try:
                # Локальная классификация (всегда работает)
                local = self._local_classify(item)
                
                # Пробуем LLM-классификацию как дополнение
                try:
                    llm_result = await self._llm_classify(item)
                    # Объединяем: LLM может уточнить категорию
                    if llm_result and llm_result.get("category"):
                        local["category"] = llm_result.get("category", local.get("category"))
                    local["llm_analysis"] = llm_result
                except Exception:
                    pass
                
                classified_item = {
                    **item,
                    "category": local.get("category", item.get("category", "general")),
                    "classification": local,
                    "collected_at": datetime.now().isoformat(),
                }
                classified.append(classified_item)
                
            except Exception as e:
                self.logger.error(f"Ошибка классификации новости {item.get('id')}: {e}")
                classified.append({
                    **item,
                    "category": item.get("category", "general"),
                    "classification": {"category": "unknown", "error": str(e)},
                    "collected_at": datetime.now().isoformat(),
                })
        
        return classified
    
    def _local_classify(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Локальная классификация новости по ключевым словам.
        Работает без LLM — основной метод классификации.
        """
        text = f"{item.get('title', '')} {item.get('content', '')}".lower()
        
        # Правила классификации: (категория, [(ключевое слово, вес), ...])
        rules = [
            ("monetary_policy", [("ключевая ставка", 3), ("цб рф", 3), ("банк россии", 2), ("денежно-кредитная", 3), ("дкп", 3), ("рефинансировани", 2), ("председатель цб", 2)]),
            ("inflation", [("инфляция", 3), ("базовая инфляция", 3), ("потребительски", 2), ("дефляция", 3), ("рост цен", 2)]),
            ("currency", [("рубль", 2), ("курс рубля", 3), ("доллар", 1), ("евро", 1), ("валют", 2), ("бивалютн", 3), ("мультивалютн", 3), ("курс валют", 3)]),
            ("commodities", [("нефть", 2), ("нефтепродукт", 3), ("brent", 3), ("urals", 3), ("газ", 1), ("природный газ", 3), ("золото", 3), ("металл", 2), ("никель", 3), ("палладий", 3), ("уголь", 3), ("сырьев", 2)]),
            ("agriculture", [("урожай", 3), ("зерн", 3), ("пшениц", 3), ("ячмен", 3), ("подсолнечник", 3), ("посев", 2), ("уборк", 2), ("аграрн", 2), ("мясо птицы", 3), ("растениевод", 3)]),
            ("technology", [("it-сектор", 3), ("it-рынок", 3), ("технолог", 2), ("цифров", 2), ("нейросет", 3), ("кибербезопас", 3), ("процессор", 3), ("импортозамещен", 2), ("софт", 3), ("телеком", 3), ("мтс", 3), ("билайн", 3), ("мегафон", 3), ("тарифы на связь", 3)]),
            ("banking", [("кредит", 2), ("ипотек", 3), ("вклад", 3), ("депозит", 3), ("лизинг", 3), ("процентная ставк", 3), ("банк", 1)]),
            ("regulation", [("регулирован", 3), ("законопроект", 3), ("налог", 2), ("пошлин", 3), ("санкц", 3), ("лицензир", 3), ("надзор", 2), ("макропруденциальн", 3)]),
            ("real_estate", [("недвижим", 3), ("жиль", 2), ("строительств", 2), ("квартир", 2), ("жк", 2)]),
            ("labor_market", [("рынок труд", 3), ("безработиц", 3), ("зарплат", 3), ("ваканси", 2), ("кадров", 2), ("трудов", 2)]),
            ("energy", [("электроэнерг", 3), ("энергоснабж", 3), ("тариф", 2), ("теплоэнерг", 3), ("россети", 3)]),
            ("defense", [("оборон", 3), ("военн", 2), ("спецоперац", 3), ("сво", 2), ("оборонзаказ", 3)]),
            ("geopolitics", [("переговор", 2), ("саммит", 3), ("оон", 3), ("внешнеполит", 3), ("посол", 2), ("дипломат", 2), ("нато", 2)]),
            ("macro_outlook", [("ввп", 3), ("макроэконом", 3), ("экономический рост", 3), ("рецессия", 3), ("бюджет", 2), ("минфин", 2)]),
            ("trade", [("экспорт", 2), ("импорт", 2), ("внешняя торговля", 3), ("вэд", 3), ("торговый баланс", 3), ("ритейл", 3), ("розничн", 3), ("логист", 2)]),
            ("industry", [("промышленн", 2), ("производств", 2), ("завод", 2), ("станкостроен", 3), ("машиностроен", 3)]),
        ]
        
        scores = {}
        for category, keywords in rules:
            score = sum(weight for kw, weight in keywords if kw in text)
            if score > 0:
                scores[category] = score
        
        # Выбираем категорию с максимальным скором
        if scores:
            best_category = max(scores, key=scores.get)
        else:
            best_category = item.get("category", "general")
        
        # Определение тональности
        positive_words = ["рост", "увеличен", "рекорд", "позитив", "улучшен", "рост ", "поддержк", "снижени", "стабилизац"]
        negative_words = ["снижен", "падени", "убыток", "кризис", "угроз", "риск", "санкц", "ограничен", "запрет", "проблем"]
        
        pos = sum(1 for w in positive_words if w in text)
        neg = sum(1 for w in negative_words if w in text)
        
        if pos > neg:
            impact = "positive"
        elif neg > pos:
            impact = "negative"
        else:
            impact = "neutral"
        
        return {
            "category": best_category,
            "matched_rules": scores,
            "business_impact": impact,
            "confidence": "high" if scores.get(best_category, 0) >= 2 else "medium",
        }
    
    def _is_business_relevant(self, item: Dict[str, Any]) -> bool:
        """
        Проверка, относится ли новость к деловой/экономической тематике.
        Отсеивает спорт, культуру, происшествия, некрологи.
        """
        text = f"{item.get('title', '')} {item.get('content', '')}".lower()
        
        # Признаки нерелевантности
        irrelevant = [
            "футбол", "хоккей", "теннис", "шахмат", "спорт", "олимпиад", "чемпион",
            "скончался", "умер ", "умерла", "не стало", "некролог", "похорон",
            "день рождения", "дни рождения", "именинник", "юбилей",
            "сериал", "фильм", "концерт", "фестивал", "выставк", "премьер",
            "кража", "угон", "дтп", "происшестви",
            "тройни", "двойни", "родила",
            "продажи билетов", "билетов на", "гастрол",
            "падел", "кортов", "стрельб", "погиб", "ранен", "омбудсмен",
            "бпла", "пво", "единая россия", "песков", "кремл", "спецпосланник",
        ]
        
        has_irrelevant = any(word in text for word in irrelevant)

        # Политические сюжеты отсекаем, если в заголовке нет явного делового угла.
        political_markers = [
            "выборы", "избирател", "кандидат", "президент", "оппозиц",
            "партия", "голосов", "импичмент", "скандал", "инаугурац",
            "предвыборн", "рейтинг кандидат",
        ]
        title = item.get("title", "").lower()
        title_business = bool(re.search(
            r"(?<![а-яa-z])(эконом|бизнес|компани|кредит|инвест|рынок|"
            r"экспорт|импорт|производств|промышленн|финанс|торгов|валют|"
            r"ставк|инфляц|регулир|закон|налог|технолог|бюджет)",
            title,
        )) or "банк" in title
        if any(marker in text for marker in political_markers) and not title_business:
            return False

        # Здоровье и общая геополитика без делового угла — не для бизнес-агента.
        soft_irrelevant_title = [
            "саммит", "лидеры", "посол", "дипломат", "нато", "госдеп",
            "коронавирус", "covid", "вакцин", "заболеваем", "роспотребнадзор",
            "минздрав", "эпидем", "грипп",
        ]
        if any(marker in title for marker in soft_irrelevant_title) and not title_business:
            return False

        # Политика, происшествия и светская хроника без делового угла.
        civic_title_markers = [
            "песков", "кремл", "омбудсмен", "единая россия", "госдум",
            "сенатор", "депутат", "съезд", "переговор", "спецпосланник",
            "бпла", "пво", "губернатор", "украин", "киев", "зеленск",
            "трамп", "байден", "евросоюз", "нато", "госдеп", "посол",
            "дипломат", "саммит", "лидеры", "стрельб", "погиб", "ранен",
            "падел", "кортов", "путин", "нетаньяху", "израил", "палестин",
            "газа", "иордан", "сирия", "иран", "чичваркин", "иноагент",
            "оштрафовал", "суд ",
        ]
        if any(marker in title for marker in civic_title_markers) and not title_business:
            return False

        lifestyle_title_markers = [
            "фэшн", "люкс", "hermès", "hermes", "мод", "светск",
            "знаменитост", "сериал", "кино", "музык",
        ]
        if any(marker in title for marker in lifestyle_title_markers) and not title_business:
            return False
        
        # Деловые маркеры (защищают от отсеивания)
        business_markers = [
            "эконом", "бизнес", "компани", "банк", "кредит", "инвестиц", "рынок",
            "экспорт", "импорт", "производств", "промышленн", "финанс", "торгов",
            "валют", "ставк", "инфляц", "регулир", "закон", "налог", "технолог",
        ]
        has_business = any(marker in text for marker in business_markers)
        
        if has_irrelevant and not has_business:
            return False
        
        return True
    
    async def _llm_classify(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """LLM-классификация новости (опционально)."""
        system_prompt = """Ты — эксперт по классификации деловых новостей.
Определи категорию из списка: monetary_policy, inflation, currency, commodities, agriculture,
technology, banking, regulation, real_estate, labor_market, energy, defense, geopolitics,
macro_outlook, trade, industry, general.
Укажи бизнес-влияние (positive/negative/neutral) и затронутые отрасли.
Ответь в формате JSON: {"category": "...", "business_impact": "...", "affected_industries": [...]}"""
        
        prompt = f"""Заголовок: {item.get('title', '')}
Содержание: {item.get('content', '')[:500]}
Источник: {item.get('source', '')}"""
        
        return await self.call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
