"""Парсинг тем раздач RuTracker (viewtopic.php) и извлечение детальных метаданных."""
import copy
import re
from html import unescape as html_unescape
from bs4 import BeautifulSoup

from core.filter import (
    clean_game_title,
    extract_size_from_title,
    parse_size_to_bytes,
    is_allowed_size,
    MAX_SIZE_GB,
)
from core.network import fetch_url, BASE_URL


def clean_magnet(url: str | None) -> str | None:
    """Очистка magnet-ссылки: декодирование HTML-entities и удаление лишних параметров."""
    if not url:
        return url
    url = html_unescape(url).strip()
    url = re.sub(r'[?&]dn=[^&]*', '', url)
    return url


def get_magnet_btih(url: str | None) -> str:
    """Извлекает infohash (BTIH) из magnet-ссылки (hex40 или base32)."""
    if not url:
        return ""
    m = re.search(r'btih:([A-Fa-f0-9]{40}|[a-zA-Z2-7]{32})', url, re.IGNORECASE)
    return m.group(1).lower() if m else ""


def post_text(post_body) -> str:
    """Извлечение текста поста с сохранением переводов строк без склеивания блоков."""
    if not post_body:
        return ""
    pb = copy.deepcopy(post_body)
    for br in pb.find_all('br'):
        br.replace_with('\n')
    for block in pb.find_all(['div', 'ul', 'ol', 'li', 'tr', 'table']):
        block.insert_before('\n')
        block.insert_after('\n')
    for el in pb.find_all('span', class_='post-b'):
        el.insert_before('\n')
    return pb.get_text()


def clean_version_str(raw: str | None) -> str | None:
    """Очищает строку версии (напр. 'v1.0.3 от 24.10' -> '1.0.3')."""
    if not raw:
        return None
    raw = str(raw).strip().strip('"\'[]()')
    raw = re.sub(r'^(?:v(?:er(?:sion)?)?\.?\s*)', '', raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r'\s*(\+|\[|\().*(?:dlc|upd|update|repack|portable).*$', '', raw, flags=re.IGNORECASE).strip()

    sem_match = re.match(r'^([0-9]+(?:\.[0-9]+)+(?:[a-zA-Z]|b\d+|-rc\d+|-patch\d*)?)', raw)
    if sem_match:
        return sem_match.group(1)

    alt_match = re.match(r'^([0-9]+(?:\.[0-9a-zA-Z]+)+)', raw)
    if alt_match:
        return alt_match.group(1)

    raw = raw.strip('.,;:- \t\r\n[]()\'"')
    if not re.search(r'\d', raw) or len(raw) > 30:
        return None
    return raw if raw else None


