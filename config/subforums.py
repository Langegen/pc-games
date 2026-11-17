"""Конфигурация подразделов раздела f=5 (Игры для Windows) трекера RuTracker.

Включает:
- Список разрешённых подразделов по современным жанрам и классическим (старым) играм
- Жёсткий список исключённых подразделов (f=1151, f=2228, f=68, служебные темы)
- Метаданные (название, slug, родительская категория) для использования в клиентском приложении
"""

# Родительский форум
PARENT_FORUM_ID = "5"
PARENT_FORUM_NAME = "Игры для Windows"

# Исключённые подразделы (ЧЁРНЫЙ СПИСОК)
# Эти подразделы НИ ПРИ КАКИХ УСЛОВИЯХ не опрашиваются и не включаются в базу
EXCLUDED_SUBFORUM_IDS = {
    "1151",  # Поиск и обсуждение игр для Windows
    "2228",  # Для некондиционных раздач
    "68",    # Архив (Игры)
    "1175",  # Общение, обсуждение игр для Windows
    "1176",  # Обсуждение вышедших игр для Windows
    "2341",  # Общение (Игры для Windows)
    "139",   # Прочее для Windows-игр (патчи, моды, русификаторы)
    "761",   # Редакторы, эмуляторы и прочие игровые утилиты
}

# Реестр целевых подразделов
SUBFORUMS = {
    # ─── Основные современные жанровые подразделы ───
    "635": {
        "name": "Новинки",
        "slug": "new",
        "parent": None,
        "is_retro": False,
    },
    "646": {
        "name": "Экшены от третьего лица",
        "slug": "action-tps",
        "parent": "Экшены",
        "is_retro": False,
    },
    "647": {
        "name": "Экшены от первого лица",
        "slug": "action-fps",
        "parent": "Экшены",
        "is_retro": False,
    },
    "52": {
        "name": "Ролевые игры",
        "slug": "rpg",
        "parent": None,
        "is_retro": False,
    },
    "51": {
        "name": "Стратегии в реальном времени",
        "slug": "strategy-rts",
        "parent": "Стратегии",
        "is_retro": False,
    },
    "2226": {
        "name": "Пошаговые стратегии",
        "slug": "strategy-tbs",
        "parent": "Стратегии",
        "is_retro": False,
    },
    "53": {
        "name": "Приключения и квесты",
        "slug": "adventure",
        "parent": None,
        "is_retro": False,
    },
    "54": {
        "name": "Симуляторы",
        "slug": "simulators",
        "parent": None,
        "is_retro": False,
    },
    "50": {
        "name": "Хорроры",
        "slug": "horror",
        "parent": None,
        "is_retro": False,
    },
    "127": {
        "name": "Аркады",
        "slug": "arcade",
        "parent": None,
        "is_retro": False,
    },
    "962": {
        "name": "Автосимуляторы и гонки",
        "slug": "racing",
        "parent": None,
        "is_retro": False,
    },
    "2187": {
        "name": "Спортивные симуляторы",
        "slug": "sports",
        "parent": None,
        "is_retro": False,
    },
    "2204": {
        "name": "Логические игры",
        "slug": "puzzle",
        "parent": None,
        "is_retro": False,
    },
    "1008": {
        "name": "Квесты в стиле Поиск предметов",
        "slug": "hidden-object",
        "parent": "Приключения и квесты",
        "is_retro": False,
    },
    "959": {
        "name": "Демо-версии и игры с ранним доступом",
        "slug": "early-access",
        "parent": None,
        "is_retro": False,
    },
    "2118": {
        "name": "Антологии и сборники игр",
        "slug": "collections",
        "parent": None,
        "is_retro": False,
    },
    "2115": {
        "name": "Онлайн Игры",
        "slug": "online",
        "parent": None,
        "is_retro": False,
    },

    # ─── Ретро и классические игры (Старые игры) ───
    "1007": {
        "name": "Старые игры (Аркады)",
        "slug": "retro-arcade",
        "parent": "Старые игры",
        "is_retro": True,
    },
    "1310": {
        "name": "Старые игры (Экшены)",
        "slug": "retro-action",
        "parent": "Старые игры",
        "is_retro": True,
    },
    "2205": {
        "name": "Старые игры (Стратегии)",
        "slug": "retro-strategy",
        "parent": "Старые игры",
        "is_retro": True,
    },
    "2206": {
        "name": "Старые игры (Симуляторы)",
        "slug": "retro-simulators",
        "parent": "Старые игры",
        "is_retro": True,
    },
    "2225": {
        "name": "Старые игры (Приключения и квесты)",
        "slug": "retro-adventure",
        "parent": "Старые игры",
        "is_retro": True,
    },
    "2227": {
        "name": "Автосимуляторы и гонки (Старые Игры)",
        "slug": "retro-racing",
        "parent": "Старые игры",
        "is_retro": True,
    },
    "2385": {
        "name": "Логические игры (Старые Игры)",
        "slug": "retro-puzzle",
        "parent": "Старые игры",
        "is_retro": True,
    },
    "2410": {
        "name": "Старые игры (Ролевые игры)",
        "slug": "retro-rpg",
        "parent": "Старые игры",
        "is_retro": True,
    },
    "649": {
        "name": "Эротические игры (Старые Игры)",
        "slug": "retro-erotic",
        "parent": "Старые игры",
        "is_retro": True,
    },
}


def is_subforum_allowed(subforum_id: str | int) -> bool:
    """Проверяет, разрешён ли подраздел для парсинга."""
    fid = str(subforum_id).strip()
    if fid in EXCLUDED_SUBFORUM_IDS:
        return False
    return fid in SUBFORUMS


def get_subforum_info(subforum_id: str | int) -> dict:
    """Возвращает информацию о подразделе или дефолтные значения."""
    fid = str(subforum_id).strip()
    if fid in SUBFORUMS:
        info = SUBFORUMS[fid].copy()
        info["id"] = fid
        return info
    return {
        "id": fid,
        "name": f"Подраздел {fid}",
        "slug": f"subforum-{fid}",
        "parent": None,
        "is_retro": False,
    }


def get_all_allowed_subforums() -> list[dict]:
    """Возвращает список всех разрешённых подразделов с их ID и метаданными."""
    return [get_subforum_info(fid) for fid in SUBFORUMS.keys()]
