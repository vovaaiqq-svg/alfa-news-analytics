(() => {
    "use strict";

    const STORAGE_KEY = "alfa_business_profile_v4";

    const $ = (selector, root = document) => root.querySelector(selector);
    const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

    const CATEGORY_LABELS = {
        monetary_policy: "Денежная политика",
        macro_outlook: "Макроэкономика",
        inflation: "Инфляция",
        currency: "Валюта",
        agriculture: "АПК",
        technology: "Технологии",
        regulation: "Регулирование",
        commodities: "Сырьё",
        real_estate: "Недвижимость",
        ecommerce: "E-commerce",
        automotive: "Авто",
        pharma: "Фармацевтика",
        tourism: "Туризм",
        general: "Общее",
    };

    const FALLBACK_META = {
        industries: [
            { key: "construction", label: "Строительство и недвижимость", okved: "Строительство жилых и нежилых зданий", code: "41.20" },
            { key: "it", label: "Информационные технологии", okved: "Разработка компьютерного программного обеспечения", code: "62.01" },
            { key: "trade", label: "Оптовая и розничная торговля", okved: "Торговля оптовая неспециализированная", code: "46.90" },
            { key: "manufacturing", label: "Производство и промышленность", okved: "Производство прочих готовых изделий", code: "32.99" },
            { key: "finance", label: "Финансы и страхование", okved: "Деятельность по предоставлению финансовых услуг", code: "64.99" },
            { key: "logistics", label: "Логистика и транспорт", okved: "Деятельность грузового автомобильного транспорта", code: "49.41" },
            { key: "agriculture", label: "Сельское хозяйство", okved: "Выращивание зерновых культур", code: "01.11" },
            { key: "services", label: "Услуги для бизнеса", okved: "Консультирование по вопросам коммерческой деятельности и управления", code: "70.22" },
            { key: "energy", label: "Энергетика", okved: "Производство электроэнергии", code: "35.11" },
            { key: "medicine", label: "Медицина и фармацевтика", okved: "Общая врачебная практика", code: "86.21" },
            { key: "other", label: "Другая сфера", okved: "Консультирование по вопросам коммерческой деятельности и управления", code: "70.22" },
        ],
        regions: ["Москва", "Московская область", "Санкт-Петербург", "Ленинградская область", "Свердловская область", "Новосибирская область", "Республика Татарстан", "Краснодарский край", "Нижегородская область", "Самарская область", "Челябинская область", "Ростовская область", "Республика Башкортостан", "Пермский край", "Воронежская область", "Тюменская область", "Красноярский край", "Курганская область", "Иркутская область", "Приморский край", "Другая область"],
        revenue_options: [
            { key: "small", label: "До 300 млн ₽", amount: 200000000, scale: "Малый бизнес" },
            { key: "medium", label: "300 млн – 1 млрд ₽", amount: 700000000, scale: "Средний бизнес" },
            { key: "medium_plus", label: "1–5 млрд ₽", amount: 3000000000, scale: "Средний бизнес" },
            { key: "large", label: "5–15 млрд ₽", amount: 10000000000, scale: "Крупный бизнес" },
            { key: "xlarge", label: "15+ млрд ₽", amount: 25000000000, scale: "Крупный бизнес" },
        ],
        employees: ["до 15", "16-100", "101-250", "251-1000", "1000+"],
        company_age: ["до 3 лет", "3-5", "5-10", "10-16", "16-25", "25+"],
        growth_stages: ["Начальный этап", "Растущий бизнес", "Зрелый бизнес", "Бизнес в новой реальности"],
        products: [
            { key: "rko", label: "РКО", field: "CL_PRODUCT_RKO_MARK" },
            { key: "loans", label: "Кредиты", field: "CL_PRODUCT_LOA_MARK" },
            { key: "deposits", label: "Депозиты", field: "CL_PRODUCT_DEP_MARK" },
            { key: "guarantees", label: "Гарантии", field: "CL_PRODUCT_GAR_MARK" },
            { key: "leasing", label: "Лизинг", field: "CL_PRODUCT_LEA_MARK" },
            { key: "payroll", label: "Зарплатный проект", field: "CL_PRODUCT_ZPP_MARK" },
        ],
    };

    const state = {
        meta: null,
        metaFilled: false,
        profile: null,
        analysis: null,
        analysisError: null,
        loadingAnalysis: false,
        analysisRequest: 0,
        draft: null,
        activeView: "profile",
        feedbackRating: 5,
        feedbackCategory: "Полезно",
        riskFilter: "all",
        riskCategory: "",
        riskSort: "relevance",
        audit: null,
        guideStep: 0,
        guideOpen: true,
        chat: {
            alfa: [],
            news: [],
        },
        typing: { alfa: false, news: false },
    };

    let toastTimer = null;

    // -----------------------------------------------------------------
    // Утилиты
    // -----------------------------------------------------------------

    function esc(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function truncate(value, limit = 260) {
        const text = String(value ?? "").replace(/\s+/g, " ").trim();
        if (text.length <= limit) return text;
        return `${text.slice(0, limit).replace(/\s+\S*$/, "")}…`;
    }

    function withoutTitle(summary, title) {
        let text = String(summary ?? "").replace(/\s+/g, " ").trim();
        const cleanTitle = String(title ?? "").replace(/\s+/g, " ").trim();
        if (cleanTitle && text.startsWith(cleanTitle)) {
            text = text.slice(cleanTitle.length).replace(/^[\s—–:;,.|/\\-]+/, "").trim();
        }
        return text;
    }

    function bestSummary(primary, fallback, title) {
        const candidates = [primary, fallback]
            .map((value) => withoutTitle(value, title))
            .filter(Boolean);
        return candidates.sort((left, right) => right.length - left.length)[0] || "";
    }

    function shortDate(value) {
        if (!value) return "";
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) return String(value);
        return parsed.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
    }

    function shortTime(value) {
        if (!value) return "";
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) return "";
        return parsed.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
    }

    function categoryLabel(value) {
        return CATEGORY_LABELS[value] || value || "Аналитика";
    }

    function plural(number, one, few, many) {
        const value = Math.abs(Number(number)) % 100;
        if (value >= 11 && value <= 14) return many;
        const last = value % 10;
        if (last === 1) return one;
        if (last >= 2 && last <= 4) return few;
        return many;
    }

    function safeUrl(value) {
        return /^https?:\/\//i.test(String(value || "")) ? esc(value) : "";
    }

    function setText(id, value) {
        const element = document.getElementById(id);
        if (element) element.textContent = value ?? "";
    }

    function toast(message, type = "") {
        const element = $("#toast");
        if (!element) return;
        element.textContent = message;
        element.className = `toast show ${type}`.trim();
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => {
            element.className = `toast ${type}`.trim();
        }, 4600);
    }

    function setButtonLoading(button, loading, label = "Загрузка…") {
        if (!button) return;
        if (loading) {
            if (!button.dataset.originalText) {
                button.dataset.originalText = button.textContent;
            }
            button.textContent = label;
            button.disabled = true;
        } else {
            if (button.dataset.originalText) {
                button.textContent = button.dataset.originalText;
            }
            button.disabled = false;
        }
    }

    async function api(path, options = {}) {
        const config = {
            headers: { "Content-Type": "application/json" },
            ...options,
        };
        if (config.body !== undefined && config.body !== null && typeof config.body !== "string") {
            config.body = JSON.stringify(config.body);
        }
        const response = await fetch(path, config);
        let data = {};
        try {
            data = await response.json();
        } catch {
            data = {};
        }
        if (!response.ok) {
            let detail = data.detail;
            if (Array.isArray(detail)) {
                detail = detail.map((item) => item.msg || "Некорректное поле").join(", ");
            }
            throw new Error(detail || "Не удалось выполнить запрос");
        }
        return data;
    }

    function saveProfile(profile) {
        state.profile = profile;
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
        } catch {
            // localStorage may be disabled — профиль продолжает работать в памяти
        }
    }

    function loadSavedProfile() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return null;
            const parsed = JSON.parse(raw);
            return parsed && parsed.client_id ? parsed : null;
        } catch {
            return null;
        }
    }

    function resetChat() {
        state.chat = {
            alfa: [{
                role: "agent",
                welcome: true,
                text: "Здравствуйте! Я Альфа-агент. Отвечаю только по аналитике и продуктам Альфа-Банка. Спросите про ставку, инфляцию, лизинг или риски — и я покажу, на чём основан вывод.",
            }],
            news: [{
                role: "agent",
                welcome: true,
                text: "Здравствуйте! Я новостной агент. Отвечаю только по внешним новостям и их влиянию на ваш бизнес. Если по теме нет свежей новости, честно скажу об этом и предложу перейти к Альфа-агенту.",
            }],
        };
        state.typing = { alfa: false, news: false };
    }

    // -----------------------------------------------------------------
    // Роутинг
    // -----------------------------------------------------------------

    function guideStepForView(view) {
        const index = GUIDE_STEPS.findIndex((step) => step.view === view);
        return index >= 0 ? index : state.guideStep;
    }

    function renderGuide() {
        const card = $("#guide-card");
        const pill = $("#guide-toggle");
        const text = $("#guide-text");
        const steps = $("#guide-steps");
        const next = $("#guide-next");
        if (!card || !pill || !text || !steps) return;

        const step = GUIDE_STEPS[state.guideStep] || GUIDE_STEPS[0];
        const visible = Boolean(state.profile) && state.guideOpen;
        card.classList.toggle("hidden", !visible);
        pill.classList.toggle("hidden", visible || !state.profile);

        text.textContent = step.text;
        steps.innerHTML = GUIDE_STEPS.map((item, index) => (
            `<button class="guide-step ${index === state.guideStep ? "active" : ""} ${index < state.guideStep ? "done" : ""}" type="button" data-guide-step="${index}">${index + 1}. ${esc(item.label)}</button>`
        )).join("");
        if (next) {
            next.textContent = state.guideStep >= GUIDE_STEPS.length - 1
                ? "Начать сначала"
                : `${step.action} →`;
        }
    }

    function openGuide(stepIndex = null) {
        if (stepIndex !== null) state.guideStep = Math.max(0, Math.min(GUIDE_STEPS.length - 1, stepIndex));
        state.guideOpen = true;
        renderGuide();
    }

    function nextGuideStep() {
        state.guideStep = state.guideStep >= GUIDE_STEPS.length - 1 ? 0 : state.guideStep + 1;
        state.guideOpen = true;
        showApp(GUIDE_STEPS[state.guideStep].view);
        renderGuide();
    }

    function showAuth(route) {
        if (route === "register-2" && !state.draft) route = "register";
        if (!["landing", "login", "register", "register-2"].includes(route)) route = "landing";

        $$(".screen").forEach((screen) => screen.classList.remove("active"));
        const screen = document.getElementById(`screen-${route}`);
        if (screen) screen.classList.add("active");
        const appScreen = document.getElementById("screen-app");
        if (appScreen) appScreen.dataset.appView = "";
        state.activeView = null;
        history.replaceState(null, "", `#/${route}`);
        window.scrollTo(0, 0);
    }

    function showApp(view) {
        if (!state.profile || !state.profile.client_id) {
            showAuth("login");
            return;
        }
        if (!["profile", "risks", "alfa", "news", "trace", "faq", "feedback"].includes(view)) {
            view = "profile";
        }

        $$(".screen").forEach((screen) => screen.classList.remove("active"));
        const appScreen = $("#screen-app");
        appScreen.classList.add("active");
        appScreen.dataset.appView = view;

        $$(".view").forEach((element) => element.classList.remove("active"));
        const viewElement = document.getElementById(`view-${view}`);
        if (viewElement) viewElement.classList.add("active");

        $$("#side-nav .nav-item").forEach((item) => {
            item.classList.toggle("active", item.dataset.view === view);
        });

        state.activeView = view;
        const stepIndex = GUIDE_STEPS.findIndex((step) => step.view === view);
        if (stepIndex >= 0) state.guideStep = stepIndex;
        renderGuide();
        history.replaceState(null, "", `#/${view}`);
        window.scrollTo(0, 0);

        if (view === "profile") renderProfile();
        if (view === "risks") renderRisks();
        if (view === "trace") {
            renderTrace();
            loadAudit(true);
        }
        if (view === "alfa" || view === "news") renderChat(view);
    }

    // -----------------------------------------------------------------
    // Справочники и формы
    // -----------------------------------------------------------------

    function fillSelect(select, items, options = {}) {
        if (!select) return;
        const {
            valueKey = "key",
            labelKey = "label",
            placeholder = "",
        } = options;
        const first = placeholder ? `<option value="">${esc(placeholder)}</option>` : "";
        select.innerHTML = first + items.map((item) => {
            const value = typeof item === "string" ? item : item[valueKey];
            const label = typeof item === "string" ? item : item[labelKey];
            return `<option value="${esc(value)}">${esc(label)}</option>`;
        }).join("");
    }

    function renderProductChips(container) {
        if (!container || !state.meta) return;
        container.innerHTML = state.meta.products.map((product) => (
            `<label class="check-chip">` +
            `<input type="checkbox" name="product" value="${esc(product.key)}">` +
            `<span>${esc(product.label)}</span>` +
            `</label>`
        )).join("");
    }

    function fillMeta() {
        if (state.metaFilled || !state.meta) return;
        state.metaFilled = true;

        fillSelect($("#reg-industry"), state.meta.industries, { placeholder: "Выберите сферу" });
        fillSelect($("#edit-industry"), state.meta.industries, { placeholder: "Выберите сферу" });
        fillSelect($("#reg-region"), state.meta.regions, { placeholder: "Выберите регион" });
        fillSelect($("#edit-region"), state.meta.regions, { placeholder: "Выберите регион" });
        fillSelect($("#reg-scale"), state.meta.revenue_options, { placeholder: "Выберите масштаб" });
        fillSelect($("#edit-scale"), state.meta.revenue_options, { placeholder: "Выберите масштаб" });
        fillSelect($("#reg-employees"), state.meta.employees, { placeholder: "Не указано" });
        fillSelect($("#edit-employees"), state.meta.employees, { placeholder: "Не указано" });
        fillSelect($("#reg-age"), state.meta.company_age, { placeholder: "Не указано" });
        fillSelect($("#edit-age"), state.meta.company_age, { placeholder: "Не указано" });
        fillSelect($("#reg-stage"), state.meta.growth_stages, { placeholder: "Не указано" });
        fillSelect($("#edit-stage"), state.meta.growth_stages, { placeholder: "Не указано" });

        renderProductChips($("#reg-products"));
        renderProductChips($("#edit-products"));

        const defaults = [
            ["#reg-region", "Москва"],
            ["#reg-scale", "medium"],
            ["#reg-employees", "16-100"],
            ["#reg-age", "5-10"],
            ["#reg-stage", "Растущий бизнес"],
        ];
        defaults.forEach(([selector, value]) => {
            const element = $(selector);
            if (!element) return;
            if (Array.from(element.options).some((option) => option.value === value)) {
                element.value = value;
            }
        });

        const rko = $("#reg-products input[value='rko']");
        if (rko) rko.checked = true;
    }

    async function loadMeta() {
        try {
            state.meta = await api("/api/meta");
        } catch (error) {
            console.warn("Не удалось загрузить справочники, используется локальный набор", error);
            state.meta = FALLBACK_META;
        }
        fillMeta();
    }

    function ensureOption(select, value) {
        if (!select || !value) return;
        if (!Array.from(select.options).some((option) => option.value === value)) {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = value;
            select.appendChild(option);
        }
    }

    function findIndustryKey(label, okved) {
        if (!state.meta) return "other";
        const found = state.meta.industries.find((item) => (
            item.label === label || (okved && item.okved === okved)
        ));
        return found ? found.key : "other";
    }

    function pickScaleKey(profile) {
        const revenue = Number(profile?.revenue || 0);
        if (Number.isFinite(revenue) && revenue > 0) {
            if (revenue >= 15_000_000_000) return "xlarge";
            if (revenue >= 5_000_000_000) return "large";
            if (revenue >= 1_000_000_000) return "medium_plus";
            if (revenue >= 300_000_000) return "medium";
            return "small";
        }
        if (profile?.scale === "Крупный бизнес") return "large";
        if (profile?.scale === "Средний бизнес") return "medium";
        return "small";
    }

    function getFormField(form, name) {
        return form.querySelector(`[name="${name}"]`);
    }

    // -----------------------------------------------------------------
    // Профиль и анализ
    // -----------------------------------------------------------------

    function renderProfile() {
        const profile = state.profile;
        if (!profile) return;

        setText("profile-company", profile.legal_entity || "Профиль компании");
        setText("profile-meta", [profile.okved, profile.okved_code ? `ОКВЭД ${profile.okved_code}` : ""].filter(Boolean).join(" · ") || "—");
        setText("profile-industry", profile.industry || "—");
        setText("profile-region", profile.region || "—");
        const scaleLabel = [profile.scale, profile.revenue_label && profile.revenue_label !== "—" ? profile.revenue_label : ""]
            .filter(Boolean)
            .join(" · ");
        setText("profile-scale", scaleLabel || "—");
        setText("profile-employees", profile.employees && profile.employees !== "—" ? `${profile.employees} чел.` : "—");
        setText("profile-age", profile.company_age && profile.company_age !== "—" ? `${profile.company_age} лет` : "—");
        setText("profile-stage", profile.growth_stage || "—");

        const source = $("#profile-source");
        if (source) source.textContent = profile.is_custom ? "Профиль пользователя" : "Внутренняя база";

        const products = $("#profile-products");
        if (products) {
            products.innerHTML = (profile.products && profile.products.length)
                ? profile.products.map((product) => `<span class="tag red">${esc(product)}</span>`).join("")
                : `<span class="tag">Не указаны</span>`;
        }

        const extra = $("#profile-extra-tags");
        if (extra) {
            const tags = [];
            tags.push(profile.has_fts ? `ВЭД: ${profile.fts_country || "да"}` : "Без ВЭД");
            if (profile.has_factoring) tags.push("Факторинг");
            if (profile.city) tags.push(profile.city);
            extra.innerHTML = tags.map((tag) => `<span class="tag">${esc(tag)}</span>`).join("");
        }

        const sidebarUser = $("#sidebar-user");
        if (sidebarUser) {
            sidebarUser.innerHTML =
                `<strong>${esc(profile.legal_entity || "Профиль компании")}</strong>` +
                `<span>${esc(profile.industry || "Отрасль не указана")}</span>`;
        }

        renderAnalysis();
    }

    function renderPreview() {
        const newsCard = $("#preview-news");
        const analyticsCard = $("#preview-analytics");
        if (!newsCard || !analyticsCard) return;

        const newsTitle = newsCard.querySelector("h3");
        const newsText = newsCard.querySelector("p");
        const newsFooter = newsCard.querySelector(".preview-footer span:first-child");

        const analyticsTitle = analyticsCard.querySelector("h3");
        const analyticsText = analyticsCard.querySelector("p");
        const analyticsFooter = analyticsCard.querySelector(".preview-footer span:first-child");

        const analysis = state.analysis;
        if (!analysis) {
            const loading = state.loadingAnalysis;
            const error = state.analysisError;
            newsCard.classList.toggle("is-empty", !loading);
            analyticsCard.classList.toggle("is-empty", !loading);
            newsTitle.textContent = loading ? "Анализируем новости…" : (error ? "Не удалось загрузить" : "Анализ ещё не запускался");
            newsText.textContent = loading
                ? "Собираем свежие RSS-новости и отбираем важное для вашей компании."
                : (error || "Нажмите «Обновить анализ», чтобы собрать новости и аналитику.");
            analyticsTitle.textContent = loading ? "Анализируем рынок…" : (error ? "Повторите попытку" : "Аналитика появится здесь");
            analyticsText.textContent = loading
                ? "Сверяем события с профилем компании и материалами Альфа-Банка."
                : "Агент покажет, как макроэкономика и рынки влияют на ваш бизнес.";
            newsFooter.textContent = loading ? "Собираем источники" : "Первоисточник";
            analyticsFooter.textContent = "Материалы Альфа-Банка";
            return;
        }

        newsCard.classList.remove("is-empty");
        analyticsCard.classList.remove("is-empty");

        const firstInterpretation = (analysis.interpretations || [])[0];
        const firstNews = (analysis.ranked_news || [])[0] || (analysis.news_items || [])[0];
        const newsSource = [firstInterpretation?.news_source || firstNews?.source, shortDate(firstInterpretation?.news_date || firstNews?.date)]
            .filter(Boolean)
            .join(" · ");

        if (firstInterpretation || firstNews) {
            const previewTitle = firstInterpretation?.news_title || firstNews?.title || "Главная новость";
            const previewSummary =
                firstInterpretation?.interpretation?.what_happened ||
                firstInterpretation?.interpretation?.why_important ||
                firstNews?.relevance_reasoning ||
                "Свежая новость, связанная с вашим бизнесом.";
            newsTitle.textContent = previewTitle;
            newsText.textContent = truncate(withoutTitle(previewSummary, previewTitle), 190) || "Свежая новость, связанная с вашим бизнесом.";
            newsFooter.textContent = newsSource || "Первоисточник";
        } else {
            newsCard.classList.add("is-empty");
            newsTitle.textContent = "Подходящих новостей пока нет";
            newsText.textContent = "Попробуйте обновить анализ позже.";
            newsFooter.textContent = "Первоисточник";
        }

        const firstInsight = (analysis.analytics_insights || [])[0];
        const firstAnalytics = (analysis.alfa_analytics || [])[0];
        if (firstInsight || firstAnalytics) {
            const analyticsHeading = firstInsight?.title || firstAnalytics?.title || "Аналитическая сводка";
            const analyticsSummary =
                firstInsight?.summary ||
                firstInsight?.interpretation?.what_happened ||
                firstAnalytics?.summary ||
                "Аналитическая сводка Альфа-Банка.";
            analyticsTitle.textContent = analyticsHeading;
            analyticsText.textContent = truncate(withoutTitle(analyticsSummary, analyticsHeading), 190) || "Аналитическая сводка Альфа-Банка.";
            analyticsFooter.textContent = firstInsight?.source_file
                ? `Альфа-Банк · ${truncate(firstInsight.source_file, 40)}`
                : "Материалы Альфа-Банка";
        } else {
            analyticsCard.classList.add("is-empty");
            analyticsTitle.textContent = "Нет аналитических материалов";
            analyticsText.textContent = "База Альфа-Банка временно недоступна.";
            analyticsFooter.textContent = "Материалы Альфа-Банка";
        }
    }

    function renderMetrics() {
        const metrics = $$("#metrics-row .metric strong");
        if (!metrics.length) return;

        if (!state.analysis) {
            metrics.forEach((metric) => { metric.textContent = "—"; });
            return;
        }

        const interpretations = state.analysis.interpretations || [];
        const insights = state.analysis.analytics_insights || [];
        const risksAndOpportunities = [...interpretations, ...insights].reduce((total, item) => {
            const interpretation = item.interpretation || {};
            return total + (interpretation.risks?.length || 0) + (interpretation.opportunities?.length || 0);
        }, 0);

        const values = [
            (state.analysis.news_items || []).length,
            interpretations.length,
            risksAndOpportunities,
            (state.analysis.trace || []).length,
        ];
        metrics.forEach((metric, index) => {
            metric.textContent = values[index] ?? "—";
        });
    }

    function renderAnalysisStatus() {
        const element = $("#analysis-status");
        if (!element) return;
        if (state.loadingAnalysis) {
            element.textContent = "Анализируем новости и аналитику…";
            return;
        }
        if (state.analysisError) {
            element.textContent = "Не удалось загрузить анализ";
            return;
        }
        if (state.analysis) {
            const newsCount = (state.analysis.news_items || []).length;
            const interpretationCount = (state.analysis.interpretations || []).length;
            element.textContent =
                `Обновлено в ${shortTime(state.analysis.loadedAt)} · ` +
                `${newsCount} ${plural(newsCount, "новость", "новости", "новостей")} · ` +
                `${interpretationCount} ${plural(interpretationCount, "событие", "события", "событий")}`;
            return;
        }
        element.textContent = "Анализ ещё не запускался";
    }

    function renderAnalysis() {
        renderPreview();
        renderMetrics();
        renderAnalysisStatus();
    }

    async function loadAnalysis(force = false) {
        if (!state.profile || !state.profile.client_id) return;
        if (state.loadingAnalysis) return;
        if (!force && state.analysis) return;

        const refreshButton = $("#refresh-analysis");
        const risksButton = $("#risks-refresh");
        const requestId = ++state.analysisRequest;

        state.loadingAnalysis = true;
        state.analysisError = null;
        setButtonLoading(refreshButton, true, "Анализируем…");
        setButtonLoading(risksButton, true, "Анализируем…");
        renderAnalysis();
        if (state.activeView === "risks") renderRisks();

        try {
            const data = await api("/api/analyze", {
                method: "POST",
                body: { client_id: state.profile.client_id },
            });
            if (requestId !== state.analysisRequest) return;

            if (data.profile_display) {
                saveProfile({ ...state.profile, ...data.profile_display });
            }
            data.loadedAt = new Date().toISOString();
            state.analysis = data;
            state.analysisError = null;

            if (state.activeView === "profile") renderProfile();
            else renderAnalysis();
            if (state.activeView === "risks") renderRisks();
            if (state.activeView === "trace") renderTrace();
            if (force) toast("Анализ обновлён", "success");
        } catch (error) {
            if (requestId !== state.analysisRequest) return;
            state.analysisError = error.message || "Ошибка анализа";
            renderAnalysis();
            if (state.activeView === "risks") renderRisks();
            toast(state.analysisError, "error");
        } finally {
            if (requestId === state.analysisRequest) {
                state.loadingAnalysis = false;
                setButtonLoading(refreshButton, false);
                setButtonLoading(risksButton, false);
                renderAnalysis();
                if (state.activeView === "risks") renderRisks();
            }
        }
    }

    // -----------------------------------------------------------------
    // Риски и возможности
    // -----------------------------------------------------------------

    function nonEmpty(value, fallback) {
        return Array.isArray(value) && value.length ? value : fallback;
    }

    function listHtml(items, className = "") {
        const safeItems = (items || []).filter(Boolean);
        if (!safeItems.length) {
            return `<ul class="${className}"><li>Нет данных</li></ul>`;
        }
        return `<ul class="${className}">${safeItems.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>`;
    }

    function newsInsight(item) {
        const interpretation = item.interpretation || {};
        const foundNews = (state.analysis?.news_items || []).find((news) => news.id === item.news_id);
        const title = item.news_title || foundNews?.title || "Новость";
        return {
            kind: "news",
            title,
            summary: bestSummary(interpretation.what_happened, foundNews?.excerpt || foundNews?.content, title) || interpretation.why_important || "",
            source: item.news_source || foundNews?.source || "",
            date: item.news_date || foundNews?.date || "",
            url: item.news_url || foundNews?.url || "",
            category: item.news_category || foundNews?.category || "",
            relevance: Number(item.relevance_score || 0),
            bankView: interpretation.bank_view || "",
            aiSummary: interpretation.consequences || interpretation.why_important || "",
            relatedAnalytics: item.related_analytics || [],
            verification: item.verification || null,
            risks: nonEmpty(interpretation.risks, [interpretation.why_important, interpretation.consequences].filter(Boolean)),
            riskActions: nonEmpty(interpretation.risk_actions, interpretation.actions ? [interpretation.actions] : []),
            opportunities: nonEmpty(interpretation.opportunities, [
                "Изменения открывают новые ниши и партнёрства.",
                "Можно пересмотреть продуктовую линейку и условия работы с клиентами.",
            ]),
            opportunityActions: nonEmpty(interpretation.opportunity_actions, [
                "Провести сценарный анализ для ключевых клиентов.",
                "Зафиксировать ценовые и закупочные триггеры в договорах.",
            ]),
        };
    }

    function analyticsInsight(item) {
        const interpretation = item.interpretation || {};
        const title = item.title || "Аналитическая сводка";
        return {
            kind: "alfa",
            title,
            summary: bestSummary(interpretation.what_happened, item.summary, title),
            source: item.source_file ? `Альфа-Банк · ${item.source_file}` : "Материалы Альфа-Банка",
            date: item.date || "",
            url: "",
            category: item.category || "",
            relevance: 10,
            bankView: item.bank_view || interpretation.bank_view || "",
            aiSummary: interpretation.consequences || interpretation.why_important || "",
            relatedAnalytics: [],
            verification: item.verification || null,
            risks: nonEmpty(interpretation.risks, [interpretation.why_important, interpretation.consequences].filter(Boolean)),
            riskActions: nonEmpty(interpretation.risk_actions, interpretation.actions ? [interpretation.actions] : []),
            opportunities: nonEmpty(interpretation.opportunities, [
                "Аналитика помогает точнее спланировать бюджет и продукты.",
                "Можно использовать прогноз для переговоров с клиентами.",
            ]),
            opportunityActions: nonEmpty(interpretation.opportunity_actions, [
                "Провести сценарный анализ.",
                "Зафиксировать условия финансирования на горизонте квартала.",
            ]),
        };
    }

    function analyticsLinksHtml(items) {
        if (!Array.isArray(items) || !items.length) return "";
        const links = items.slice(0, 3).map((item) => {
            const title = item.title || "Аналитический материал";
            const file = item.source_file ? ` · ${item.source_file}` : "";
            return `<span class="risk-analytics-link">«${esc(title)}»${esc(file)}</span>`;
        }).join("");
        return `<div class="risk-analytics-links"><span>Связанная аналитика банка</span>${links}</div>`;
    }

    function verificationHtml(verification) {
        if (!verification) return "";
        const status = verification.status || "needs_review";
        const labels = {
            verified: "Самопроверка пройдена",
            needs_improvement: "Нужна доработка",
            insufficient: "Недостаточно данных",
            error: "Ошибка проверки",
        };
        return `<span class="verification-chip ${esc(status)}">${esc(labels[status] || "Проверено AI")}</span>`;
    }

    function riskCard(insight) {
        const isNews = insight.kind === "news";
        const typeLabel = isNews ? "Новость · внешний источник" : "Аналитика Альфа-Банка";
        const sourceLabel = [insight.source, shortDate(insight.date)].filter(Boolean).join(" · ");
        const url = safeUrl(insight.url);
        const sourceFooter = url
            ? `<a href="${url}" target="_blank" rel="noopener noreferrer">Перейти к первоисточнику →</a>`
            : `<span class="risk-source">${esc(insight.source || "Материалы Альфа-Банка")}</span>`;
        const question = `Что это значит для моего бизнеса: «${insight.title}»?`;
        const factBlock = isNews
            ? `<div class="risk-fact">
                    <div class="risk-block-label">Что произошло <span class="source-badge">факт из новости</span></div>
                    <p>${esc(truncate(insight.summary, 620))}</p>
               </div>`
            : "";
        const bankText = isNews
            ? (insight.bankView || "Отдельного материала Альфа-Банка по этому событию в базе нет.")
            : (insight.summary || insight.bankView || "Аналитический материал Альфа-Банка.");
        const aiText = insight.aiSummary
            || "AI оценил возможные последствия для компании на основе профиля и источника.";

        return `
            <article class="risk-card" data-kind="${isNews ? "news" : "alfa"}" data-category="${esc(insight.category || "")}" data-date="${esc(insight.date || "")}">
                <div class="risk-card-head">
                    <div class="risk-head-left">
                        <span class="risk-type ${isNews ? "news" : "alfa"}">${typeLabel}</span>
                        <span class="risk-category">${esc(categoryLabel(insight.category))}</span>
                    </div>
                    <span class="risk-source">${esc(sourceLabel || "Источник")}</span>
                </div>
                <h2>${esc(insight.title)}</h2>
                ${factBlock}
                <div class="risk-bank-view">
                    <div class="risk-block-label">Позиция Альфа-Банка <span class="source-badge">экспертный материал</span></div>
                    <p>${esc(truncate(bankText, 640))}</p>
                    ${isNews ? analyticsLinksHtml(insight.relatedAnalytics) : ""}
                </div>
                <div class="risk-ai-block">
                    <div class="risk-block-label">AI-разбор для вашей компании <span class="ai-badge">сформировано AI</span></div>
                    <p class="risk-ai-summary">${esc(truncate(aiText, 520))}</p>
                    <div class="risk-columns">
                        <div class="risk-col risk-col-risk">
                            <div class="col-head"><span class="col-dot risk"></span>Риски</div>
                            ${listHtml(insight.risks)}
                            <div class="col-subhead">Что можно сделать</div>
                            ${listHtml(insight.riskActions, "actions")}
                        </div>
                        <div class="risk-col risk-col-op">
                            <div class="col-head"><span class="col-dot op"></span>Возможности</div>
                            ${listHtml(insight.opportunities)}
                            <div class="col-subhead">Как адаптировать</div>
                            ${listHtml(insight.opportunityActions, "actions")}
                        </div>
                    </div>
                </div>
                <div class="risk-card-foot">
                    <div class="risk-foot-left">
                        ${sourceFooter}
                        ${verificationHtml(insight.verification)}
                    </div>
                    <div>
                        <button class="btn btn-ghost small" type="button" data-ask-alfa="${esc(question)}">Спросить Альфа-агента</button>
                        <button class="btn btn-ghost small" type="button" data-ask-news="${esc(question)}">Спросить новостного агента</button>
                    </div>
                </div>
            </article>
        `;
    }

    function allRiskInsights() {
        if (!state.analysis) return [];
        const news = (state.analysis.interpretations || []).map(newsInsight);
        const analytics = (state.analysis.analytics_insights || []).map(analyticsInsight);
        return [...news, ...analytics];
    }

    function renderRisks() {
        const container = $("#risks-list");
        if (!container) return;

        if (!state.analysis) {
            const message = state.loadingAnalysis
                ? "Анализ собирается: новости, профиль и материалы Альфа-Банка."
                : (state.analysisError || "Нажмите «Обновить анализ», чтобы собрать риски и возможности.");
            container.innerHTML = `<div class="empty-state"><strong>Пока нет данных</strong><p>${esc(message)}</p></div>`;
            return;
        }

        const all = allRiskInsights();
        const categories = Array.from(new Set(all.map((item) => item.category).filter(Boolean))).sort();
        const categorySelect = $("#risk-category-filter");
        if (categorySelect) {
            const current = state.riskCategory;
            categorySelect.innerHTML = `<option value="">Все темы</option>` + categories.map((category) => (
                `<option value="${esc(category)}">${esc(categoryLabel(category))}</option>`
            )).join("");
            categorySelect.value = categories.includes(current) ? current : "";
            state.riskCategory = categorySelect.value;
        }

        let filtered = all.filter((item) => {
            if (state.riskFilter !== "all" && item.kind !== state.riskFilter) return false;
            if (state.riskCategory && item.category !== state.riskCategory) return false;
            return true;
        });

        filtered.sort((left, right) => {
            if (state.riskSort === "date") {
                const leftDate = Date.parse(left.date) || 0;
                const rightDate = Date.parse(right.date) || 0;
                return rightDate - leftDate;
            }
            return (right.relevance || 0) - (left.relevance || 0);
        });

        const count = $("#risk-count");
        if (count) {
            count.textContent = `${filtered.length} из ${all.length} ${plural(all.length, "события", "событий", "событий")}`;
        }

        const verification = $("#risk-verification");
        if (verification) {
            const checked = all.filter((item) => item.verification).length;
            const passed = all.filter((item) => item.verification?.status === "verified").length;
            const summary = state.analysis.verification_summary || {};
            const checkedCount = summary.checked || checked;
            const passedCount = summary.verified ?? passed;
            verification.innerHTML = checkedCount
                ? `<span class="self-check-badge">Самопроверка: ${passedCount}/${checkedCount} карточек прошли проверку</span>
                   <span class="self-check-note">Проверяются полнота, источники и использование профиля компании.</span>`
                : `<span class="self-check-note">Самопроверка появится после генерации карточек.</span>`;
        }

        if (!filtered.length) {
            container.innerHTML = `<div class="empty-state"><strong>В этом разрезе пока нет событий</strong><p>Сбросьте фильтр или обновите анализ.</p></div>`;
            return;
        }
        container.innerHTML = filtered.map(riskCard).join("");
    }

    // -----------------------------------------------------------------
    // Трассировка
    // -----------------------------------------------------------------

    const TRACE_LABELS = {
        analyze_client_profile: "Анализ профиля клиента",
        collect_and_classify_news: "Сбор и классификация новостей",
        rank_news: "Ранжирование по значимости",
        generate_interpretations: "Генерация интерпретаций",
        verify_results: "Верификация результатов",
    };

    function stringify(value) {
        try {
            return JSON.stringify(value, null, 2);
        } catch {
            return String(value);
        }
    }

    function renderTrace() {
        const summary = $("#trace-summary");
        const container = $("#trace-list");
        if (!summary || !container) return;

        if (!state.analysis) {
            summary.innerHTML = "";
            container.innerHTML = `<div class="empty-state"><strong>Трассировка появится после анализа</strong><p>Нажмите «Обновить анализ» на странице профиля.</p></div>`;
            return;
        }

        const trace = state.analysis.trace || [];
        const successCount = trace.filter((step) => step.success).length;

        const verification = state.analysis.verification_summary || {};
        const verified = verification.verified ?? 0;
        const checked = verification.checked ?? 0;
        summary.innerHTML = `
            <div class="trace-stat"><strong>${trace.length}</strong>${plural(trace.length, "шаг", "шага", "шагов")}</div>
            <div class="trace-stat"><strong>${successCount}</strong>успешно</div>
            <div class="trace-stat"><strong>${(state.analysis.news_items || []).length}</strong>${plural((state.analysis.news_items || []).length, "новость", "новости", "новостей")}</div>
            <div class="trace-stat"><strong>${(state.analysis.interpretations || []).length}</strong>${plural((state.analysis.interpretations || []).length, "интерпретация", "интерпретации", "интерпретаций")}</div>
            <div class="trace-stat"><strong>${verified}/${checked}</strong>самопроверка</div>
        `;

        if (!trace.length) {
            container.innerHTML = `<div class="empty-state"><strong>Шаги не записаны</strong><p>Оркестратор не вернул трассировку.</p></div>`;
            return;
        }

        container.innerHTML = trace.map((step, index) => {
            const label = TRACE_LABELS[step.action] || step.action || `Шаг ${step.step_number}`;
            const error = step.error_message
                ? `<div><div class="trace-block-label">Ошибка</div><pre>${esc(step.error_message)}</pre></div>`
                : "";
            return `
                <details class="trace-card" ${index === 0 ? "open" : ""}>
                    <summary>
                        <span class="trace-num">${esc(step.step_number ?? index + 1)}</span>
                        <div class="trace-title">
                            <strong>${esc(label)}</strong>
                            <span>${esc(step.action || "")}${step.timestamp ? ` · ${esc(shortTime(step.timestamp))}` : ""}</span>
                        </div>
                        <span class="trace-badge ${step.success ? "ok" : "fail"}">${step.success ? "успешно" : "ошибка"}</span>
                    </summary>
                    <div class="trace-body">
                        <div>
                            <div class="trace-block-label">Входные данные</div>
                            <pre>${esc(stringify(step.input_data))}</pre>
                        </div>
                        <div>
                            <div class="trace-block-label">Результат</div>
                            <pre>${esc(stringify(step.output_data))}</pre>
                        </div>
                        ${error}
                    </div>
                </details>
            `;
        }).join("");
    }

    function renderAudit() {
        const metrics = $("#audit-metrics");
        const feedback = $("#audit-feedback");
        const chats = $("#audit-chats");
        if (!metrics || !feedback || !chats) return;

        if (!state.audit) {
            metrics.innerHTML = `<div class="audit-loading">Загружаем метрики…</div>`;
            chats.innerHTML = "";
            feedback.innerHTML = "";
            return;
        }

        const data = state.audit;
        const rating = data.average_rating == null ? "—" : `${data.average_rating} / 5`;
        const verification = data.verification_pass_rate == null
            ? "—"
            : `${Math.round(data.verification_pass_rate * 100)}%`;
        const llmShare = data.llm_share == null ? "—" : `${Math.round(data.llm_share * 100)}%`;
        metrics.innerHTML = [
            ["Анализов", data.analyses ?? 0],
            ["Диалогов", data.chats ?? 0],
            ["Средняя оценка", rating],
            ["Самопроверка", verification],
            ["Ответы LLM", llmShare],
            ["Низких оценок", data.low_rating_count ?? 0],
        ].map(([label, value]) => (
            `<div class="audit-metric"><strong>${esc(value)}</strong><span>${esc(label)}</span></div>`
        )).join("");

        const recentChats = (data.recent_chats || []).filter((item) => item.agent);
        chats.innerHTML = recentChats.length
            ? `<div class="audit-feedback-head">Последние диалоги</div>` + recentChats.map((item) => (
                `<div class="audit-chat-item">
                    <span class="audit-chat-agent">${esc(item.agent === "alfa" ? "Альфа-агент" : "Новостной агент")}</span>
                    <span>${esc(item.mode === "llm" ? "LLM" : "fallback")}</span>
                    <span>источников: ${esc(item.sources_count ?? 0)}</span>
                    <span>${esc(item.latency_ms ?? "—")} мс</span>
                </div>`
            )).join("")
            : "";

        const recent = (data.recent_low_feedback?.length
            ? data.recent_low_feedback
            : (data.recent_feedback || []).slice(0, 3)
        ).filter((item) => String(item.category || "").toLowerCase() !== "test");
        feedback.innerHTML = recent.length
            ? `<div class="audit-feedback-head">Последние отзывы</div>` + recent.map((item) => (
                `<div class="audit-feedback-item">
                    <span class="audit-feedback-rating">${esc(item.rating ?? "—")} / 5</span>
                    <span class="audit-feedback-category">${esc(item.category || "Без категории")}</span>
                    <p>${esc(truncate(item.text || "", 220))}</p>
                </div>`
            )).join("")
            : `<div class="audit-feedback-empty">Отзывов пока нет. Оставьте первый — он появится здесь и в журнале аудита.</div>`;
    }

    async function loadAudit(force = false) {
        if (state.audit && !force) {
            renderAudit();
            return;
        }
        try {
            state.audit = await api("/api/audit/summary");
        } catch (error) {
            state.audit = {
                analyses: 0,
                chats: 0,
                feedback_count: 0,
                average_rating: null,
                low_rating_count: 0,
                verification_pass_rate: null,
                llm_share: null,
                recent_feedback: [],
                recent_low_feedback: [],
                recent_chats: [],
            };
        }
        renderAudit();
    }

    function downloadTrace() {
        if (!state.analysis) {
            toast("Сначала запустите анализ", "error");
            return;
        }
        const payload = {
            client_id: state.profile?.client_id,
            profile: state.profile,
            generated_at: new Date().toISOString(),
            trace: state.analysis.trace || [],
            news_items: state.analysis.news_items || [],
            interpretations: state.analysis.interpretations || [],
            analytics_insights: state.analysis.analytics_insights || [],
        };
        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `alfa-trace-${state.profile?.client_id || "client"}.json`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(link.href);
    }

    // -----------------------------------------------------------------
    // Чаты
    // -----------------------------------------------------------------

    const GUIDE_STEPS = [
        {
            view: "profile",
            label: "Профиль",
            text: "Сначала проверьте профиль: от отрасли, региона и продуктов зависит, какие события попадут в фокус.",
            action: "Проверить профиль",
        },
        {
            view: "risks",
            label: "Риски",
            text: "Главный экран: здесь факты и позиция Альфа-Банка отделены от AI-разбора. Можно отфильтровать новости и аналитику.",
            action: "Показать риски",
        },
        {
            view: "alfa",
            label: "Альфа-агент",
            text: "Я привёл вас к Альфа-агенту. Спросите про ставку, инфляцию или лизинг — он отвечает только по аналитике банка.",
            action: "Спросить агента",
        },
        {
            view: "news",
            label: "Новости",
            text: "А здесь только внешние новости. Сравните: факт из RSS, позиция банка и AI-вывод не смешиваются.",
            action: "Открыть новости",
        },
        {
            view: "trace",
            label: "Трассировка",
            text: "Если нужна проверка — откройте трассировку и аудит: источники, шаги агентов и обратная связь.",
            action: "Проверить источники",
        },
        {
            view: "feedback",
            label: "Отзыв",
            text: "Последний шаг — оценка. Низкие оценки попадают в аудит качества, чтобы мы улучшали ответы.",
            action: "Оценить сервис",
        },
    ];

    const SUGGESTIONS = {
        alfa: [
            "Что будет со ставкой?",
            "Какие риски вы видите?",
            "Что говорят аналитики о кредитовании?",
            "Как это влияет на лизинг?",
        ],
        news: [
            "Что нового в моей отрасли?",
            "Какие события важны для моего бизнеса?",
            "Что происходит с потребительским спросом?",
            "Есть ли новости про мой регион?",
        ],
    };

    function renderSuggestions(agent) {
        const container = $(`#suggestions-${agent}`);
        if (!container) return;
        container.innerHTML = SUGGESTIONS[agent].map((question) => (
            `<button class="suggestion" type="button" data-suggestion="${esc(question)}" data-agent="${agent}">${esc(question)}</button>`
        )).join("");
    }

    function sourcesHtml(sources) {
        if (!Array.isArray(sources) || !sources.length) return "";
        const items = sources.slice(0, 4).map((source) => {
            const url = safeUrl(source.url);
            const label = esc([source.type, source.title].filter(Boolean).join(": "));
            return url
                ? `<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`
                : `<em>${label}</em>`;
        }).join("");
        return `<div class="bubble-sources"><span>Источники</span>${items}</div>`;
    }

    function renderChat(agent) {
        const container = $(`#chat-${agent}`);
        if (!container) return;

        const messages = state.chat[agent] || [];
        const followUps = agent === "alfa"
            ? ["А что это значит для меня?", "Какие риски вы видите?", "Покажи источник"]
            : ["Что нового в моей отрасли?", "Какие события важны для меня?", "Есть ли новости про мой регион?"];
        container.innerHTML = messages.map((message, index) => {
            if (message.role === "user") {
                return `<div class="bubble user">${esc(message.text)}</div>`;
            }
            if (message.welcome) {
                return `<div class="bubble agent welcome">${esc(message.text)}</div>`;
            }
            const mode = message.mode === "llm" ? "AI · LLM" : "AI · локальная сборка";
            const modeClass = message.mode === "llm" ? "llm" : "fallback";
            const suggestion = message.suggestedAgent
                ? `<button class="bubble-action" type="button" data-suggestion-agent="${esc(message.suggestedAgent)}" data-suggestion-question="${esc(message.suggestedQuestion || "")}">Перейти к Альфа-агенту →</button>`
                : "";
            const check = message.selfCheck
                ? `<div class="bubble-check">Самопроверка: ${message.selfCheck.passed}/${message.selfCheck.total} проверок пройдено</div>`
                : "";
            const follow = index === messages.length - 1
                ? `<div class="bubble-followups">${followUps.map((question) => (
                    `<button type="button" data-suggestion="${esc(question)}" data-agent="${esc(agent)}">${esc(question)}</button>`
                )).join("")}</div>`
                : "";
            return `<div class="bubble agent">
                <div class="bubble-meta"><span class="mode-badge ${modeClass}">${mode}</span><span>ответ сформирован AI</span></div>
                ${esc(message.text)}
                ${sourcesHtml(message.sources)}
                ${check}
                ${suggestion}
                ${follow}
            </div>`;
        }).join("");

        if (state.typing[agent]) {
            container.insertAdjacentHTML("beforeend", `<div class="bubble agent"><span class="typing"><i></i><i></i><i></i></span></div>`);
        }
        container.scrollTop = container.scrollHeight;
        renderSuggestions(agent);
    }

    async function askAgent(agent, question) {
        const text = String(question || "").trim();
        if (!text || text.length < 2 || !state.profile || state.typing[agent]) return;

        state.chat[agent].push({ role: "user", text, sources: [] });
        state.typing[agent] = true;
        renderChat(agent);

        try {
            const data = await api("/api/chat", {
                method: "POST",
                body: {
                    agent,
                    client_id: state.profile.client_id,
                    question: text,
                },
            });
            state.typing[agent] = false;
            state.chat[agent].push({
                role: "agent",
                text: data.answer || "Не удалось сформировать ответ.",
                sources: data.sources || [],
                mode: data.mode || "demo",
                suggestedAgent: data.suggested_agent || "",
                suggestedQuestion: data.suggested_question || "",
                selfCheck: data.self_check || null,
            });
        } catch (error) {
            state.typing[agent] = false;
            const message = error.message || "Не удалось получить ответ";
            state.chat[agent].push({
                role: "agent",
                text: /^(Введите|Задайте)/i.test(message)
                    ? message
                    : `Не удалось получить ответ: ${message}`,
                sources: [],
            });
            toast(message, "error");
        }
        renderChat(agent);
    }

    function prefillChat(agent, question) {
        showApp(agent);
        const input = document.querySelector(`#composer-${agent} input`);
        if (input) {
            input.value = question;
            input.focus();
        }
    }

    // -----------------------------------------------------------------
    // Редактирование профиля
    // -----------------------------------------------------------------

    function toggleRegCustom(show) {
        const wrap = $("#custom-industry-wrap");
        const input = $("#reg-custom-industry");
        if (wrap) wrap.classList.toggle("hidden", !show);
        if (input) input.required = show;
    }

    function toggleEditCustom(show) {
        const wrap = $("#edit-custom-wrap");
        const input = $("#edit-custom");
        if (wrap) wrap.classList.toggle("hidden", !show);
        if (input) input.required = show;
    }

    function openEdit() {
        if (!state.profile || !state.meta) return;
        const profile = state.profile;
        const form = $("#edit-form");
        if (!form) return;

        const legalEntity = getFormField(form, "legal_entity");
        if (legalEntity) legalEntity.value = profile.legal_entity || "";

        const industryKey = findIndustryKey(profile.industry, profile.okved);
        const industry = getFormField(form, "industry");
        if (industry) industry.value = industryKey;
        const custom = getFormField(form, "custom_industry");
        if (custom) {
            custom.value = industryKey === "other"
                ? (profile.custom_industry || profile.industry || "")
                : "";
        }
        toggleEditCustom(industryKey === "other");

        const region = getFormField(form, "region");
        if (region) {
            ensureOption(region, profile.region);
            region.value = profile.region || "";
        }

        const scale = getFormField(form, "scale");
        if (scale) scale.value = pickScaleKey(profile);

        const employees = getFormField(form, "employees");
        if (employees) {
            ensureOption(employees, profile.employees);
            employees.value = profile.employees && profile.employees !== "—" ? profile.employees : "";
        }
        const age = getFormField(form, "company_age");
        if (age) {
            ensureOption(age, profile.company_age);
            age.value = profile.company_age && profile.company_age !== "—" ? profile.company_age : "";
        }
        const stage = getFormField(form, "growth_stage");
        if (stage) {
            ensureOption(stage, profile.growth_stage);
            stage.value = profile.growth_stage && profile.growth_stage !== "—" ? profile.growth_stage : "";
        }

        $$("#edit-products input").forEach((input) => {
            const product = state.meta.products.find((item) => item.key === input.value);
            input.checked = Boolean(product && (profile.products || []).includes(product.label));
        });

        const fts = getFormField(form, "has_fts");
        const ftsCountry = getFormField(form, "fts_country");
        if (fts) fts.checked = Boolean(profile.has_fts);
        if (ftsCountry) ftsCountry.value = profile.fts_country || "";
        $("#edit-fts-wrap")?.classList.toggle("hidden", !profile.has_fts);

        const factoring = getFormField(form, "has_factoring");
        if (factoring) factoring.checked = Boolean(profile.has_factoring);

        const dialog = $("#edit-dialog");
        if (typeof dialog.showModal === "function") dialog.showModal();
        else dialog.setAttribute("open", "");
    }

    function closeEdit() {
        const dialog = $("#edit-dialog");
        if (!dialog) return;
        if (typeof dialog.close === "function") dialog.close();
        else dialog.removeAttribute("open");
    }

    async function submitEdit(event) {
        event.preventDefault();
        const form = event.currentTarget;
        const data = new FormData(form);
        const industry = String(data.get("industry") || "");
        const custom = String(data.get("custom_industry") || "").trim();
        const legalEntity = String(data.get("legal_entity") || "").trim();
        const region = String(data.get("region") || "");

        if (legalEntity.length < 2) {
            toast("Укажите название юридического лица", "error");
            return;
        }
        if (!industry) {
            toast("Выберите отрасль", "error");
            return;
        }
        if (industry === "other" && !custom) {
            toast("Опишите свою сферу деятельности", "error");
            return;
        }
        if (!region) {
            toast("Выберите регион", "error");
            return;
        }

        const button = form.querySelector('button[type="submit"]');
        setButtonLoading(button, true, "Сохраняем…");

        try {
            const payload = {
                legal_entity: legalEntity,
                industry,
                custom_industry: industry === "other" ? custom : "",
                region,
                city: state.profile.city || "",
                scale: String(data.get("scale") || ""),
                employees: String(data.get("employees") || ""),
                company_age: String(data.get("company_age") || ""),
                growth_stage: String(data.get("growth_stage") || ""),
                products: data.getAll("product"),
                has_fts: Boolean(getFormField(form, "has_fts")?.checked),
                fts_country: String(data.get("fts_country") || ""),
                has_factoring: Boolean(getFormField(form, "has_factoring")?.checked),
            };
            const response = await api(`/api/profile/${encodeURIComponent(state.profile.client_id)}`, {
                method: "PATCH",
                body: payload,
            });
            saveProfile(response.profile);
            state.analysis = null;
            state.analysisError = null;
            state.analysisRequest += 1;
            state.loadingAnalysis = false;
            closeEdit();
            showApp("profile");
            renderProfile();
            toast("Профиль обновлён. Пересобираем анализ…", "success");
            loadAnalysis(true);
        } catch (error) {
            toast(error.message, "error");
        } finally {
            setButtonLoading(button, false);
        }
    }

    // -----------------------------------------------------------------
    // Обратная связь
    // -----------------------------------------------------------------

    async function submitFeedback() {
        const textarea = $("#feedback-text");
        const text = textarea ? textarea.value.trim() : "";
        if (text.length < 2) {
            toast("Напишите пару слов об ответах агентов", "error");
            return;
        }
        const button = $("#feedback-submit");
        setButtonLoading(button, true, "Отправляем…");
        try {
            await api("/api/feedback", {
                method: "POST",
                body: {
                    client_id: state.profile?.client_id || "",
                    rating: state.feedbackRating,
                    category: state.feedbackCategory,
                    text,
                },
            });
            textarea.value = "";
            state.audit = null;
            toast("Спасибо! Отзыв отправлен.", "success");
        } catch (error) {
            toast(error.message, "error");
        } finally {
            setButtonLoading(button, false);
        }
    }

    // -----------------------------------------------------------------
    // События
    // -----------------------------------------------------------------

    function bindEvents() {
        document.addEventListener("click", (event) => {
            const routeTarget = event.target.closest("[data-route]");
            if (routeTarget) {
                event.preventDefault();
                showAuth(routeTarget.dataset.route);
                return;
            }

            const suggestion = event.target.closest("[data-suggestion]");
            if (suggestion) {
                event.preventDefault();
                askAgent(suggestion.dataset.agent, suggestion.dataset.suggestion);
                return;
            }

            const switchAgent = event.target.closest("[data-suggestion-agent]");
            if (switchAgent) {
                event.preventDefault();
                prefillChat(
                    switchAgent.dataset.suggestionAgent,
                    switchAgent.dataset.suggestionQuestion || "",
                );
                return;
            }

            const guideStep = event.target.closest("[data-guide-step]");
            if (guideStep) {
                event.preventDefault();
                const index = Number(guideStep.dataset.guideStep);
                state.guideStep = index;
                state.guideOpen = true;
                showApp(GUIDE_STEPS[index].view);
                return;
            }

            const riskFilter = event.target.closest("[data-risk-filter]");
            if (riskFilter) {
                event.preventDefault();
                state.riskFilter = riskFilter.dataset.riskFilter;
                $$("#risk-filters .risk-filter").forEach((item) => item.classList.toggle("active", item === riskFilter));
                renderRisks();
                return;
            }

            const riskSort = event.target.closest("[data-risk-sort]");
            if (riskSort) {
                event.preventDefault();
                state.riskSort = riskSort.dataset.riskSort;
                $$("#risk-sort .risk-filter").forEach((item) => item.classList.toggle("active", item === riskSort));
                renderRisks();
                return;
            }

            const askAlfa = event.target.closest("[data-ask-alfa]");
            const askNews = event.target.closest("[data-ask-news]");
            if (askAlfa || askNews) {
                event.preventDefault();
                const agent = askAlfa ? "alfa" : "news";
                const question = askAlfa ? askAlfa.dataset.askAlfa : askNews.dataset.askNews;
                prefillChat(agent, question);
                return;
            }

            const viewTarget = event.target.closest("[data-view]");
            if (viewTarget) {
                event.preventDefault();
                showApp(viewTarget.dataset.view);
            }
        });

        document.addEventListener("keydown", (event) => {
            if (!["Enter", " "].includes(event.key)) return;
            const target = event.target;
            if (target instanceof HTMLElement && target.matches('[role="button"][data-view]')) {
                event.preventDefault();
                showApp(target.dataset.view);
            }
        });

        $("#logout-btn")?.addEventListener("click", () => {
            try {
                localStorage.removeItem(STORAGE_KEY);
            } catch {
                // ignore
            }
            state.profile = null;
            state.analysis = null;
            state.analysisError = null;
            state.draft = null;
            state.analysisRequest += 1;
            state.loadingAnalysis = false;
            resetChat();
            showAuth("landing");
            toast("Вы вышли из профиля");
        });

        $("#refresh-analysis")?.addEventListener("click", () => loadAnalysis(true));
        $("#risks-refresh")?.addEventListener("click", () => loadAnalysis(true));
        $("#download-trace")?.addEventListener("click", downloadTrace);
        $("#audit-refresh")?.addEventListener("click", () => loadAudit(true));
        $("#risk-category-filter")?.addEventListener("change", (event) => {
            state.riskCategory = event.target.value;
            renderRisks();
        });
        $("#guide-toggle")?.addEventListener("click", () => openGuide());
        $("#guide-close")?.addEventListener("click", () => {
            state.guideOpen = false;
            renderGuide();
        });
        $("#guide-hide")?.addEventListener("click", () => {
            state.guideOpen = false;
            renderGuide();
        });
        $("#guide-next")?.addEventListener("click", nextGuideStep);
        $("#edit-profile-btn")?.addEventListener("click", openEdit);
        $("#edit-close")?.addEventListener("click", closeEdit);
        $("#edit-cancel")?.addEventListener("click", closeEdit);
        $("#feedback-submit")?.addEventListener("click", submitFeedback);

        $("#edit-dialog")?.addEventListener("click", (event) => {
            if (event.target === $("#edit-dialog")) closeEdit();
        });

        // Вход
        $("#login-form")?.addEventListener("submit", async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const data = new FormData(form);
            const login = String(data.get("login") || "").trim();
            const password = String(data.get("password") || "");
            const button = form.querySelector('button[type="submit"]');
            if (!login || !password) {
                toast("Введите логин и пароль", "error");
                return;
            }
            setButtonLoading(button, true, "Входим…");
            try {
                const response = await api("/api/login", { method: "POST", body: { login, password } });
                saveProfile(response.profile);
                state.analysis = null;
                state.analysisError = null;
                resetChat();
                showApp("risks");
                toast(`Здравствуйте, ${response.profile.legal_entity || "снова"}`, "success");
                await loadAnalysis(false);
            } catch (error) {
                toast(error.message, "error");
            } finally {
                setButtonLoading(button, false);
            }
        });

        $("#demo-login")?.addEventListener("click", async (event) => {
            const button = event.currentTarget;
            setButtonLoading(button, true, "Входим…");
            try {
                const response = await api("/api/login", { method: "POST", body: { login: "demo", password: "demo" } });
                saveProfile(response.profile);
                state.analysis = null;
                state.analysisError = null;
                resetChat();
                showApp("risks");
                toast("Профиль U_84 открыт — сразу к рискам", "success");
                await loadAnalysis(false);
            } catch (error) {
                toast(error.message, "error");
            } finally {
                setButtonLoading(button, false);
            }
        });

        // Регистрация: шаг 1
        $("#register-form")?.addEventListener("submit", (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const data = new FormData(form);
            const industry = String(data.get("industry") || "");
            const custom = String(data.get("custom_industry") || "").trim();
            const legalEntity = String(data.get("legal_entity") || "").trim();
            const region = String(data.get("region") || "");
            const scale = String(data.get("scale") || "");

            if (legalEntity.length < 2) {
                toast("Укажите название юридического лица", "error");
                return;
            }
            if (!industry) {
                toast("Выберите сферу деятельности", "error");
                return;
            }
            if (industry === "other" && !custom) {
                toast("Опишите свою сферу — агент определит отрасль по словам", "error");
                return;
            }
            if (!region || !scale) {
                toast("Выберите регион и масштаб бизнеса", "error");
                return;
            }

            state.draft = {
                legal_entity: legalEntity,
                industry,
                custom_industry: industry === "other" ? custom : "",
                region,
                city: region === "Москва" ? "Москва" : "",
                scale,
                employees: String(data.get("employees") || ""),
                company_age: String(data.get("company_age") || ""),
                growth_stage: String(data.get("growth_stage") || ""),
                products: data.getAll("product"),
                has_fts: Boolean(getFormField(form, "has_fts")?.checked),
                fts_country: String(data.get("fts_country") || ""),
                has_factoring: Boolean(getFormField(form, "has_factoring")?.checked),
            };
            showAuth("register-2");
        });

        // Регистрация: шаг 2
        $("#register-2-form")?.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (!state.draft) {
                showAuth("register");
                return;
            }
            const form = event.currentTarget;
            const data = new FormData(form);
            const login = String(data.get("login") || "").trim();
            const password = String(data.get("password") || "");
            const password2 = String(data.get("password2") || "");
            const button = form.querySelector('button[type="submit"]');

            if (!login || login.length < 3) {
                toast("Логин должен быть не короче 3 символов", "error");
                return;
            }
            if (password.length < 4) {
                toast("Пароль должен быть не короче 4 символов", "error");
                return;
            }
            if (password !== password2) {
                toast("Пароли не совпадают", "error");
                return;
            }

            setButtonLoading(button, true, "Создаём профиль…");
            try {
                const response = await api("/api/register", {
                    method: "POST",
                    body: { ...state.draft, login, password },
                });
                saveProfile(response.profile);
                state.draft = null;
                state.analysis = null;
                state.analysisError = null;
                resetChat();
                showApp("risks");
                toast(response.note || "Профиль создан", "success");
                await loadAnalysis(false);
            } catch (error) {
                toast(error.message, "error");
            } finally {
                setButtonLoading(button, false);
            }
        });

        // Редактирование профиля
        $("#edit-form")?.addEventListener("submit", submitEdit);
        $("#edit-industry")?.addEventListener("change", (event) => {
            toggleEditCustom(event.target.value === "other");
        });
        $("#edit-fts")?.addEventListener("change", (event) => {
            $("#edit-fts-wrap")?.classList.toggle("hidden", !event.target.checked);
        });

        // Регистрация: динамические поля
        $("#reg-industry")?.addEventListener("change", (event) => {
            toggleRegCustom(event.target.value === "other");
        });
        $("#reg-fts")?.addEventListener("change", (event) => {
            $("#fts-country-wrap")?.classList.toggle("hidden", !event.target.checked);
        });

        // Чаты
        $$(".chat-composer").forEach((form) => {
            form.addEventListener("submit", (event) => {
                event.preventDefault();
                const agent = form.dataset.agent;
                const data = new FormData(form);
                const question = String(data.get("question") || "").trim();
                if (!question) return;
                if (question.length < 2) {
                    toast("Введите вопрос подробнее — хотя бы пару слов.", "error");
                    return;
                }
                form.reset();
                askAgent(agent, question);
            });
        });

        // Обратная связь
        $("#rating-row")?.addEventListener("click", (event) => {
            const button = event.target.closest("[data-rating]");
            if (!button) return;
            state.feedbackRating = Number(button.dataset.rating);
            $$("#rating-row .rating-btn").forEach((item) => item.classList.toggle("active", item === button));
        });
        $("#category-row")?.addEventListener("click", (event) => {
            const button = event.target.closest("[data-category]");
            if (!button) return;
            state.feedbackCategory = button.dataset.category;
            $$("#category-row .category-btn").forEach((item) => item.classList.toggle("active", item === button));
        });
    }

    // -----------------------------------------------------------------
    // Инициализация
    // -----------------------------------------------------------------

    async function init() {
        bindEvents();

        const saved = loadSavedProfile();
        if (saved) {
            state.profile = saved;
            resetChat();
            showApp("risks");
        } else {
            showAuth("landing");
        }

        await loadMeta();

        if (state.profile) {
            renderProfile();
            await loadAnalysis(false);
        }
    }

    document.addEventListener("DOMContentLoaded", init);
})();
