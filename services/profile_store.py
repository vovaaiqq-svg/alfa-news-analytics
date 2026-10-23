"""
Хранилище пользовательских профилей, аккаунтов и отзывов.

Данные лежат в .run/ и не попадают в git. Это демо-хранилище:
в продакшене его следует заменить на БД.
"""

import hashlib
import json
import secrets
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

RUN_DIR = Path(__file__).resolve().parent.parent / ".run"
PROFILES_FILE = RUN_DIR / "custom_clients.json"
ACCOUNTS_FILE = RUN_DIR / "accounts.json"
FEEDBACK_FILE = RUN_DIR / "feedback.jsonl"

_LOCK = threading.Lock()


def _ensure_dir() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    _ensure_dir()
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data: Any) -> None:
    _ensure_dir()
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Профили
# ---------------------------------------------------------------------------

def load_custom_profiles() -> Dict[str, Dict[str, Any]]:
    return _read_json(PROFILES_FILE, {})


def get_custom_profile(client_id: str) -> Optional[Dict[str, Any]]:
    return load_custom_profiles().get(client_id)


def save_custom_profile(client_id: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        profiles = load_custom_profiles()
        raw = dict(raw)
        raw["SYNTHETIC_U"] = client_id
        raw["_UPDATED_AT"] = datetime.now().isoformat(timespec="seconds")
        profiles[client_id] = raw
        _write_json(PROFILES_FILE, profiles)
    return raw


def update_custom_profile(client_id: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    return save_custom_profile(client_id, raw)


# ---------------------------------------------------------------------------
# Аккаунты
# ---------------------------------------------------------------------------

def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000
    ).hex()


def _normalize_login(login: str) -> str:
    return (login or "").strip().lower()


def register_account(login: str, password: str, client_id: str) -> None:
    login = _normalize_login(login)
    if not login:
        raise ValueError("Логин не может быть пустым")
    if len(password or "") < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    with _LOCK:
        accounts = _read_json(ACCOUNTS_FILE, {})
        if login in accounts:
            raise ValueError("Логин уже занят")
        salt = secrets.token_hex(16)
        accounts[login] = {
            "client_id": client_id,
            "salt": salt,
            "password_hash": _hash_password(password, salt),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        _write_json(ACCOUNTS_FILE, accounts)


def verify_account(login: str, password: str) -> Optional[str]:
    login = _normalize_login(login)
    accounts = _read_json(ACCOUNTS_FILE, {})
    account = accounts.get(login)
    if not account:
        return None
    expected = account.get("password_hash", "")
    actual = _hash_password(password or "", account.get("salt", ""))
    if secrets.compare_digest(expected, actual):
        return account.get("client_id")
    return None


def account_exists(login: str) -> bool:
    return _normalize_login(login) in _read_json(ACCOUNTS_FILE, {})


# ---------------------------------------------------------------------------
# Отзывы
# ---------------------------------------------------------------------------

def save_feedback(entry: Dict[str, Any]) -> None:
    _ensure_dir()
    payload = dict(entry)
    payload["created_at"] = datetime.now().isoformat(timespec="seconds")
    with _LOCK:
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Представление профиля для фронтенда
# ---------------------------------------------------------------------------

def _is_true(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "1.0", "true", "yes", "да"}


def format_money(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.1f} млрд ₽".replace(".0", "")
    if number >= 1_000_000:
        return f"{number / 1_000_000:.0f} млн ₽"
    if number >= 1_000:
        return f"{number / 1_000:.0f} тыс. ₽"
    return f"{number:.0f} ₽"


def _products(raw: Dict[str, Any]) -> List[str]:
    mapping = [
        ("CL_PRODUCT_RKO_MARK", "РКО"),
        ("CL_PRODUCT_LOA_MARK", "Кредиты"),
        ("CL_PRODUCT_DEP_MARK", "Депозиты"),
        ("CL_PRODUCT_GAR_MARK", "Гарантии"),
        ("CL_PRODUCT_LEA_MARK", "Лизинг"),
        ("CL_PRODUCT_ZPP_MARK", "Зарплатный проект"),
    ]
    return [label for field, label in mapping if _is_true(raw.get(field))]


def _derive_scale(raw: Dict[str, Any]) -> str:
    if raw.get("_SCALE_LABEL"):
        return str(raw["_SCALE_LABEL"])
    try:
        revenue = float(raw.get("REVENUE_COMPANY") or 0)
    except (TypeError, ValueError):
        revenue = 0
    if revenue >= 5_000_000_000:
        return "Крупный бизнес"
    if revenue >= 300_000_000:
        return "Средний бизнес"
    return "Малый бизнес"


def to_public_profile(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Превращает строку CSV/кастомный профиль в удобный для UI объект."""
    if not raw:
        return {}

    client_id = raw.get("SYNTHETIC_U") or raw.get("client_id") or ""
    legal_entity = (
        raw.get("_LEGAL_ENTITY")
        or raw.get("LEGAL_ENTITY")
        or raw.get("COMPANY_NAME")
        or f"Компания {client_id}"
    )
    industry = (
        raw.get("_INDUSTRY_LABEL")
        or raw.get("MAINOKVED_NAME")
        or "Не указана"
    )
    region = raw.get("REGION") or raw.get("_REGION") or "Не указан"
    city = raw.get("CITY") or ""
    revenue = raw.get("REVENUE_COMPANY")
    products = _products(raw)

    return {
        "client_id": client_id,
        "legal_entity": legal_entity,
        "industry": industry,
        "custom_industry": raw.get("_CUSTOM_INDUSTRY", ""),
        "okved": raw.get("MAINOKVED_NAME", ""),
        "okved_code": raw.get("MAINOKVED_CODE", ""),
        "region": region,
        "city": city,
        "revenue": revenue,
        "revenue_label": format_money(revenue) if revenue else "—",
        "scale": _derive_scale(raw),
        "employees": raw.get("AMOUNT_WORKERS_FNS_GRADATION") or "—",
        "company_age": raw.get("COMPANY_AGE_YEARS_GRADATION") or "—",
        "growth_stage": raw.get("ECO_MARK_LABEL") or "—",
        "products": products,
        "has_fts": _is_true(raw.get("FTS_FLAG")),
        "fts_country": raw.get("FTS_COUNTRY_NAME") or "",
        "has_factoring": _is_true(raw.get("FACTORING_MARK")),
        "source": raw.get("_SOURCE") or "Внутренняя база данных",
        "is_custom": bool(raw.get("_SOURCE")),
    }