def get_topic_data(topic_id: str | int) -> dict:
    """Парсит страницу раздачи viewtopic.php?t={topic_id} и извлекает метаданные."""
    tid = str(topic_id).strip()
    url = f"{BASE_URL}viewtopic.php?t={tid}"

    data = {
        "topic_id": tid,
        "title": "Unknown",
        "raw_title": "",
        "magnet": None,
        "size": "Unknown",
        "size_bytes": None,
        "year": "Unknown",
        "genre": "Unknown",
        "developer": "Unknown",
        "publisher": "Unknown",
        "version": "Unknown",
        "edition_type": "Unknown",
        "release_type": "Portable",
        "interface_lang": "Unknown",
        "voice_lang": "Unknown",
        "source": "Unknown",
        "steam_id": None,
        "steam_url": None,
        "cover": None,
        "cover_standard": None,
        "screenshots": [],
        "description": "",
    }

    html = fetch_url(url, forum_url=False)
    if not html:
        return data

    soup = BeautifulSoup(html, 'html.parser')

    # Проверка наличия post_body (раздача существует и не на премодерации)
    post_body = soup.find('div', class_='post_body')
    if not post_body:
        return data

    # 1. Заголовок темы
    h1 = soup.select_one('h1.maintitle, #topic-title')
    raw_title = h1.get_text().strip() if h1 else ''
    if not raw_title and soup.title:
        raw_title = re.sub(r'\s*::\s*RuTracker\.org.*$', '', soup.title.get_text().strip(), flags=re.IGNORECASE)

    data["raw_title"] = raw_title
    data["title"] = clean_game_title(raw_title)

    # 2. Magnet ссылка
    mag_link = soup.find('a', class_='magnet-link')
    if mag_link and mag_link.get('href'):
        data["magnet"] = clean_magnet(mag_link.get('href'))
    if not data["magnet"]:
        m = re.search(r'(magnet:\?xt=urn:btih:[^\s\"\'<>]+)', html, re.IGNORECASE)
        if m:
            data["magnet"] = clean_magnet(m.group(1))

    # 3. Размер
    size_el = soup.find(id='tor-size-humn')
    if size_el:
        data["size"] = size_el.get_text(' ', strip=True).replace('\xa0', ' ').strip()
    if data["size"] == "Unknown":
        attach_div = soup.find('div', class_='attach_link')
        if attach_div:
            for li in attach_div.find_all('li'):
                li_text = li.get_text(' ', strip=True).replace('\xa0', ' ').strip()
                if re.search(r'\d[0-9.,]*\s*(?:B|KB|MB|GB|TB|Б|КБ|МБ|ГБ|ТБ)\b', li_text, re.IGNORECASE):
                    data["size"] = li_text
                    break
    if data["size"] == "Unknown":
        sz = extract_size_from_title(raw_title)
        if sz:
            data["size"] = sz

    if data["size"] != "Unknown":
        data["size_bytes"] = parse_size_to_bytes(data["size"])

    # 4. Текстовые метаданные из тела поста
    text_content = post_text(post_body)
    patterns = {
        "year": r'(?:Год выпуска|Дата выпуска|Дата выхода|Год выхода|Release date)\s*:\s*([^\n]+)',
        "genre": r'Жанр\s*:\s*([^\n]+)',
        "developer": r'Разработчик\s*:\s*([^\n]+)',
        "publisher": r'Издатель\s*:\s*([^\n]+)',
        "version": r'(?:Версия(?:\s+игры)?|Game\s*Version)\s*:\s*([^\n]+)',
        "edition_type": r'Тип издания\s*:\s*([^\n]+)',
        "release_type": r'Релиз\s*:\s*([^\n]+)',
        "interface_lang": r'Язык интерфейса\s*:\s*([^\n]+)',
        "voice_lang": r'(?:Язык озвучки|Озвучка)\s*:\s*([^\n]+)',
        "source": r'Источник\s*:\s*([^\n]+)',
    }

    for key, pat in patterns.items():
        m = re.search(pat, text_content, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            # Убираем лишние обрамляющие скобки если есть
            if val:
                data[key] = val

    if data.get("version") and data["version"] != "Unknown":
        cv = clean_version_str(data["version"])
        if cv:
            data["version"] = cv

    # Определение Steam App ID и ссылки на источник
    steam_m = re.search(r'store\.steampowered\.com/app/(\d+)', html)
    if steam_m:
        sid = steam_m.group(1)
        data["steam_id"] = sid
        data["steam_url"] = f"https://store.steampowered.com/app/{sid}"
        # Стандартный постер Steam Library Capsule 600x900
        data["cover_standard"] = f"https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/{sid}/library_600x900.jpg"

    # 5. Обложка и скриншоты
    # Ищем специальный спойлер со скриншотами
    sp_screen = None
    for sp in post_body.find_all('div', class_='sp-wrap'):
        head = sp.find('div', class_='sp-head')
        if head and 'скриншот' in head.get_text().lower():
            sp_screen = sp
            break

    screenshots = []
    if sp_screen:
        for el in sp_screen.find_all(['var', 'img'], class_='postImg'):
            parent_a = el.find_parent('a')
            href = parent_a.get('href', '').strip() if parent_a else ''
            thumb = (el.get('title') or el.get('src') or '').strip()
            if href.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                if href not in screenshots:
                    screenshots.append(href)
            elif thumb and thumb.startswith('http') and 'smiles' not in thumb:
                if thumb not in screenshots:
                    screenshots.append(thumb)

    # Обложка — первая картинка вне спойлера со скриншотами
    cover = None
    all_imgs = []
    for el in post_body.find_all(['var', 'img'], class_='postImg'):
        if sp_screen and el in sp_screen.find_all(['var', 'img'], class_='postImg'):
            continue
        u = (el.get('title') or el.get('src') or '').strip()
        if u.startswith('http') and 'smiles' not in u:
            all_imgs.append(u)
            if not cover:
                cover = u

    if not screenshots and len(all_imgs) > 1:
        screenshots = all_imgs[1:10]

    data["cover"] = cover
    if not data["cover_standard"]:
        data["cover_standard"] = cover
    data["screenshots"] = screenshots[:10]

    # 6. Описание
    desc_match = re.search(
        r'Описание\s*:\s*([\s\S]+?)(?=\n\s*(?:Системные требования|Минимальные|Рекомендуемые|Доп\. информация|Скриншоты|Трейлер|Список файлов|FAQ|Время раздачи|Особенности)|$)',
        text_content, re.IGNORECASE
    )
    if desc_match:
        data["description"] = desc_match.group(1).strip()
    else:
        # Берём первые 500 символов, если явный блок "Описание" отсутствует
        data["description"] = text_content[:500].strip()

    return data


def merge_topic_details(item: dict, details: dict) -> bool:
    """Объединяет свежие метаданные темы в существующую запись базы.

    Возвращает True, если infohash сменился (перезаливка на трекере).
    """
    old_hash = get_magnet_btih(item.get("magnet"))

    # Обновляем заголовок, если он стал чище
    if details.get("title") and details["title"] != "Unknown":
        item["title"] = details["title"]
    if details.get("raw_title"):
        item["raw_title"] = details["raw_title"]

    # Обновляем размер
    if details.get("size") and details["size"] != "Unknown":
        item["size"] = details["size"]
        if details.get("size_bytes"):
            item["size_bytes"] = details["size_bytes"]

    # Обновляем остальные непустые поля
    for k, v in details.items():
        if k in ("size", "size_bytes", "title", "raw_title", "subforum_id", "subforum", "subforum_slug"):
            continue
        if v not in (None, "Unknown", [], ""):
            item[k] = v
        elif k not in item:
            item[k] = v

    new_hash = get_magnet_btih(details.get("magnet"))
    return bool(new_hash) and new_hash != old_hash
