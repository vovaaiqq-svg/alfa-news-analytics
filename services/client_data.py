"""
Загрузка данных о клиентах из CSV кейса или синтетического файла.
"""

import csv
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


def get_data_path() -> Path:
    """Путь к CSV: env-переменная → файл кейса → синтетика."""
    env_path = os.getenv("CLIENT_DATA_CSV")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    case_path = (
        Path(__file__).resolve().parent.parent.parent
        / "пример"
        / "extracted"
        / "df_Uid_data_hack.csv"
    )
    if case_path.exists():
        return case_path

    return Path(__file__).resolve().parent.parent / "data" / "client_profiles" / "clients.csv"


def _delimiter(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        first_line = f.readline()
    return ";" if first_line.count(";") >= first_line.count(",") else ","


def iter_client_rows(limit: Optional[int] = None) -> Iterator[Dict[str, Any]]:
    """Итератор по строкам CSV с автоопределением разделителя."""
    path = get_data_path()
    if not path.exists():
        return

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=_delimiter(path))
        for index, row in enumerate(reader):
            if limit is not None and index >= limit:
                break
            yield row


def find_client_row(client_id: str) -> Optional[Dict[str, Any]]:
    """Находит строку клиента по SYNTHETIC_U."""
    for row in iter_client_rows():
        if row.get("SYNTHETIC_U") == client_id:
            return row
    return None


def count_similar(industry: str, region: str) -> int:
    """Сколько похожих компаний есть в базе (отрасль + регион)."""
    total = 0
    for row in iter_client_rows():
        same_industry = industry and row.get("MAINOKVED_NAME") == industry
        same_region = region and row.get("REGION") == region
        if same_industry and same_region:
            total += 1
            if total >= 999:
                break
    return total
