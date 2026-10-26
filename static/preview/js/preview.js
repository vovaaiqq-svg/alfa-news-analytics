(() => {
  "use strict";

  const SCREENS = [
    { id: "2001_3", name: "Лендинг" },
    { id: "2001_16", name: "Вход" },
    { id: "2001_29", name: "Регистрация · бизнес" },
    { id: "2001_52", name: "Регистрация · бизнес заполнен" },
    { id: "2001_77", name: "Регистрация · аккаунт" },
    { id: "2001_93", name: "Регистрация · контакты" },
    { id: "2001_109", name: "Регистрация · успех" },
    { id: "2001_126", name: "Профиль / главная" },
    { id: "2001_269", name: "Выбор агента" },
    { id: "2001_242", name: "Альфа-агент · чат" },
    { id: "2001_389", name: "Новостной агент · чат" },
    { id: "2001_334", name: "Риски" },
    { id: "2001_356", name: "Возможности" },
    { id: "2001_303", name: "FAQ" },
    { id: "2001_322", name: "Задать вопрос" },
    { id: "2001_416", name: "Обратная связь" },
    { id: "2001_378", name: "Трассировка" }
  ];

  const NAV_MAP = {
    "Главная": "2001_126",
    "Возможности": "2001_356",
    "Риски": "2001_334",
    "Агенты": "2001_269",
    "Профиль": "2001_126",
    "Войти": "2001_16",
    "Зарегистрироваться": "2001_29",
    "Зарегистрируйтесь": "2001_29",
    "Зарегистрируйтесь,": "2001_29",
    "Перейти к аналитике": "2001_334",
    "Альфа Агент": "2001_242",
    "Альфа-агент": "2001_242",
    "Новостной Агент": "2001_389",
    "Новостной агент": "2001_389",
    "Задать вопрос": "2001_322",
    "Оставить отзыв": "2001_416",
    "Трассировка": "2001_378"
  };

  const SCALES = ["Микробизнес", "Малый бизнес", "Средний бизнес", "Крупный бизнес"];

  const REGISTRATION_REQUIRED = [
    ["legal_entity", "Название юридического лица"],
    ["industry", "Сфера деятельности"],
    ["region", "Регион"],
    ["scale", "Масштаб"]
  ];

  const FIELD_DEFS = {
    "2001_16": [
      {
        target: "2001_19", type: "text", group: "login", key: "login",
        placeholder: "Введите логин", autocomplete: "username", aria: "Логин"
      },
      {
        target: "2001_18", type: "password", group: "login", key: "password",
        placeholder: "Введите пароль", autocomplete: "current-password", aria: "Пароль"
      }
    ],
    "2001_29": [
      {
        target: "2001_36", type: "text", group: "registration", key: "legal_entity",
        placeholder: "ООО «Ваша компания»", aria: "Название юридического лица"
      },
      {
        target: "2001_39", type: "text", group: "registration", key: "industry",
        placeholder: "Например, IT и технологии", paddingLeft: 95,
        aria: "Сфера деятельности"
      },
      {
        target: "2001_37", type: "text", group: "registration", key: "region",
        placeholder: "Например, Москва и МО", paddingLeft: 95,
        aria: "Регион"
      },
      {
        target: "2001_38", type: "select", group: "registration", key: "scale",
        placeholder: "Выберите масштаб", options: SCALES, aria: "Масштаб бизнеса"
      }
    ],
    "2001_52": [
      {
        target: "2001_59", type: "text", group: "registration", key: "legal_entity",
        placeholder: "ООО «Ваша компания»", aria: "Название юридического лица"
      },
      {
        target: "2001_62", type: "text", group: "registration", key: "industry",
        placeholder: "Например, IT и технологии", paddingLeft: 95,
        aria: "Сфера деятельности"
      },
      {
        target: "2001_60", type: "text", group: "registration", key: "region",
        placeholder: "Например, Москва и МО", paddingLeft: 95,
        aria: "Регион"
      },
      {
        target: "2001_61", type: "select", group: "registration", key: "scale",
        placeholder: "Выберите масштаб", options: SCALES, aria: "Масштаб бизнеса"
      }
    ],
    "2001_77": [
      {
        target: "2001_82", type: "text", group: "account", key: "login",
        placeholder: "Придумайте логин", autocomplete: "username", aria: "Логин"
      },
      {
        target: "2001_84", type: "password", group: "account", key: "password",
        placeholder: "Придумайте пароль", autocomplete: "new-password", aria: "Пароль"
      },
      {
        target: "2001_83", type: "password", group: "account", key: "repeat",
        placeholder: "Повторите пароль", autocomplete: "new-password", aria: "Повторение пароля"
      }
    ],
    "2001_93": [
      {
        target: "2001_98", type: "text", group: "contacts", key: "fio",
        placeholder: "Иванов Иван Иванович", autocomplete: "name", aria: "ФИО"
      },
      {
        target: "2001_100", type: "email", group: "contacts", key: "email",
        placeholder: "name@company.ru", autocomplete: "email", aria: "Адрес электронной почты"
      },
      {
        target: "2001_99", type: "tel", group: "contacts", key: "phone",
        placeholder: "+7 999 000-00-00", autocomplete: "tel", aria: "Номер телефона"
      }
    ],
    "2001_269": [
      {
        target: "2001_271", type: "text", group: "agentPrompt", key: "text",
        placeholder: "Введите сообщение", paddingLeft: 43, paddingRight: 90,
        aria: "Вопрос для подбора агента", enter: "agent"
      }
    ],
    "2001_242": [
      {
        target: "2001_244", type: "text", group: "chat", key: "alfa",
        placeholder: "Введите сообщение", paddingLeft: 43, paddingRight: 90,
        aria: "Сообщение Альфа-агенту", enter: "chat-alfa"
      }
    ],
    "2001_389": [
      {
        target: "2001_391", type: "text", group: "chat", key: "news",
        placeholder: "Введите сообщение", paddingLeft: 43, paddingRight: 90,
        aria: "Сообщение Новостному агенту", enter: "chat-news"
      }
    ],
    "2001_322": [
      {
        target: "2001_325", type: "textarea", group: "question", key: "text",
        placeholder: "Введите ваш вопрос", fontSize: "30px", lineHeight: "1.35",
        padding: "29px 38px 30px", borderRadius: "0", aria: "Ваш вопрос"
      }
    ],
    "2001_416": [
      {
        target: "2001_425", container: "target", type: "textarea", group: "feedback", key: "positive",
        left: 25, top: 82, width: 1608, height: 130,
        placeholder: "Опишите, какие преимущества вы видите в сервисе. Что для вас стало особенно важным?",
        fontSize: "24px", lineHeight: "1.35", padding: "0", aria: "Что вам нравится в сервисе"
      },
      {
        target: "2001_421", container: "target", type: "textarea", group: "feedback", key: "negative",
        left: 25, top: 82, width: 1608, height: 130,
        placeholder: "Опишите, с какими трудностями вы столкнулись. Какие неудобства вызвал сервис? Что можно улучшить?",
        fontSize: "24px", lineHeight: "1.35", padding: "0", aria: "Что вам не нравится в сервисе"
      }
    ]
  };

  const HIDE_BY_SCREEN = {
    "2001_52": ["2001_71", "2001_72"],
    "2001_269": ["2001_272"],
    "2001_242": ["2001_248"],
    "2001_389": ["2001_395"],
    "2001_322": ["2001_326"],
    "2001_416": ["2001_424", "2001_428"]
  };

  const ENTER_ACTIONS = {
    "2001_16": "2001_22",
    "2001_29": "2001_50",
    "2001_52": "preview-next-52",
    "2001_77": "2001_91",
    "2001_93": "2001_107"
  };

  const $ = (id) => document.getElementById(id);
  const select = $("preview-screen");
  const count = $("preview-count");
  const fitButton = $("preview-fit");
  const scroll = document.querySelector(".scroll-container");
  const frames = () => Array.from(document.querySelectorAll('.Pixso-canvas-0_1 > div[id^="2001_"]'));

  const state = {
    login: { login: "", password: "" },
    registration: { legal_entity: "", industry: "", region: "", scale: "" },
    account: { login: "", password: "", repeat: "" },
    contacts: { fio: "", email: "", phone: "" },
    agentPrompt: { text: "" },
    chat: { alfa: "", news: "" },
    question: { text: "" },
    feedback: { positive: "", negative: "" }
  };

  const controls = new Map();
  const actionIndex = new Map();
  let current = 0;
  let fit = true;
  let lastHash = "";
  let registrationMode = "onboarding";
  let toastEl = null;
  let toastTimer = 0;

  function validIndex(id) {
    const i = SCREENS.findIndex((s) => s.id === id);
    return i >= 0 ? i : 0;
  }

  function currentScreenId() {
    return SCREENS[current].id;
  }

  function showByIndex(index, updateHash = true) {
    current = (index + SCREENS.length) % SCREENS.length;
    const screen = SCREENS[current];
    frames().forEach((el) => {
      const active = el.id === screen.id;
      el.classList.toggle("is-active", active);
      el.style.display = active ? "block" : "none";
    });
    select.value = screen.id;
    count.textContent = `${current + 1} / ${SCREENS.length}`;
    document.title = `${screen.name} — Альфа-Бизнес preview`;
    if (scroll) {
      scroll.scrollTop = 0;
      scroll.scrollLeft = 0;
    }
    if (screen.id === "2001_126") syncProfile();
    ensureInteractive(screen.id);
    if (updateHash) {
      lastHash = `#${screen.id}`;
      history.replaceState(null, "", lastHash);
    }
  }

  function showById(id, updateHash = true) {
    showByIndex(validIndex(id), updateHash);
  }

  function applyFit() {
    fitButton.classList.toggle("is-on", fit);
    fitButton.textContent = fit ? "Вписать" : "100%";
    document.body.classList.toggle("fit", fit);
    if (!fit) {
      document.documentElement.style.setProperty("--preview-zoom", "1");
      document.documentElement.style.setProperty("--preview-offset", "0px");
      return;
    }
    const width = Math.max(320, window.innerWidth);
    const barHeight = document.querySelector(".preview-bar")?.offsetHeight || 58;
    const height = Math.max(320, window.innerHeight - barHeight);
    const scale = Math.min(1, width / 1920, height / 1080);
    const zoom = Math.max(0.32, scale);
    const offset = Math.max(0, (width - 1920 * zoom) / 2);
    document.documentElement.style.setProperty("--preview-zoom", String(zoom));
    document.documentElement.style.setProperty("--preview-offset", `${offset}px`);
  }

  function notify(message, type = "ok") {
    if (!toastEl) {
      toastEl = document.createElement("div");
      toastEl.className = "preview-toast";
      toastEl.setAttribute("role", "status");
      toastEl.setAttribute("aria-live", "polite");
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = message;
    toastEl.classList.toggle("is-error", type === "error");
    toastEl.classList.add("is-visible");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      toastEl.classList.remove("is-visible");
    }, type === "error" ? 4200 : 3200);
  }

  function stateValue(group, key) {
    return state[group] && typeof state[group][key] === "string" ? state[group][key] : "";
  }

  function setControlValue(el, value) {
    const next = value || "";
    if (el.value !== next) el.value = next;
    el.classList.toggle("is-empty", !next);
  }

  function syncScreen(screenId) {
    const list = controls.get(screenId);
    if (!list) return;
    list.forEach(({ el, def }) => {
      setControlValue(el, stateValue(def.group, def.key));
    });
  }

  function focusField(screenId, key) {
    const list = controls.get(screenId);
    if (!list) return;
    const item = list.find((entry) => entry.def.key === key);
    if (item) {
      item.el.focus();
      item.el.scrollIntoView({ block: "center", inline: "center" });
    }
  }

  function valueOf(group, key) {
    return stateValue(group, key).trim();
  }

  function fail(message, screenId, key) {
    notify(message, "error");
    if (screenId && key) focusField(screenId, key);
    return false;
  }

  function hideFake(screenId) {
    (HIDE_BY_SCREEN[screenId] || []).forEach((id) => {
      const el = $(id);
      if (el) el.style.display = "none";
    });
  }

  function createField(screenId, def) {
    const frame = $(screenId);
    const target = $(def.target);
    if (!frame || !target) return null;

    const inTarget = def.container === "target";
    const parent = inTarget ? target : frame;
    const left = inTarget ? (def.left || 0) : target.offsetLeft + (def.left || 0);
    const top = inTarget ? (def.top || 0) : target.offsetTop + (def.top || 0);
    const width = def.width || target.offsetWidth;
    const height = def.height || target.offsetHeight;

    let el;
    if (def.type === "textarea") {
      el = document.createElement("textarea");
      el.rows = 3;
      el.spellcheck = false;
    } else if (def.type === "select") {
      el = document.createElement("select");
    } else {
      el = document.createElement("input");
      el.type = def.type || "text";
    }

    el.className = "preview-field";
    if (def.type === "textarea") el.classList.add("preview-field--textarea");
    if (def.type === "select") el.classList.add("preview-field--select");
    el.id = `preview-field-${screenId}-${def.key}`;
    el.dataset.group = def.group;
    el.dataset.key = def.key;
    el.dataset.screen = screenId;
    el.style.left = `${left}px`;
    el.style.top = `${top}px`;
    el.style.width = `${width}px`;
    el.style.height = `${height}px`;
    if (def.fontSize) el.style.fontSize = def.fontSize;
    if (def.lineHeight) el.style.lineHeight = def.lineHeight;
    if (def.padding) el.style.padding = def.padding;
    if (def.borderRadius) el.style.borderRadius = def.borderRadius;
    if (def.paddingLeft != null) el.style.paddingLeft = `${def.paddingLeft}px`;
    if (def.paddingRight != null) el.style.paddingRight = `${def.paddingRight}px`;
    el.placeholder = def.placeholder || "";
    el.setAttribute("aria-label", def.aria || def.placeholder || def.key);
    el.autocomplete = def.autocomplete || "off";

    if (def.type === "select") {
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = def.placeholder || "Выберите значение";
      el.appendChild(placeholder);
      (def.options || []).forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        el.appendChild(option);
      });
    }

    const handleInput = () => {
      if (!state[def.group]) state[def.group] = {};
      state[def.group][def.key] = el.value;
      el.classList.toggle("is-empty", !el.value);
      if (def.group === "registration") syncRegistrationSiblings(screenId);
    };

    el.addEventListener("input", handleInput);
    el.addEventListener("change", handleInput);
    el.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || def.type === "textarea" || def.type === "select") return;
      event.preventDefault();
      if (def.enter === "chat-alfa") sendChat("alfa");
      else if (def.enter === "chat-news") sendChat("news");
      else if (def.enter === "agent") submitAgentPrompt();
      else {
        const actionId = ENTER_ACTIONS[screenId];
        if (actionId) triggerAction(actionId);
      }
    });

    parent.appendChild(el);
    setControlValue(el, stateValue(def.group, def.key));
    return { el, def };
  }

  function syncRegistrationSiblings(screenId) {
    const list = controls.get(screenId === "2001_29" ? "2001_52" : "2001_29");
    if (!list) return;
    list.forEach(({ el, def }) => {
      if (def.group !== "registration") return;
      if (document.activeElement === el) return;
      setControlValue(el, stateValue("registration", def.key));
    });
  }

  function ensureInteractive(screenId) {
    if (controls.has(screenId)) {
      syncScreen(screenId);
      return;
    }
    const defs = FIELD_DEFS[screenId];
    if (!defs) return;
    if (screenId === "2001_52") seedFilledRegistration();
    hideFake(screenId);
    const list = defs.map((def) => createField(screenId, def)).filter(Boolean);
    controls.set(screenId, list);
    if (screenId === "2001_16") addLoginSubmit();
    if (screenId === "2001_52") addFilledRegistrationNext();
    if (screenId === "2001_242") addSendButton(screenId, "2001_249", "alfa");
    if (screenId === "2001_389") addSendButton(screenId, "2001_404", "news");
    if (screenId === "2001_269") addSendButton(screenId, "2001_273", "agent");
    syncScreen(screenId);
  }

  function addLoginSubmit() {
    const frame = $("2001_16");
    if (!frame || $("preview-login-submit")) return;
    const button = document.createElement("button");
    button.type = "button";
    button.id = "preview-login-submit";
    button.className = "preview-login-submit";
    button.textContent = "Войти →";
    button.style.left = "810px";
    button.style.top = "748px";
    button.style.width = "300px";
    button.style.height = "64px";
    button.addEventListener("click", submitLogin);
    frame.appendChild(button);
  }

  function addSendButton(screenId, vectorId, kind) {
    const frame = $(screenId);
    const vector = $(vectorId);
    if (!frame || !vector || $(`preview-send-${screenId}`)) return;
    const button = document.createElement("button");
    button.type = "button";
    button.id = `preview-send-${screenId}`;
    button.className = "preview-icon-button";
    button.setAttribute("aria-label", kind === "agent" ? "Подобрать агента" : "Отправить сообщение");
    button.style.left = `${vector.offsetLeft - 12}px`;
    button.style.top = `${vector.offsetTop - 20}px`;
    button.style.width = "62px";
    button.style.height = "58px";
    button.addEventListener("click", () => {
      if (kind === "agent") submitAgentPrompt();
      else sendChat(kind);
    });
    frame.appendChild(button);
  }

  function addFilledRegistrationNext() {
    const frame = $("2001_52");
    if (!frame || $("preview-next-52")) return;
    const button = document.createElement("button");
    button.type = "button";
    button.id = "preview-next-52";
    button.className = "preview-cta";
    button.textContent = "Далее →";
    button.style.left = "1201px";
    button.style.top = "944px";
    button.style.width = "270px";
    button.style.height = "52px";
    const handleNext = () => {
      const missing = REGISTRATION_REQUIRED.find(([key]) => !valueOf("registration", key));
      if (missing) {
        notify(`Заполните поле «${missing[1]}»`, "error");
        showById("2001_29");
        focusField("2001_29", missing[0]);
        return;
      }
      if (registrationMode === "edit") {
        registrationMode = "onboarding";
        showById("2001_126");
        notify("Профиль обновлён в демо-режиме.");
      } else {
        showById("2001_77");
      }
    };
    button.addEventListener("click", handleNext);
    actionIndex.set("preview-next-52", handleNext);
    frame.appendChild(button);
  }

  function seedFilledRegistration() {
    const r = state.registration;
    if (!r.legal_entity.trim()) r.legal_entity = "ООО «Дедлайн вчера»";
    if (!r.industry.trim()) r.industry = "IT и технологии";
    if (!r.region.trim()) r.region = "Москва и МО";
    if (!r.scale.trim()) r.scale = "Средний бизнес";
  }

  function seedProfileRegistration() {
    const r = state.registration;
    if (!r.legal_entity.trim()) r.legal_entity = "ООО «Дедлайн вчера»";
    if (!r.industry.trim()) r.industry = "Строительство воздушных замков";
    if (!r.region.trim()) r.region = "Московская область";
    if (!r.scale.trim()) r.scale = "Средний бизнес";
  }

  function syncProfile() {
    const r = state.registration;
    if (r.legal_entity.trim() && $("2001_203")) $("2001_203").textContent = r.legal_entity.trim();
    if (r.region.trim() && $("2001_200")) $("2001_200").textContent = r.region.trim();
    if (r.scale.trim() && $("2001_206")) $("2001_206").textContent = r.scale.trim();
    const industry = r.industry.trim();
    if (industry && $("2001_197_0") && $("2001_197_1")) {
      const parts = industry.split(/\s+/);
      $("2001_197_0").textContent = parts[0] || "";
      $("2001_197_1").textContent = parts.slice(1).join(" ");
    }
  }

  function startRegistration(mode = "onboarding") {
    registrationMode = mode;
    if (mode === "edit") seedProfileRegistration();
    showById("2001_29");
  }

  function submitLogin() {
    if (!valueOf("login", "login")) return fail("Введите логин", "2001_16", "login");
    if (!valueOf("login", "password")) return fail("Введите пароль", "2001_16", "password");
    showById("2001_334");
    notify("Демо-вход выполнен. Сразу открываем риски и возможности.");
  }

  function submitRegistration() {
    for (const [key, label] of REGISTRATION_REQUIRED) {
      if (!valueOf("registration", key)) {
        return fail(`Заполните поле «${label}»`, "2001_29", key);
      }
    }
    showById("2001_52");
    notify("Данные сохранены. Проверьте их и нажмите «Далее».");
  }

  function submitAccount() {
    const password = valueOf("account", "password");
    if (!valueOf("account", "login")) return fail("Придумайте логин", "2001_77", "login");
    if (password.length < 4) return fail("Пароль должен быть не короче 4 символов", "2001_77", "password");
    if (password !== valueOf("account", "repeat")) {
      return fail("Пароли не совпадают", "2001_77", "repeat");
    }
    showById("2001_93");
  }

  function submitContacts() {
    if (!valueOf("contacts", "fio")) return fail("Введите ФИО", "2001_93", "fio");
    const email = valueOf("contacts", "email");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return fail("Введите корректный адрес электронной почты", "2001_93", "email");
    }
    const digits = valueOf("contacts", "phone").replace(/\D/g, "");
    if (digits.length < 10) return fail("Введите номер телефона", "2001_93", "phone");
    showById("2001_109");
    notify("Регистрация завершена. Аналитика уже готова.");
  }

  function sendChat(kind) {
    const screenId = kind === "alfa" ? "2001_242" : "2001_389";
    const text = valueOf("chat", kind);
    if (!text) return fail("Введите сообщение", screenId, kind);
    state.chat[kind] = "";
    syncScreen(screenId);
    const agent = kind === "alfa" ? "Альфа-агент" : "Новостной агент";
    notify(`${agent}: сообщение отправлено. В демо-режиме ответ не генерируется.`);
  }

  function submitAgentPrompt() {
    const text = valueOf("agentPrompt", "text");
    if (!text) return fail("Введите вопрос для подбора агента", "2001_269", "text");
    const target = /новост/i.test(text) ? "2001_389" : "2001_242";
    state.agentPrompt.text = "";
    syncScreen("2001_269");
    showById(target);
    notify(`Подобран ${target === "2001_389" ? "Новостной агент" : "Альфа-агент"} (демо).`);
  }

  function submitQuestion() {
    if (!valueOf("question", "text")) return fail("Введите ваш вопрос", "2001_322", "text");
    state.question.text = "";
    syncScreen("2001_322");
    notify("Вопрос отправлен. В рабочем сервисе на него ответит Альфа-агент.");
  }

  function submitFeedback() {
    const positive = valueOf("feedback", "positive");
    const negative = valueOf("feedback", "negative");
    if (!positive && !negative) {
      return fail("Опишите хотя бы один пункт", "2001_416", "positive");
    }
    state.feedback.positive = "";
    state.feedback.negative = "";
    syncScreen("2001_416");
    notify("Спасибо! Отзыв сохранён в демо-режиме.");
  }

  function openProfileEdit() {
    startRegistration("edit");
    notify("Демо: измените данные и нажмите «Далее».");
  }

  const ACTIONS = {
    "2001_3": {
      "2001_11_0": () => startRegistration("onboarding"),
      "2001_12": () => showById("2001_16"),
      "2001_14": () => showById("2001_16")
    },
    "2001_16": {
      "2001_22": submitLogin,
      "2001_24": () => startRegistration("onboarding")
    },
    "2001_29": {
      "2001_50": submitRegistration
    },
    "2001_77": {
      "2001_91": submitAccount
    },
    "2001_93": {
      "2001_107": submitContacts
    },
    "2001_109": {
      "2001_120": () => {
        registrationMode = "onboarding";
        showById("2001_334");
        notify("Аналитика готова. Открываем риски и возможности.");
      }
    },
    "2001_126": {
      "2001_156": openProfileEdit,
      "2001_191": () => showById("2001_322"),
      "2001_193": () => showById("2001_416"),
      "2001_237": () => showById("2001_389"),
      "2001_240": () => showById("2001_242")
    },
    "2001_269": {
      "2001_293": () => showById("2001_242"),
      "2001_301": () => showById("2001_389")
    },
    "2001_303": {
      "2001_309": () => notify("Демо-ответ: пароль можно изменить в профиле."),
      "2001_310": () => notify("Демо-ответ: Новостной агент объясняет внешние новости и показывает источники."),
      "2001_311": () => notify("Демо-ответ: задайте вопрос агенту — он подскажет, с чего начать."),
      "2001_312": () => showById("2001_322")
    },
    "2001_322": {
      "2001_327": submitQuestion
    },
    "2001_334": {
      "2001_349": () => showById("2001_356")
    },
    "2001_356": {
      "2001_371": () => showById("2001_334")
    },
    "2001_416": {
      "2001_434": submitFeedback
    }
  };

  function triggerAction(id) {
    const handler = actionIndex.get(id);
    if (handler) handler();
  }

  function bindActions() {
    Object.entries(ACTIONS).forEach(([screenId, actions]) => {
      Object.entries(actions).forEach(([id, handler]) => {
        const el = $(id);
        if (!el) return;
        actionIndex.set(id, handler);
        el.dataset.previewAction = "";
        el.setAttribute("role", "button");
        el.tabIndex = 0;
        el.style.cursor = "pointer";
        el.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (currentScreenId() !== screenId) return;
          handler();
        });
        el.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" && event.key !== " ") return;
          event.preventDefault();
          el.click();
        });
      });
    });
  }

  function markClickableNav() {
    const elements = document.querySelectorAll("p, span");
    elements.forEach((el) => {
      if (el.hasAttribute("data-preview-action") || el.closest("[data-preview-action]")) return;
      const text = (el.textContent || "").trim();
      if (!NAV_MAP[text]) return;
      if (el.children.length > 0) return;
      el.dataset.previewTarget = NAV_MAP[text];
      el.style.cursor = "pointer";
      el.title = `Открыть: ${SCREENS.find((s) => s.id === NAV_MAP[text]).name}`;
    });
    document.addEventListener("click", (event) => {
      const target = event.target.closest("[data-preview-target]");
      if (!target) return;
      event.preventDefault();
      showById(target.dataset.previewTarget);
    });
  }

  SCREENS.forEach((screen) => {
    const option = document.createElement("option");
    option.value = screen.id;
    option.textContent = screen.name;
    select.appendChild(option);
  });

  const params = new URLSearchParams(location.search);
  const fromQuery = params.get("screen");
  const fromHash = location.hash ? location.hash.slice(1) : "";
  showById(fromQuery || fromHash || "2001_3", false);
  bindActions();
  markClickableNav();

  select.addEventListener("change", () => showById(select.value));
  $("preview-prev").addEventListener("click", () => showByIndex(current - 1));
  $("preview-next").addEventListener("click", () => showByIndex(current + 1));
  fitButton.addEventListener("click", () => {
    fit = !fit;
    applyFit();
  });

  window.addEventListener("resize", applyFit);
  window.addEventListener("hashchange", () => {
    if (location.hash === lastHash) return;
    const id = location.hash ? location.hash.slice(1) : "2001_3";
    showById(id, false);
  });

  document.addEventListener("keydown", (event) => {
    if (event.target.closest("select, input, textarea, button, a, [data-preview-action]")) return;
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      showByIndex(current - 1);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      showByIndex(current + 1);
    } else if (event.key === "Home") {
      event.preventDefault();
      showByIndex(0);
    } else if (event.key === "End") {
      event.preventDefault();
      showByIndex(SCREENS.length - 1);
    }
  });

  applyFit();
})();
