"""Главный CLI-парсер PC-игр (Windows) с RuTracker.

Парсит подразделы форума f=5 (Игры для Windows):
- Исключает подразделы: f=1151, f=2228, f=68 и служебные темы
- Фильтрует только версии [portable]
- Ограничивает размер: не больше 60 ГБ
- Сохраняет принадлежность к подразделу (subforum_id, subforum, subforum_slug)
- Генерирует каталог подразделов data/subforums.json
- Сохраняет базу в data/pc_games.json и статистику в data/pc_games_stats.json
"""
import argparse
import os
import sys
import time

# Принудительно UTF-8 для консоли Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from config.subforums import (
    SUBFORUMS,
    is_subforum_allowed,
    get_subforum_info,
)
from core.filter import (
    is_portable,
    is_allowed_size,
    clean_game_title,
    MAX_SIZE_GB,
)
from core.atom import fetch_subforum_feed
from core.forum import scrape_forum_page, get_forum_max_pages
from core.topic_parser import get_topic_data, merge_topic_details
from core.storage import (
    load_json,
    save_json,
    update_subforums_catalog,
    enrich_incomplete,
    write_changes_log,
    GAMES_FILE,
    STATS_FILE,
    SUBFORUMS_FILE,
)
from core.stats import crawl_tracker_portable, scrape_torrents_stats
from core.network import close_driver


def run_incremental_scan(existing_data: list[dict],
                         target_subforums: list[str],
                         max_size_gb: float = MAX_SIZE_GB) -> tuple[list[dict], list[dict], list[dict]]:
    """Ежедневный инкрементальный сбор через Atom-ленты подразделов."""
    existing_map = {str(item["topic_id"]): item for item in existing_data if item.get("topic_id")}
    added = []
    updated = []

    print(f"[*] Инкрементальный опрос Atom-лент ({len(target_subforums)} подразделов)...")

    for fid in target_subforums:
        info = get_subforum_info(fid)
        name = info["name"]
        feed_entries = fetch_subforum_feed(fid, filter_portable=True, max_size_gb=max_size_gb)

        sub_added = 0
        sub_updated = 0

        for entry in feed_entries:
            tid = str(entry["topic_id"])
            if tid not in existing_map:
                # Новая раздача
                existing_data.insert(0, entry)
                existing_map[tid] = entry
                added.append(entry)
                sub_added += 1
            else:
                # Уже известная раздача — проверяем возможное обновление magnet / названия
                item = existing_map[tid]
                changed = False
                if entry.get("magnet") and entry["magnet"] != item.get("magnet"):
                    item["magnet"] = entry["magnet"]
                    changed = True
                if entry.get("size") and entry["size"] != "Unknown" and entry["size"] != item.get("size"):
                    item["size"] = entry["size"]
                    item["size_bytes"] = entry.get("size_bytes")
                    changed = True
                if changed:
                    item["updated_at"] = entry.get("updated_at") or time.strftime('%Y-%m-%d %H:%M:%S')
                    updated.append(item)
                    sub_updated += 1

        print(f"  [+] f={fid:4s} ({name:35s}): найдено {len(feed_entries):2d} portable (новых: {sub_added}, обновлено: {sub_updated})")

    return existing_data, added, updated


def run_full_scan(existing_data: list[dict],
                  target_subforums: list[str],
                  max_pages: int | None = None,
                  max_size_gb: float = MAX_SIZE_GB) -> tuple[list[dict], list[dict], list[dict]]:
    """Полный постраничный обход viewforum.php для выбранных подразделов."""
    existing_map = {str(item["topic_id"]): item for item in existing_data if item.get("topic_id")}
    added = []
    updated = []

    print(f"[*] Запуск полного обхода подразделов ({len(target_subforums)} шт.)...")

    for fid in target_subforums:
        info = get_subforum_info(fid)
        name = info["name"]
        print(f"\n=======================================================")
        print(f"[*] Подраздел f={fid}: {name}")
        print(f"=======================================================")

        page = 0
        while True:
            if max_pages is not None and page >= max_pages:
                print(f"[*] Достигнут лимит страниц ({max_pages}) для f={fid}.")
                break

            topics = scrape_forum_page(fid, page_num=page, filter_portable=True, max_size_gb=max_size_gb)
            if not topics:
                print(f"[*] Нет тем на странице {page + 1} f={fid}, переход к следующему подразделу.")
                break

            page_added = 0
            for t in topics:
                tid = str(t["topic_id"])
                if tid not in existing_map:
                    # Добавляем базовую запись (magnet и детали доберутся при enrich)
                    existing_data.append(t)
                    existing_map[tid] = t
                    added.append(t)
                    page_added += 1

            print(f"  Страница {page + 1}: обработано {len(topics)} portable-тем, новых в базе: {page_added}")

            # Сохраняем промежуточный результат каждые 2 страницы
            if (page + 1) % 2 == 0:
                save_json(existing_data, GAMES_FILE)

            page += 1
            time.sleep(0.5)

    return existing_data, added, updated


