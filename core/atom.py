"""Парсинг Atom-лент RuTracker для быстрого сбора раздач без блокировок Cloudflare."""
import xml.etree.ElementTree as ET
from curl_cffi import requests as cf_requests

from config.subforums import (
    is_subforum_allowed,
    get_subforum_info,
    SUBFORUMS,
)
from core.filter import (
    is_portable,
    is_allowed_size,
    extract_size_from_title,
    parse_size_to_bytes,
    clean_game_title,
    MAX_SIZE_GB,
)
from core.network import BASE_URL, PROXY_URL

ATOM_BASE_URL = "https://feed.rutracker.cc/atom/f/{subforum_id}.atom"


def fetch_subforum_feed(subforum_id: str | int,
                        filter_portable: bool = True,
                        max_size_gb: float = MAX_SIZE_GB,
                        timeout: int = 15) -> list[dict]:
    """Получает последние раздачи из Atom-ленты подраздела.

    Возвращает только те, которые удовлетворяют критериям:
    - [portable] (если filter_portable=True)
    - размер <= max_size_gb
    - подраздел не в черном списке
    """
    fid = str(subforum_id).strip()
    if not is_subforum_allowed(fid):
        print(f"[!] Подраздел f={fid} исключён или не разрешён.")
        return []

    sf_info = get_subforum_info(fid)
    subforum_name = sf_info.get("name", f"Подраздел {fid}")
    subforum_slug = sf_info.get("slug", f"subforum-{fid}")

    url = ATOM_BASE_URL.format(subforum_id=fid)
    kwargs = {"impersonate": "chrome120", "timeout": timeout}
    if PROXY_URL:
        kwargs["proxies"] = {"http": PROXY_URL, "https": PROXY_URL}

    try:
        resp = cf_requests.get(url, **kwargs)
        if resp.status_code != 200:
            print(f"[!] Atom-лента f={fid} вернула статус {resp.status_code}")
            return []

        root = ET.fromstring(resp.content.decode('utf-8'))
        matching_entries = []

        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            id_elem = entry.find('{http://www.w3.org/2005/Atom}id')
            title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
            updated_elem = entry.find('{http://www.w3.org/2005/Atom}updated')

            if id_elem is None or title_elem is None:
                continue

            raw_title = title_elem.text or ""
            topic_id = str(id_elem.text.split('/')[-1])
            updated_at = updated_elem.text if updated_elem is not None else ""

            # 1. Фильтр Portable
            if filter_portable and not is_portable(raw_title):
                continue

            # 2. Извлечение размера и фильтр <= 60 ГБ
            size_str = extract_size_from_title(raw_title) or "Unknown"
            if size_str != "Unknown" and not is_allowed_size(size_str, max_size_gb):
                continue

            size_bytes = parse_size_to_bytes(size_str) if size_str != "Unknown" else None

            # 3. Извлечение ссылок (веб-ссылка и magnet)
            topic_url = f"{BASE_URL}viewtopic.php?t={topic_id}"
            magnet = None

            for link in entry.findall('{http://www.w3.org/2005/Atom}link'):
                rel = link.attrib.get('rel')
                href = link.attrib.get('href', '')
                if rel == 'enclosure' and href.startswith('magnet:'):
                    magnet = href
                elif not rel and href.startswith('http'):
                    topic_url = href

            clean_title = clean_game_title(raw_title)

            matching_entries.append({
                "topic_id": topic_id,
                "title": clean_title,
                "raw_title": raw_title,
                "size": size_str,
                "size_bytes": size_bytes,
                "subforum_id": fid,
                "subforum": subforum_name,
                "subforum_slug": subforum_slug,
                "magnet": magnet,
                "url": topic_url,
                "is_portable": True,
                "updated_at": updated_at,
            })

        return matching_entries

    except Exception as e:
        print(f"[!] Ошибка получения Atom-ленты f={fid}: {e}")
        return []


def fetch_all_subforums_feeds(filter_portable: bool = True,
                              max_size_gb: float = MAX_SIZE_GB) -> list[dict]:
    """Опрашивает Atom-ленты всех разрешённых подразделов.

    Возвращает общий список найденных portable-игр <= 60 ГБ.
    """
    all_games = []
    seen_ids = set()

    print(f"[*] Опрос Atom-лент всех разрешённых подразделов ({len(SUBFORUMS)} шт.)...")
    for fid, sf_info in SUBFORUMS.items():
        name = sf_info["name"]
        entries = fetch_subforum_feed(fid, filter_portable=filter_portable, max_size_gb=max_size_gb)
        new_count = 0
        for entry in entries:
            tid = entry["topic_id"]
            if tid not in seen_ids:
                seen_ids.add(tid)
                all_games.append(entry)
                new_count += 1
        print(f"  [+] f={fid:4s} ({name:35s}): найдено {len(entries):2d} portable, новых: {new_count:2d}")

    print(f"[*] Всего собрано из Atom-лент: {len(all_games)} уникальных раздач.")
    return all_games
