"""Модуль фильтрации и валидации раздач.

Реализует строгие требования:
1. Только версии [portable]
2. Размер не больше 60 ГБ
3. Очистка названий игр от трекерных тегов
"""
import re

MAX_SIZE_GB = 60.0
MAX_SIZE_BYTES = int(MAX_SIZE_GB * 1024 * 1024 * 1024)  # 64,424,509,440 байт

# Регулярное выражение для поиска маркера Portable в названии или тегах
PORTABLE_REGEX = re.compile(
    r'(?:\[|\()(?:[^\]\)]*[\s/])?portable(?:[\s/][^\]\)]*)?(?:\]|\))|\bportable\b|портативн',
    re.IGNORECASE
)

# Регулярное выражение для извлечения размера из строк вида "[242.7 MB]", "1.25 GB", "500 КБ"
SIZE_EXTRACTION_REGEX = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*(B|KB|MB|GB|TB|Б|КБ|МБ|ГБ|ТБ|байт)\b',
    re.IGNORECASE
)

SIZE_MULTIPLIERS = {
    'b': 1,
    'б': 1,
    'байт': 1,
    'kb': 1024,
    'кб': 1024,
    'mb': 1024 ** 2,
    'мб': 1024 ** 2,
    'gb': 1024 ** 3,
    'гб': 1024 ** 3,
    'tb': 1024 ** 4,
    'тб': 1024 ** 4,
}


def is_portable(title: str, text: str = "") -> bool:
    """Проверяет, является ли раздача портативной версией игры.

    Проверяется как заголовок темы, так и (при наличии) текст раздачи.
    """
    if not title and not text:
        return False
    if title and PORTABLE_REGEX.search(title):
        return True
    if text and PORTABLE_REGEX.search(text):
        return True
    return False


def parse_size_to_bytes(size_str: str) -> int | None:
    """Конвертирует строку размера (напр. '306.7 MB', '1.25 GB', '500 КБ') в байты.

    Возвращает количество байт (int) или None при невозможности распарсить.
    """
    if not size_str:
        return None

    # Заменяем неразрывные пробелы
    cleaned = str(size_str).replace('\xa0', ' ').strip()
    match = SIZE_EXTRACTION_REGEX.search(cleaned)
    if not match:
        return None

    val_str, unit_str = match.groups()
    val_str = val_str.replace(',', '.')

    try:
        val = float(val_str)
        multiplier = SIZE_MULTIPLIERS.get(unit_str.lower(), 1)
        return int(val * multiplier)
    except (ValueError, TypeError):
        return None


def is_allowed_size(size_str: str, max_gb: float = MAX_SIZE_GB) -> bool:
    """Проверяет, укладывается ли размер раздачи в допустимый лимит (по умолчанию <= 60 ГБ)."""
    size_bytes = parse_size_to_bytes(size_str)
    if size_bytes is None:
        return False
    max_bytes = int(max_gb * (1024 ** 3))
    return 0 < size_bytes <= max_bytes


def extract_size_from_title(title: str) -> str | None:
    """Извлекает строку размера из конца заголовка (например '[242.7 MB]')."""
    if not title:
        return None
    m = re.search(r'\[([0-9.,]+\s*(?:B|KB|MB|GB|TB|Б|КБ|МБ|ГБ|ТБ|байт))\]\s*$', title, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Альтернативный поиск по всему заголовку
    m2 = SIZE_EXTRACTION_REGEX.search(title)
    if m2:
        return m2.group(0).strip()
    return None


def clean_game_title(raw_title: str) -> str:
    """Очищает заголовок темы от трекерных префиксов и служебных тегов.

    Пример:
    '[DL] Repel The Rifts [P] [ENG + 6] (2026, Strategy) (1.0.26) [Portable] [242.7 MB]'
    -> 'Repel The Rifts'
    """
    if not raw_title:
        return "Unknown"

    clean = raw_title.strip()

    # 1. Удаляем префиксы трекера в начале: [DL], [Обновлено], [В разработке], [Repack], [Rip]
    clean = re.sub(
        r'^(?:\[(?:DL|Обновлено|В разработке|Repack|Rip|Лицензия|L|Пиратка)[^\]]*\]\s*)+',
        '', clean, flags=re.IGNORECASE
    ).strip()

    # 2. Если заголовок содержит маркер типа издания [P] или [L], название игры идёт ДО него
    parts = re.split(r'\s+\[(?:P|L|Пиратка|Лицензия)\]', clean, flags=re.IGNORECASE)
    if len(parts) > 1 and parts[0].strip():
        clean = parts[0].strip()
    else:
        # Если [P] не было, очищаем с хвоста
        clean = re.sub(
            r'\s*\[[0-9.,]+\s*(?:B|KB|MB|GB|TB|Б|КБ|МБ|ГБ|ТБ|байт)\]\s*$',
            '', clean, flags=re.IGNORECASE
        ).strip()
        clean = re.sub(
            r'\s*\[\s*portable\b[^\]]*\]\s*$',
            '', clean, flags=re.IGNORECASE
        ).strip()
        clean = re.sub(
            r'\s*\(\s*portable\b[^\)]*\)\s*$',
            '', clean, flags=re.IGNORECASE
        ).strip()

        # Удаляем хвостовые скобки с версиями, годами, жанрами
        while True:
            prev = clean
            clean = re.sub(r'\s*\([vV]?\d+[0-9a-zA-Z._-]*\)\s*$', '', clean).strip()
            clean = re.sub(r'\s*\(\s*(?:19|20)\d\d[^)]*\)\s*$', '', clean).strip()
            clean = re.sub(r'\s*\[\s*portable\b[^\]]*\]\s*$', '', clean, flags=re.IGNORECASE).strip()
            clean = re.sub(r'\s*\[\s*(?:RUS|ENG|Multi|P|L)[^\]]*\]\s*$', '', clean, flags=re.IGNORECASE).strip()
            if clean == prev:
                break

    # 3. Очищаем кавычки
    clean = clean.replace('"', "'").strip()

    return clean if clean else raw_title
