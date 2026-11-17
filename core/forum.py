"""Парсинг страниц форума RuTracker (viewforum.php) для полного обхода подразделов."""
import re
from bs4 import BeautifulSoup

from config.subforums import (
    is_subforum_allowed,
    get_subforum_info,
)
from core.filter import (
    is_portable,
    is_allowed_size,
    extract_size_from_title,
    parse_size_to_bytes,
    clean_game_title,
    MAX_SIZE_GB,
)
from core.network import fetch_url, BASE_URL


def is_sticky_topic(row) -> bool:
    """Определяет, является ли строка объявлением или закреплённой темой."""
    # 1. Проверяем иконку темы (td.topic_icon)
    icon_td = row.select_one('td.topic_icon, td.t-ico')
    if icon_td:
        img = icon_td.find('img')
        if img:
            src = img.get('src', '').lower()
            if any(m in src for m in ('announce', 'sticky', 'folder_announce', 'folder_sticky')):
                return True

    # 2. Проверяем класс строки
    classes = row.get('class', [])
    if any('sticky' in c.lower() or 'announce' in c.lower() for c in classes):
        return True

    # 3. Проверяем ключевые слова в названии
    link = row.select_one('a.tt-text')
    if link:
        txt = link.get_text().strip().lower()
        if any(kw in txt for kw in (
            'правила раздела', 'навигатор по разделу', 'список раздач раздела',
            'важная информация', 'поиск и заказ игр', 'правила подраздела', 'faq'
        )):
            return True

    return False


def get_forum_max_pages(html) -> int:
    """Определяет количество страниц в подразделе из блока пагинации."""
    if not html:
        return 1
    soup = BeautifulSoup(html, 'html.parser')
    pg_div = soup.select_one('.bottom_info .nav, #pagination, .pg')
    if not pg_div:
        return 1

    max_p = 1
    for a in pg_div.find_all('a', href=re.compile(r'start=(\d+)')):
        m = re.search(r'start=(\d+)', a['href'])
        if m:
            start_val = int(m.group(1))
            page_num = (start_val // 50) + 1
            if page_num > max_p:
                max_p = page_num

    # Также проверяем обычные текстовые номера страниц
    for b in pg_div.find_all(['b', 'span', 'p']):
        txt = b.get_text().strip()
        if txt.isdigit() and int(txt) > max_p:
            max_p = int(txt)

    return max_p


def scrape_forum_page(subforum_id: str | int,
                       page_num: int = 0,
                       filter_portable: bool = True,
                       max_size_gb: float = MAX_SIZE_GB) -> list[dict]:
    """Загружает страницу подраздела и возвращает отфильтрованные темы.

    Возвращает:
        list of dict: [{"topic_id", "title", "raw_title", "size", "size_bytes",
                        "subforum_id", "subforum", "subforum_slug", "url"}, ...]
    """
    fid = str(subforum_id).strip()
    if not is_subforum_allowed(fid):
        print(f"[!] Подраздел f={fid} исключён или не разрешён.")
        return []

    sf_info = get_subforum_info(fid)
    subforum_name = sf_info.get("name", f"Подраздел {fid}")
    subforum_slug = sf_info.get("slug", f"subforum-{fid}")

    start = page_num * 50
    forum_url = f"{BASE_URL}viewforum.php?f={fid}&start={start}"

    html = fetch_url(forum_url, forum_url=True)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    table = soup.select_one('table.vf-table, table.forumline') or soup
    rows = table.find_all('tr', recursive=False) or table.select('tr')
    if not rows:
        return []

    topics = []

    # Разделитель "Темы" для пропуска объявлений на 1-й странице
    has_temy_separator = any(
        len(r.find_all('td', recursive=False)) == 1 and 'Темы' in r.text
        for r in rows
    )
    in_regular_topics = (page_num > 0) or (not has_temy_separator)

    for row in rows:
        tds = row.find_all('td', recursive=False)
        if len(tds) == 1:
            sep_text = tds[0].text.strip()
            if 'Темы' in sep_text:
                in_regular_topics = True
                continue
            elif not in_regular_topics:
                continue

        link_tag = row.select_one('a.tt-text')
        if not link_tag:
            continue

        raw_title = link_tag.get_text().strip()
        topic_url = link_tag.get('href', '')
        if not topic_url.startswith('http'):
            topic_url = f"{BASE_URL}{topic_url.lstrip('/')}"

        m = re.search(r't=(\d+)', topic_url)
        if not m:
            continue
        topic_id = m.group(1)

        dl_link = row.select_one('a.f-dl, a[href^="dl.php?t="]')
        is_sticky_row = not in_regular_topics

        if is_sticky_row:
            if not dl_link or is_sticky_topic(row):
                continue

        # 1. Фильтр Portable
        if filter_portable and not is_portable(raw_title):
            continue

        # 2. Размер из колонки форума или из заголовка
        size_str = None
        size_td = row.select_one('td.tor-size, td.t-tor-size')
        if size_td:
            size_str = size_td.get_text(' ', strip=True).replace('\xa0', ' ').strip()
        if not size_str or size_str == 'Unknown':
            size_str = extract_size_from_title(raw_title) or "Unknown"

        if size_str != "Unknown" and not is_allowed_size(size_str, max_size_gb):
            continue

        size_bytes = parse_size_to_bytes(size_str) if size_str != "Unknown" else None
        clean_title = clean_game_title(raw_title)

        topics.append({
            "topic_id": topic_id,
            "title": clean_title,
            "raw_title": raw_title,
            "size": size_str,
            "size_bytes": size_bytes,
            "subforum_id": fid,
            "subforum": subforum_name,
            "subforum_slug": subforum_slug,
            "url": topic_url,
            "is_portable": True,
            "magnet": None,
        })

    return topics
