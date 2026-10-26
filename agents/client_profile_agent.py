"""
Агент анализа профиля клиента.
Определяет бизнес-контекст компании: отрасль, масштаб, продукты, связи.
"""

import json
from typing import Any, Dict, List

from agents.base_agent import AgentContext, BaseAgent
from services.client_data import find_client_row
from services.profile_store import get_custom_profile


class ClientProfileAgent(BaseAgent):
    """
    Агент для анализа профиля клиента и определения бизнес-контекста.
    
    Извлекает ключевые характеристики компании, которые влияют на значимость новостей:
    - Отрасль и виды деятельности
    - Масштаб бизнеса
    - Банковские продукты
    - Связи с другими компаниями
    - Регион присутствия
    """

    async def execute(self, context: AgentContext) -> AgentContext:
        """
        Анализ профиля клиента.
        
        Args:
            context: Контекст с client_id
            
        Returns:
            Обновленный контекст с client_profile
        """
        self.logger.info(f"Анализ профиля клиента: {context.client_id}")
        
        # Загрузка данных о клиенте
        client_data = await self._load_client_data(context.client_id)
        
        if not client_data:
            step = self.create_step(
                step_number=1,
                action="load_client_data",
                input_data={"client_id": context.client_id},
                output_data={"error": "Клиент не найден"},
                success=False,
                error_message=f"Профиль клиента {context.client_id} не найден",
            )
            context.add_step(step)
            return context
        
        # Анализ профиля с помощью LLM
        profile_analysis = await self._analyze_profile(client_data)
        
        # Сохранение результатов
        context.client_profile = {
            "client_id": context.client_id,
            "raw_data": client_data,
            "analysis": profile_analysis,
            "key_features": profile_analysis.get("key_features", {}),
            "industry": profile_analysis.get("industry", ""),
            "business_scale": profile_analysis.get("business_scale", ""),
            "products": profile_analysis.get("products", []),
            "region": profile_analysis.get("region", ""),
            "has_fts": profile_analysis.get("has_fts", False),
            "relevance_criteria": profile_analysis.get("relevance_criteria", []),
            "regions": profile_analysis.get("regions", []),
            "connections": profile_analysis.get("connections", []),
            "risk_factors": profile_analysis.get("risk_factors", []),
        }
        
        # Трассировка
        source = client_data.get("_SOURCE") or "df_Uid_data_hack.csv (реальные данные)"
        step = self.create_step(
            step_number=1,
            action="analyze_client_profile",
            input_data={
                "client_id": context.client_id,
                "source": source,
                "legal_entity": client_data.get("_LEGAL_ENTITY", ""),
                "raw_fields_used": ["SYNTHETIC_U", "MAINOKVED_CODE", "MAINOKVED_NAME", "REVENUE_COMPANY", "AMOUNT_WORKERS_FNS_GRADATION", "CL_TYPE", "REGION", "CITY", "CL_PRODUCT_*_MARK", "FTS_FLAG", "FTS_COUNTRY_NAME", "FACTORING_MARK"],
            },
            output_data={
                "legal_entity": client_data.get("_LEGAL_ENTITY", ""),
                "industry": context.client_profile.get("industry", "")[:80],
                "business_scale": context.client_profile.get("business_scale", ""),
                "products": context.client_profile.get("products", []),
                "region": context.client_profile.get("region", ""),
                "has_fts": context.client_profile.get("has_fts", False),
                "fts_country": context.client_profile.get("analysis", {}).get("fts_country", ""),
                "risk_factors": context.client_profile.get("risk_factors", []),
                "relevance_criteria": context.client_profile.get("relevance_criteria", []),
            },
        )
        context.add_step(step)
        
        self.logger.info(f"Профиль проанализирован: {context.client_profile['industry']}")
        return context

    async def _load_client_data(self, client_id: str) -> Dict[str, Any]:
        """
        Загрузка данных о клиенте:
        1) профиль, созданный при регистрации;
        2) реальный CSV кейса;
        3) синтетический профиль.
        """
        custom = get_custom_profile(client_id)
        if custom:
            return custom

        try:
            row = find_client_row(client_id)
            if row:
                return row
        except Exception as e:
            self.logger.warning(f"Ошибка загрузки данных из CSV: {e}")

        return self._generate_synthetic_profile(client_id)

    def _generate_synthetic_profile(self, client_id: str) -> Dict[str, Any]:
        """
        Генерация синтетического профиля для демонстрации.
        """
        return {
            "SYNTHETIC_U": client_id,
            "ORG_TYPE": "ООО",
            "OKFS_NAME": "Частная собственность",
            "COMPANY_AGE_YEARS_GRADATION": "5-10 лет",
            "ECO_MARK_LABEL": "Растущий бизнес",
            "MAINOKVED_CODE": "62.01",
            "MAINOKVED_NAME": "Разработка компьютерного программного обеспечения",
            "NEGATIVEMARK": 0,
            "AMOUNT_WORKERS_FNS_GRADATION": "50-100",
            "CL_PRODUCT_RKO_MARK": 1,
            "CL_PRODUCT_GAR_MARK": 0,
            "CL_PRODUCT_LOA_MARK": 1,
            "CL_PRODUCT_LEA_MARK": 0,
            "CL_PRODUCT_DEP_MARK": 1,
            "CL_PRODUCT_ZPP_MARK": 1,
            "FTS_FLAG": 1,
            "FTS_COUNTRY_NAME": "Китай",
            "FACTORING_MARK": 0,
            "REVENUE_COMPANY": 2500000000,
            "AMOUNT_WORKERS_SPARK_GRADATION": "50-100",
            "GROUP_ID": f"GRP_{client_id[:8]}",
            "CL_TYPE": "Действующий клиент",
            "REGION": "Москва",
            "CITY": "Москва",
        }

    async def _analyze_profile(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализ профиля клиента на основе реальных данных.
        
        Args:
            client_data: Сырые данные о клиенте
            
        Returns:
            Структурированный анализ профиля
        """
        # Извлекаем ключевые характеристики из реальных данных
        okved = client_data.get("MAINOKVED_NAME", "")
        okved_code = client_data.get("MAINOKVED_CODE", "")
        revenue = client_data.get("REVENUE_COMPANY", "")
        workers = client_data.get("AMOUNT_WORKERS_FNS_GRADATION", "")
        region = client_data.get("REGION", "")
        city = client_data.get("CITY", "")
        company_age = client_data.get("COMPANY_AGE_YEARS_GRADATION", "")
        eco_stage = client_data.get("ECO_MARK_LABEL", "")
        cl_type = client_data.get("CL_TYPE", "")
        
        # Банковские продукты
        products = []
        rko = str(client_data.get("CL_PRODUCT_RKO_MARK", "0")).strip()
        if rko in ("1", "1.0", "True", "true"):
            products.append("Расчётно-кассовое обслуживание")
        loa = str(client_data.get("CL_PRODUCT_LOA_MARK", "0")).strip()
        if loa in ("1", "1.0", "True", "true"):
            products.append("Кредитные продукты")
        dep = str(client_data.get("CL_PRODUCT_DEP_MARK", "0")).strip()
        if dep in ("1", "1.0", "True", "true"):
            products.append("Депозитные продукты")
        gar = str(client_data.get("CL_PRODUCT_GAR_MARK", "0")).strip()
        if gar in ("1", "1.0", "True", "true"):
            products.append("Банковские гарантии")
        lea = str(client_data.get("CL_PRODUCT_LEA_MARK", "0")).strip()
        if lea in ("1", "1.0", "True", "true"):
            products.append("Лизинговые продукты")
        zpp = str(client_data.get("CL_PRODUCT_ZPP_MARK", "0")).strip()
        if zpp in ("1", "1.0", "True", "true"):
            products.append("Зарплатный проject")
        
        # Внешнеэкономическая деятельность
        fts = str(client_data.get("FTS_FLAG", "0")).strip()
        fts_flag = fts in ("1", "1.0", "True", "true")
        fts_country = client_data.get("FTS_COUNTRY_NAME", "")
        factoring_mark = str(client_data.get("FACTORING_MARK", "0")).strip()
        factoring = factoring_mark in ("1", "1.0", "True", "true")
        
        # Группа компаний
        group_id = client_data.get("GROUP_ID", "")
        
        # Fallback для region
        if not region:
            region = client_data.get("REGION", "")
        
        # Для профиля, созданного пользователем, показываем выбранную отрасль и масштаб
        industry_label = client_data.get("_INDUSTRY_LABEL") or okved
        scale_label = client_data.get("_SCALE_LABEL") or self._classify_scale(revenue, workers)

        # Формируем анализ
        analysis = {
            "industry": industry_label,
            "industry_code": okved_code,
            "business_scale": scale_label,
            "revenue": revenue,
            "workers": workers,
            "region": region or client_data.get("REGION", ""),
            "city": city,
            "company_age": company_age,
            "growth_stage": eco_stage,
            "client_type": cl_type,
            "products": products,
            "has_fts": fts_flag,
            "fts_country": fts_country,
            "has_factoring": factoring,
            "group_id": group_id,
            "key_features": {
                "okved": okved,
                "industry": industry_label,
                "okved_code": okved_code,
                "revenue": revenue,
                "workers": workers,
            "region": region or client_data.get("REGION", ""),
                "city": city,
                "company_age": company_age,
                "growth_stage": eco_stage,
                "client_type": cl_type,
                "products": products,
            "has_fts": fts_flag,
                "fts_country": fts_country,
                "has_factoring": factoring,
                "group_id": group_id,
            },
            "risk_factors": self._identify_risks(client_data),
            "relevance_criteria": self._get_relevance_criteria(okved, products, fts_flag),
        }
        
        return analysis
    
    def _classify_scale(self, revenue: str, workers: str) -> str:
        """Классификация масштаба бизнеса."""
        try:
            rev = float(revenue) if revenue else 0
            if rev >= 15e9:
                return "Крупный бизнес (выручка > 15 млрд ₽)"
            elif rev >= 1e9:
                return "Средний бизнес (выручка 1-15 млрд ₽)"
            elif rev >= 100e6:
                return "Малый бизнес (выручка 100 млн - 1 млрд ₽)"
            else:
                return "Микробизнес (выручка < 100 млн ₽)"
        except (ValueError, TypeError):
            return "Не определён"
    
    def _identify_risks(self, client_data: Dict[str, Any]) -> List[str]:
        """Определение факторов риска."""
        risks = []
        
        # Кредитные риски
        loa = str(client_data.get("CL_PRODUCT_LOA_MARK", "0")).strip()
        if loa in ("1", "1.0", "True", "true"):
            risks.append("Зависимость от заемного финансирования")
        
        # Валютные риски
        if client_data.get("FTS_FLAG") in ("1", "1.0"):
            risks.append("Валютные риски (внешнеэкономическая деятельность)")
        
        # Риски факторинга
        if client_data.get("FACTORING_MARK") in ("1", "1.0"):
            risks.append("Риски дебиторской задолженности")
        
        # Возраст компании
        age = client_data.get("COMPANY_AGE_YEARS_GRADATION", "")
        if age in ("0-3", "3-5"):
            risks.append("Молодая компания (повышенные риски)")
        
        return risks
    
    def _get_relevance_criteria(self, okved: str, products: List[str], fts: bool) -> List[str]:
        """Критерии релевантности новостей."""
        criteria = []
        
        # По отрасли
        if "компьютер" in okved.lower() or "программ" in okved.lower() or "IT" in okved:
            criteria.extend(["IT-новости", "Технологические тренды", "Кибербезопасность"])
        elif "торгов" in okved.lower():
            criteria.extend(["Торговые новости", "Потребительский спрос", "Логистика"])
        elif "производ" in okved.lower() or "обработк" in okved.lower():
            criteria.extend(["Производственные новости", "Сырьевые рынки", "Промышленность"])
        elif "строитель" in okved.lower():
            criteria.extend(["Строительные новости", "Недвижимость", "Инфраструктура"])
        elif "транспорт" in okved.lower() or "перевозк" in okved.lower():
            criteria.extend(["Транспортные новости", "Логистика", "Топливный рынок"])
        elif "сельск" in okved.lower() or "растениевод" in okved.lower() or "животновод" in okved.lower():
            criteria.extend(["Аграрные новости", "Урожай", "Сельхозтехника"])
        elif "финанс" in okved.lower() or "банк" in okved.lower():
            criteria.extend(["Финансовые новости", "Кредитный рынок", "Регулирование"])
        
        # По продуктам
        if "Кредитные продукты" in products:
            criteria.append("Ключевая ставка и кредитные ставки")
        if "Депозитные продукты" in products:
            criteria.append("Депозитные ставки")
        if "Банковские гарантии" in products:
            criteria.append("Государственные закупки и тендеры")
        if "Лизинговые продукты" in products:
            criteria.append("Лизинговый рынок")
        if "Зарплатный проект" in products:
            criteria.append("Трудовое законодательство")
        
        # По ВЭД
        if fts:
            criteria.extend(["Международная торговля", "Санкции", "Валютный курс"])
        
        # Общие критерии
        criteria.extend(["Макроэкономика", "Налоговые изменения", "Регулирование"])
        
        return list(set(criteria))
