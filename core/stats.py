"""Сбор и поддержание актуальности статистики раздач (сиды, пиры, скачивания),
а также постраничный сбор исторической базы через поисковые запросы tracker.php.
"""
import json
import os
import re
import time
from bs4 import BeautifulSoup

from config.subforums import (
    is_subforum_allowed,
    get_subforum_info,
    EXCLUDED_SUBFORUM_IDS,
    SUBFORUMS,
)
from core.filter import (
    is_portable,
    is_allowed_size,
    clean_game_title,
    extract_size_from_title,
    parse_size_to_bytes,
    MAX_SIZE_GB,
)
from core.network import fetch_url, BASE_URL
from core.storage import STATS_FILE, GAMES_FILE, SUBFORUMS_FILE, load_json, save_json, update_subforums_catalog

MONTH_MAP = {
    'янв': '01', 'фев': '02', 'мар': '03', 'апр': '04',
    'май': '05', 'мая': '05', 'июн': '06', 'июл': '07',
    'авг': '08', 'сен': '09', 'окт': '10', 'ноя': '11', 'дек': '12'
}


def normalize_rutracker_date(dt_str: str) -> str:
    """Нормализует дату вида '15-Сен-26 14:20' в формат 'YYYY-MM-DD HH:MM:SS'."""
    if not dt_str:
        return ""
    dt_str = dt_str.strip()
    m = re.match(r'(\d{1,2})-([А-Яа-яA-Za-z]+)-(\d{2,4})(?:\s+(\d{1,2}):(\d{2}))?', dt_str)
    if not m:
        return dt_str
    day, month_str, year, hour, minute = m.groups()
    month = MONTH_MAP.get(month_str.lower()[:3], '01')
    if len(year) == 2:
        year = f"20{year}"
    hour = hour or '00'
    minute = minute or '00'
    return f"{year}-{month}-{int(day):02d} {int(hour):02d}:{int(minute):02d}:00"


