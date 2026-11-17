"""Управление хранилищем данных (JSON), дообогащение и логирование изменений."""
import json
import os
import tempfile
import time

from config.subforums import SUBFORUMS, get_subforum_info
from core.topic_parser import get_topic_data, merge_topic_details

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

GAMES_FILE = os.path.join(DATA_DIR, 'pc_games.json')
STATS_FILE = os.path.join(DATA_DIR, 'pc_games_stats.json')
SUBFORUMS_FILE = os.path.join(DATA_DIR, 'subforums.json')
CHANGES_FILE = os.path.join(BASE_DIR, 'changes.txt')
ENRICH_STATE_FILE = os.path.join(BASE_DIR, 'enrich_state.json')

# Поля, которые должны быть дообогащены со страницы темы
METADATA_FIELDS = (
    'cover', 'screenshots', 'description', 'year', 'genre',
    'developer', 'publisher', 'version', 'edition_type',
    'release_type', 'interface_lang', 'voice_lang', 'source', 'magnet'
)


def load_json(filepath: str) -> list | dict:
    """Загружает базу данных из JSON файла."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    except Exception as e:
        print(f"[!] Ошибка чтения {filepath}: {e}")
    return []


def save_json(data, filepath: str) -> None:
    """Атомарное сохранение JSON файла через временный файл."""
    try:
        target_dir = os.path.dirname(filepath) or '.'
        os.makedirs(target_dir, exist_ok=True)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=target_dir, suffix='.tmp')
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)
    except Exception as e:
        print(f"[!] Ошибка записи {filepath}: {e}")


def update_subforums_catalog(games_data: list[dict], filepath: str = SUBFORUMS_FILE) -> list[dict]:
    """Формирует каталог подразделов с актуальным количеством игр в каждом.

    Сохраняет результат в data/subforums.json для использования в клиентском UI.
    """
    counts = {}
    for g in games_data:
        fid = str(g.get("subforum_id", "")).strip()
        if fid:
            counts[fid] = counts.get(fid, 0) + 1

    catalog = []
    for fid, info in SUBFORUMS.items():
        catalog.append({
            "id": fid,
            "name": info["name"],
            "slug": info["slug"],
            "parent": info["parent"],
            "is_retro": info["is_retro"],
            "games_count": counts.get(fid, 0),
        })

    # Сортируем: сначала современные по алфавиту/родителям, затем ретро
    catalog.sort(key=lambda x: (x["is_retro"], x["parent"] or "", x["name"]))
    save_json(catalog, filepath)
    return catalog


def load_enrich_state() -> dict:
    """Загрузка состояния дообогащения."""
    try:
        if os.path.exists(ENRICH_STATE_FILE):
            with open(ENRICH_STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_enrich_state(state: dict) -> None:
    """Сохранение состояния дообогащения."""
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=BASE_DIR, suffix='.tmp')
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, ENRICH_STATE_FILE)
    except Exception as e:
        print(f"[!] Ошибка сохранения enrich_state: {e}")


def enrich_incomplete(games_data: list[dict], limit: int = 100, save_interval: int = 20) -> int:
    """Дообогащает метаданными раздачи, у которых отсутствуют обложка/описание.

    Возвращает количество успешно обновлённых записей.
    """
    state = load_enrich_state()
    now = time.time()
    one_week = 7 * 86400

    def _is_incomplete(item):
        missing = [
            k for k in METADATA_FIELDS
            if not item.get(k) or item.get(k) in ('Unknown', '', None)
            or (k == 'screenshots' and not item.get(k))
        ]
        return missing

    candidates = []
    for item in games_data:
        tid = str(item.get('topic_id', ''))
        if not tid:
            continue
        missing = _is_incomplete(item)
        if not missing:
            continue

        last_attempt = state.get(tid, 0)
        if now - last_attempt < one_week:
            continue

        candidates.append((item, missing))
        if len(candidates) >= limit:
            break

    if not candidates:
        print("[*] Нет раздач, требующих дообогащения (или все проверены недавно).")
        return 0

    print(f"[*] Дообогащение метаданных для {len(candidates)} раздач...")
    enriched_count = 0

    for idx, (item, missing) in enumerate(candidates, 1):
        tid = str(item['topic_id'])
        print(f"  [{idx}/{len(candidates)}] Тема {tid} (не хватает: {', '.join(missing[:3])})...")
        details = get_topic_data(tid)
        state[tid] = now

        if details and (details.get('cover') or details.get('description')):
            merge_topic_details(item, details)
            enriched_count += 1
            print(f"    [+] Дообогащено: обложка={'есть' if item.get('cover') else 'нет'}, скриншотов={len(item.get('screenshots', []))}")
        else:
            print("    [-] Данные на странице не найдены.")

        if enriched_count > 0 and enriched_count % save_interval == 0:
            save_json(games_data, GAMES_FILE)
            save_enrich_state(state)

        time.sleep(0.3)

    save_enrich_state(state)
    save_json(games_data, GAMES_FILE)
    return enriched_count


def write_changes_log(added: list[dict],
                      updated: list[dict],
                      enriched: int,
                      total: int,
                      output_file: str = CHANGES_FILE) -> None:
    """Записывает лог изменений последнего запуска в changes.txt."""
    now_str = time.strftime('%Y-%m-%d %H:%M:%S')
    lines = [
        f"=== Изменения базы pc-games: {now_str} ===",
        f"Всего игр в базе: {total}",
        f"Добавлено новых: {len(added)}",
        f"Обновлено раздач: {len(updated)}",
        f"Дообогащено метаданными: {enriched}",
        ""
    ]

    if added:
        lines.append("--- Новые раздачи [portable] ---")
        for g in added[:30]:
            lines.append(f"  + [{g.get('subforum', 'N/A')}] {g.get('title', 'Unknown')} ({g.get('size', 'Unknown')}) - t={g.get('topic_id')}")
        if len(added) > 30:
            lines.append(f"  ... и ещё {len(added) - 30} раздач")
        lines.append("")

    if updated:
        lines.append("--- Обновлённые раздачи ---")
        for g in updated[:30]:
            lines.append(f"  ~ [{g.get('subforum', 'N/A')}] {g.get('title', 'Unknown')} ({g.get('size', 'Unknown')}) - t={g.get('topic_id')}")
        if len(updated) > 30:
            lines.append(f"  ... и ещё {len(updated) - 30} раздач")
        lines.append("")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"[+] Лог изменений записан в {output_file}")
