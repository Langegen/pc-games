import sys
import os
import re
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.network import fetch_url
from core.topic_parser import post_text

def test_extract(topic_id):
    url = f"https://rutracker.org/forum/viewtopic.php?t={topic_id}"
    html = fetch_url(url, forum_url=False)
    if not html:
        print("Failed to fetch HTML")
        return

    soup = BeautifulSoup(html, 'html.parser')
    pb = soup.find('div', class_='post_body')
    if not pb:
        return

    txt = post_text(pb)

    data = {}
    
    # 1. Regex patterns
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

    for k, pat in patterns.items():
        m = re.search(pat, txt, re.IGNORECASE)
        if m:
            data[k] = m.group(1).strip()
        else:
            data[k] = None

    # Source link & Steam App ID
    steam_m = re.search(r'store\.steampowered\.com/app/(\d+)', html)
    if steam_m:
        data["steam_id"] = steam_m.group(1)
        data["steam_url"] = f"https://store.steampowered.com/app/{steam_m.group(1)}"
    else:
        data["steam_id"] = None
        data["steam_url"] = None

    # Cover & Screenshots
    cover = None
    screenshots = []
    
    # Find screenshots spoiler
    sp_screen = None
    for sp in pb.find_all('div', class_='sp-wrap'):
        head = sp.find('div', class_='sp-head')
        if head and 'скриншот' in head.get_text().lower():
            sp_screen = sp
            break

    if sp_screen:
        for el in sp_screen.find_all(['var', 'img'], class_='postImg'):
            # Check if parent is a link to full image
            parent_a = el.find_parent('a')
            href = parent_a.get('href', '') if parent_a else ''
            thumb = (el.get('title') or el.get('src') or '').strip()
            # If href is an image URL or imageban / fastpic link
            if href.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                screenshots.append(href)
            elif thumb:
                screenshots.append(thumb)

    # First image outside screenshots spoiler is cover
    for el in pb.find_all(['var', 'img'], class_='postImg'):
        if sp_screen and el in sp_screen.find_all(['var', 'img'], class_='postImg'):
            continue
        u = (el.get('title') or el.get('src') or '').strip()
        if u.startswith('http') and 'smiles' not in u:
            cover = u
            break

    data["cover"] = cover
    data["screenshots"] = screenshots[:10]

    # Description
    desc_m = re.search(
        r'Описание\s*:\s*([\s\S]+?)(?=\n\s*(?:Системные требования|Минимальные|Рекомендуемые|Доп\. информация|Скриншоты|Трейлер|Список файлов|FAQ|Время раздачи|Особенности)|$)',
        txt, re.IGNORECASE
    )
    if desc_m:
        data["description"] = desc_m.group(1).strip()
    else:
        data["description"] = ""

    print(f"\n--- Extracted Data for Topic {topic_id} ---")
    for k, v in data.items():
        if k == 'description':
            print(f"  {k}: {repr(v[:120])}...")
        elif k == 'screenshots':
            print(f"  {k}: ({len(v)}) {v[:2]}")
        else:
            print(f"  {k}: {repr(v)}")

test_extract('6890135')
test_extract('6722359')