def parse_tracker_page(html: str,
                       filter_portable_flag: bool = True,
                       max_size_gb: float = MAX_SIZE_GB) -> list[dict]:
    """Парсит страницу выдачи tracker.php.

    Извлекает как статистику (сиды, пиры, скачивания), так и полные данные тем
    (название, размер, подраздел, ссылку) для исторического наполнения каталога.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    results = []

    rows = soup.select('#tor-tbl tr[id^="trs-tr-"]') or soup.select('tr.hl-tr')

    for row in rows:
        # 1. Topic ID
        topic_id = None
        link = row.select_one('a[data-topic_id]')
        if link and link.get('data-topic_id'):
            topic_id = link['data-topic_id'].strip()
        else:
            link = row.select_one('a.tt-text, a[href*="viewtopic.php?t="]')
            if link and link.get('href'):
                m = re.search(r't=(\d+)', link['href'])
                if m:
                    topic_id = m.group(1)

        if not topic_id:
            continue

        # 2. Название темы
        title_tag = row.select_one('a.tt-text') or link
        raw_title = title_tag.get_text(strip=True) if title_tag else ''

        if filter_portable_flag and not is_portable(raw_title):
            continue

        # 3. Подраздел темы из колонки форума
        subforum_id = "Unknown"
        subforum_name = "Unknown"
        subforum_slug = "unknown"

        forum_link = row.select_one('.f-name a, a[href*="tracker.php?f="], a[href*="viewforum.php?f="]')
        if forum_link:
            fm = re.search(r'f=(\d+)', forum_link.get('href', ''))
            if fm:
                subforum_id = fm.group(1)
                if subforum_id in EXCLUDED_SUBFORUM_IDS:
                    continue
                sf_info = get_subforum_info(subforum_id)
                subforum_name = sf_info.get("name", forum_link.get_text(strip=True))
                subforum_slug = sf_info.get("slug", f"subforum-{subforum_id}")

        # 4. Размер
        size_str = "Unknown"
        size_bytes = None
        size_td = row.select_one('td.tor-size, a.f-dl, td[class*="size"]')
        if size_td:
            size_str = size_td.get_text(' ', strip=True).replace('\xa0', ' ').strip()
            ts_bytes = size_td.get('data-ts_text')
            if ts_bytes and ts_bytes.isdigit():
                size_bytes = int(ts_bytes)
        if not size_str or size_str == "Unknown":
            size_str = extract_size_from_title(raw_title) or "Unknown"

        if size_str != "Unknown" and not is_allowed_size(size_str, max_size_gb):
            continue

        if size_bytes is None and size_str != "Unknown":
            size_bytes = parse_size_to_bytes(size_str)

        # 5. Leeches
        leeches = 0
        leech_td = row.select_one('td.leechmed, span.leechmed, u.leechmed, td[class*="leech"]')
        if leech_td:
            m = re.search(r'\d+', leech_td.get_text(strip=True))
            if m:
                leeches = int(m.group(0))

        # 6. Seeds
        seeds = 0
        seed_td = None
        if leech_td and leech_td.name == 'td':
            seed_td = leech_td.find_previous_sibling('td')
        elif leech_td:
            parent_td = leech_td.find_parent('td')
            if parent_td:
                seed_td = parent_td.find_previous_sibling('td')

        if not seed_td:
            seed_td = row.select_one('td.seedmed, b.seedmed, span.seedmed, td[class*="seed"]')

        if seed_td:
            m = re.search(r'\d+', seed_td.get_text(strip=True))
            if m:
                seeds = int(m.group(0))

        # 7. Downloads
        downloads = 0
        dl_td = None
        if leech_td and leech_td.name == 'td':
            dl_td = leech_td.find_next_sibling('td')
        elif leech_td:
            parent_td = leech_td.find_parent('td')
            if parent_td:
                dl_td = parent_td.find_next_sibling('td')

        if dl_td:
            m = re.search(r'[\d,]+', dl_td.get_text(strip=True).replace(' ', ''))
            if m:
                downloads = int(m.group(0).replace(',', ''))

        # 8. Дата регистрации
        registered_at = ""
        tds = row.find_all('td')
        if tds:
            last_td = tds[-1]
            ts_val = last_td.get('data-ts_text')
            if ts_val and ts_val.isdigit() and len(ts_val) >= 9:
                import datetime
                try:
                    registered_at = datetime.datetime.fromtimestamp(int(ts_val)).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass
            if not registered_at:
                registered_at = normalize_rutracker_date(last_td.get_text(strip=True))

        clean_t = clean_game_title(raw_title)

        results.append({
            "topic_id": str(topic_id),
            "title": clean_t,
            "raw_title": raw_title,
            "size": size_str,
            "size_bytes": size_bytes,
            "subforum_id": subforum_id,
            "subforum": subforum_name,
            "subforum_slug": subforum_slug,
            "url": f"{BASE_URL}viewtopic.php?t={topic_id}",
            "is_portable": True,
            "seeds": seeds,
            "leeches": leeches,
            "downloads": downloads,
            "registered_at": registered_at
        })

    return results


def parse_topic_stats(html: str) -> dict:
    """Извлекает статистику из страницы темы viewtopic.php."""
    stats = {"seeds": 0, "leeches": 0, "downloads": 0, "registered_at": ""}
    if not html:
        return stats

    soup = BeautifulSoup(html, 'html.parser')

    # Сиды: <span class="seed"><b>45</b></span>
    seed_el = soup.select_one('.seed b, span.seed, .seedmed b, span.seedmed')
    if seed_el:
        m = re.search(r'\d+', seed_el.get_text(strip=True))
        if m:
            stats['seeds'] = int(m.group(0))

    # Личи: <span class="leech"><b>3</b></span>
    leech_el = soup.select_one('.leech b, span.leech, .leechmed b, span.leechmed')
    if leech_el:
        m = re.search(r'\d+', leech_el.get_text(strip=True))
        if m:
            stats['leeches'] = int(m.group(0))

    # Скачивания и дата регистрации
    for td in soup.find_all(['td', 'span', 'li']):
        txt = td.get_text(strip=True)
        if 'Скачан' in txt and 'раз' in txt:
            m = re.search(r'(\d[\d\s]*)\s*раз', txt)
            if m:
                stats['downloads'] = int(m.group(1).replace(' ', ''))
        if 'Зарегистрирован' in txt:
            val = txt.replace('Зарегистрирован:', '').strip()
            if val and len(val) < 40:
                stats['registered_at'] = normalize_rutracker_date(val)

    return stats


def crawl_tracker_portable(subforum_id: str | None = None,
                           max_pages: int | None = None,
                           max_size_gb: float = MAX_SIZE_GB) -> tuple[list[dict], dict]:
    """Постраничный обход tracker.php?f[]=...&nm=portable для сбора всей исторической базы.

    Возвращает:
      (games_list, stats_dict)
    """
    if subforum_id:
        base_url = f"{BASE_URL}tracker.php?f[]={subforum_id}&nm=portable&o=1&s=1"
    else:
        # Все разрешенные подразделы f=5 (Игры для Windows)
        sub_params = "&".join(f"f[]={sid}" for sid in SUBFORUMS.keys())
        base_url = f"{BASE_URL}tracker.php?{sub_params}&nm=portable&o=1&s=1"

    now_str = time.strftime('%Y-%m-%d %H:%M:%S')
    games_found = []
    stats_found = {}
    seen_ids = set()

    page = 0
    print(f"[*] Поиск исторических раздач через tracker.php ({base_url})...")

    while True:
        if max_pages is not None and page >= max_pages:
            print(f"[*] Достигнут лимит страниц ({max_pages}).")
            break

        start = page * 50
        tracker_url = f"{base_url}&start={start}"

        html = fetch_url(tracker_url, forum_url=True, wait_keywords=('tor-tbl', 'hl-tr', 'tracker'))
        if not html:
            print(f"[!] Страница {page + 1} tracker.php не загружена.")
            break

        if 'не найдено' in html.lower() or 'not found' in html.lower():
            print(f"[*] Поиск завершён (результаты закончились на странице {page + 1}).")
            break

        if 'login_username' in html:
            print("[!] tracker.php требует авторизации. Укажите RUTRACKER_COOKIES (bb_session, bb_guid) в .env.")
            break

        soup = BeautifulSoup(html, 'html.parser')
        raw_rows = soup.select('#tor-tbl tr[id^="trs-tr-"]') or soup.select('tr.hl-tr')
        if not raw_rows:
            print(f"[*] Поиск завершён (нет раздач в таблице на странице {page + 1}).")
            break

        entries = parse_tracker_page(html, filter_portable_flag=True, max_size_gb=max_size_gb)

        new_on_page = 0
        for entry in entries:
            tid = entry["topic_id"]
            if tid not in seen_ids:
                seen_ids.add(tid)
                games_found.append({
                    "topic_id": tid,
                    "title": entry["title"],
                    "raw_title": entry["raw_title"],
                    "size": entry["size"],
                    "size_bytes": entry["size_bytes"],
                    "subforum_id": entry["subforum_id"],
                    "subforum": entry["subforum"],
                    "subforum_slug": entry["subforum_slug"],
                    "url": entry["url"],
                    "is_portable": True,
                    "magnet": None,  # Добирается через enrich
                })
                stats_found[tid] = {
                    "seeds": entry["seeds"],
                    "leeches": entry["leeches"],
                    "downloads": entry["downloads"],
                    "registered_at": entry["registered_at"],
                    "updated_at": now_str
                }
                new_on_page += 1

        print(f"  Страница {page + 1}: строк в таблице {len(raw_rows)}, подошло {len(entries)} (новых: {new_on_page}, всего в поиске: {len(games_found)})")

        # Промежуточное сохранение каждые 5 страниц
        if (page + 1) % 5 == 0:
            cur_data = load_json(GAMES_FILE) or []
            cur_map = {str(item["topic_id"]): item for item in cur_data if item.get("topic_id")}
            for g in games_found:
                gtid = str(g["topic_id"])
                if gtid not in cur_map:
                    cur_data.append(g)
                    cur_map[gtid] = g
            save_json(cur_data, GAMES_FILE)
            update_subforums_catalog(cur_data, SUBFORUMS_FILE)

        if len(raw_rows) < 50:
            print(f"[*] Достигнута последняя страница ({len(raw_rows)} строк).")
            break

        page += 1
        time.sleep(0.5)

    return games_found, stats_found


def scrape_torrents_stats(output_file: str = STATS_FILE,
                          games_file: str = GAMES_FILE,
                          limit: int = 200) -> dict:
    """Поддержание актуальности статистики торрентов для игр из базы."""
    stats_data = load_json(output_file) or {}
    games_data = load_json(games_file) or []

    if not games_data:
        print("[*] База pc_games.json пуста, сбор статистики пропущен.")
        return stats_data

    print(f"[*] Сбор статистики раздач (всего игр: {len(games_data)}, лимит обхода: {limit})...")
    now_str = time.strftime('%Y-%m-%d %H:%M:%S')

    candidates = []
    for g in games_data:
        tid = str(g.get("topic_id", ""))
        if not tid:
            continue
        cur_stat = stats_data.get(tid)
        if not cur_stat:
            candidates.append((tid, 0))
        else:
            updated_ts = cur_stat.get("updated_at", "")
            candidates.append((tid, 1 if updated_ts else 0))

    candidates.sort(key=lambda x: x[1])
    to_check = [c[0] for c in candidates[:limit]]

    updated_count = 0
    for idx, tid in enumerate(to_check, 1):
        url = f"{BASE_URL}viewtopic.php?t={tid}"
        html = fetch_url(url, forum_url=False)
        if html:
            st = parse_topic_stats(html)
            stats_data[tid] = {
                "seeds": st["seeds"],
                "leeches": st["leeches"],
                "downloads": st["downloads"],
                "registered_at": st["registered_at"] or (stats_data.get(tid, {}).get("registered_at", "")),
                "updated_at": now_str,
            }
            updated_count += 1
            if idx % 10 == 0 or idx == len(to_check):
                print(f"  [{idx}/{len(to_check)}] Тема {tid}: {st['seeds']} сид., {st['leeches']} лич., {st['downloads']} скач.")
                save_json(stats_data, output_file)
        time.sleep(0.3)

    save_json(stats_data, output_file)
    print(f"[+] Статистика обновлена для {updated_count} раздач.")
    return stats_data
