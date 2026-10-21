"""
Извлечение текста из PDF-файлов аналитики Альфа-Банка через OCR.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import fitz  # PyMuPDF

PDF_DIR = Path("/home/v/Рабочий стол/pupupu/Альфа хакатон/пример")
OUTPUT_FILE = Path("/home/v/Рабочий стол/pupupu/Альфа хакатон/solution/data/alfa_analytics/alfa_analytics.json")

# Метаданные для каждого файла (из кейса)
FILE_METADATA = {
    "Inflation_tracker_02.pdf": {
        "title": "Инфляция 25–31 августа: основные выводы",
        "category": "inflation",
        "date": "2026-09-01",
    },
    "Бонд_Бриф_14092026.pdf": {
        "title": "Бонд Бриф: итоги недели",
        "category": "bonds",
        "date": "2026-09-14",
    },
    "Gold_digest_August26.pdf": {
        "title": "Обзор рынка золота, август 2026",
        "category": "commodities",
        "date": "2026-08-31",
    },
    "FI_Strategy_3Q26_22072026.pdf": {
        "title": "Тактический взгляд на 3-й квартал 2026 года: время собирать камни",
        "category": "macro_outlook",
        "date": "2026-07-22",
    },
    "ALFA-consumption.pdf": {
        "title": "Потребление на пике",
        "category": "consumption",
        "date": "2026-08-20",
    },
    "ALFA-Macro_Insights-Policy_Rate_11Sep.pdf": {
        "title": "Ключевая ставка ЦБ РФ: ставка без изменения на 14,0%, риторика стала жестче",
        "category": "monetary_policy",
        "date": "2026-09-11",
    },
    "ALFA-7M26.pdf": {
        "title": "Макростатистика 7М26: данные по рынку труда не подтверждают охлаждения экономики",
        "category": "labor_market",
        "date": "2026-08-15",
    },
    "ALFA-macro_stat1H26.pdf": {
        "title": "Макростатистика 1П26: слабый рост 1П26 смещает прогноз роста ВВП на 0,1% за год",
        "category": "macro_outlook",
        "date": "2026-07-01",
    },
    "ALFA_Russian_Steels_1К21PreviewUpdate_15Apr2021.pdf": {
        "title": "Обзор российской сталелитейной отрасли",
        "category": "industry",
        "date": "2021-04-15",
    },
}


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Извлечение текста из PDF через OCR (Tesseract)."""
    doc = fitz.open(pdf_path)
    all_text = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Рендерим страницу в изображение (высокое разрешение для качественного OCR)
        mat = fitz.Matrix(2, 2)  # 2x zoom
        pix = page.get_pixmap(matrix=mat)

        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            pix.save(tmp.name)

            # Запускаем Tesseract
            result = subprocess.run(
                [
                    "tesseract",
                    tmp.name,
                    "stdout",
                    "-l",
                    "rus+eng",
                    "--psm",
                    "3",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            all_text.append(result.stdout)

            # Удаляем временный 文件л
            Path(tmp.name).unlink(missing_ok=True)

    doc.close()
    return "\n\n".join(all_text)


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    analytics = []

    for pdf_file in sorted(PDF_DIR.glob("*.pdf")):
        metadata = FILE_METADATA.get(pdf_file.name, {})
        print(f"Обрабатываю: {pdf_file.name}")

        try:
            text = extract_text_from_pdf(pdf_file)

            analytics.append({
                "id": f"alfa_{len(analytics) + 1:03d}",
                "title": metadata.get("title", pdf_file.stem),
                "category": metadata.get("category", "unknown"),
                "date": metadata.get("date", ""),
                "content": text,
                "source_file": pdf_file.name,
            })

            print(f"  Извлечено {len(text)} символов")

        except Exception as e:
            print(f"  Ошибка: {e}")

    # Сохраняем результат
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(analytics, f, ensure_ascii=False, indent=2)

    print(f"\nГотово! Сохранено {len(analytics)} материалов в {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