def main():
    parser = argparse.ArgumentParser(description="Парсер раздач PC-игр [portable] с RuTracker (f=5)")
    parser.add_argument("--full", action="store_true", help="Полный постраничный обход всех подразделов форума")
    parser.add_argument("--subforum", type=str, default=None, help="Обработать только один подраздел (по ID)")
    parser.add_argument("--max-pages", type=int, default=None, help="Максимальное количество страниц при --full")
    parser.add_argument("--enrich-only", action="store_true", help="Только дообогащение метаданных (обложки, скриншоты, описание)")
    parser.add_argument("--enrich-limit", type=int, default=100, help="Количество раздач для дообогащения (по умолчанию: 100)")
    parser.add_argument("--skip-enrich", action="store_true", help="Пропустить этап дообогащения метаданных")
    parser.add_argument("--tracker-search", action="store_true", help="Сбор всех исторических раздач через поиск tracker.php?nm=portable")
    parser.add_argument("--tracker-pages", type=int, default=None, help="Максимальное количество страниц при --tracker-search")
    parser.add_argument("--stats-only", action="store_true", help="Только сбор статистики торрентов (сиды, пиры, скачивания)")
    parser.add_argument("--skip-stats", action="store_true", help="Пропустить сбор статистики раздач")
    parser.add_argument("--stats-limit", type=int, default=200, help="Лимит обхода для статистики (по умолчанию: 200)")
    parser.add_argument("--max-size", type=float, default=MAX_SIZE_GB, help="Максимальный размер игры в ГБ (по умолчанию: 60.0)")

    args = parser.parse_args()

    # Загружаем существующую базу
    existing_data = load_json(GAMES_FILE) or []
    print(f"[*] Загружена база pc_games.json: {len(existing_data)} раздач.")

    # 1. Режим только сбора статистики
    if args.stats_only:
        scrape_torrents_stats(STATS_FILE, GAMES_FILE, limit=args.stats_limit)
        return

    # 1.5 Режим исторического сбора через tracker.php?nm=portable
    if args.tracker_search:
        if args.subforum:
            fid = str(args.subforum).strip()
            if not is_subforum_allowed(fid):
                print(f"[!] Ошибка: подраздел f={fid} запрещён или находится в черном списке.")
                sys.exit(1)
            target_subforums = [fid]
        else:
            target_subforums = list(SUBFORUMS.keys())

        existing_map = {str(item["topic_id"]): item for item in existing_data if item.get("topic_id")}
        existing_stats = load_json(STATS_FILE) or {}
        added = []
        updated_count = 0

        for fid in target_subforums:
            sf_info = get_subforum_info(fid)
            print(f"\n[*] Сбор подраздела f={fid} ({sf_info['name']})...")
            t_games, t_stats = crawl_tracker_portable(
                subforum_id=fid,
                max_pages=args.tracker_pages,
                max_size_gb=args.max_size
            )
            for g in t_games:
                tid = str(g["topic_id"])
                if tid not in existing_map:
                    existing_data.append(g)
                    existing_map[tid] = g
                    added.append(g)
                else:
                    item = existing_map[tid]
                    changed = False
                    if g.get("subforum_id") and g["subforum_id"] != "Unknown" and item.get("subforum_id") in (None, "Unknown"):
                        item["subforum_id"] = g["subforum_id"]
                        item["subforum"] = g["subforum"]
                        item["subforum_slug"] = g["subforum_slug"]
                        changed = True
                    if g.get("size_bytes") and not item.get("size_bytes"):
                        item["size_bytes"] = g["size_bytes"]
                        changed = True
                    if changed:
                        updated_count += 1
            existing_stats.update(t_stats)

        save_json(existing_stats, STATS_FILE)
        save_json(existing_data, GAMES_FILE)
        subforums_cat = update_subforums_catalog(existing_data, SUBFORUMS_FILE)
        write_changes_log(added, [], 0, len(existing_data))
        print(f"[+] Сбор через tracker.php завершён: добавлено {len(added)} новых игр (обновлено {updated_count}), всего в базе: {len(existing_data)}")
        close_driver()
        return

    # 2. Режим только дообогащения
    if args.enrich_only:
        enriched = enrich_incomplete(existing_data, limit=args.enrich_limit)
        if enriched > 0:
            save_json(existing_data, GAMES_FILE)
            update_subforums_catalog(existing_data, SUBFORUMS_FILE)
            write_changes_log([], [], enriched, len(existing_data))
        return

    # Определение целевых подразделов
    if args.subforum:
        fid = str(args.subforum).strip()
        if not is_subforum_allowed(fid):
            print(f"[!] Ошибка: подраздел f={fid} запрещён или находится в черном списке.")
            sys.exit(1)
        target_subforums = [fid]
    else:
        target_subforums = list(SUBFORUMS.keys())

    # Сбор данных: Полный или инкрементальный
    if args.full:
        games_data, added, updated = run_full_scan(
            existing_data, target_subforums,
            max_pages=args.max_pages, max_size_gb=args.max_size
        )
    else:
        games_data, added, updated = run_incremental_scan(
            existing_data, target_subforums,
            max_size_gb=args.max_size
        )

    # Дообогащение метаданных (обложки, скриншоты, описания)
    enriched_count = 0
    if not args.skip_enrich and games_data:
        enriched_count = enrich_incomplete(games_data, limit=args.enrich_limit)

    # Сохранение базы игр и каталога подразделов
    save_json(games_data, GAMES_FILE)
    print(f"[+] База сохранена в {GAMES_FILE}: {len(games_data)} раздач.")

    subforums_cat = update_subforums_catalog(games_data, SUBFORUMS_FILE)
    print(f"[+] Каталог подразделов сохранён в {SUBFORUMS_FILE}: {len(subforums_cat)} подразделов.")

    # Запись лога изменений
    write_changes_log(added, updated, enriched_count, len(games_data))

    # Сбор статистики раздач
    if not args.skip_stats and games_data:
        scrape_torrents_stats(STATS_FILE, GAMES_FILE, limit=args.stats_limit)

    close_driver()
    print("[*] Работа парсера успешно завершена.")


if __name__ == '__main__':
    main()
