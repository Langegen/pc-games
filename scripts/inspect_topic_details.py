import sys
import os
import json
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.network import fetch_url
from core.topic_parser import post_text

# Let's take 3 topics: one modern action, one RPG, one indie
topics_to_test = ['6890135', '6722359', '6933053']

for tid in topics_to_test:
    url = f"https://rutracker.org/forum/viewtopic.php?t={tid}"
    print(f"\n==================== Topic {tid} ====================")
    html = fetch_url(url, forum_url=False)
    if not html:
        print("Failed to fetch HTML")
        continue

    soup = BeautifulSoup(html, 'html.parser')
    pb = soup.find('div', class_='post_body')
    if not pb:
        print("No post_body")
        continue

    text = post_text(pb)
    print("--- POST TEXT HEAD (first 600 chars) ---")
    print(text[:600])

    print("\n--- IMAGES & SPOILERS ---")
    spoilers = pb.find_all('div', class_='sp-wrap')
    print(f"Total spoilers: {len(spoilers)}")
    for s in spoilers:
        head = s.find('div', class_='sp-head')
        head_txt = head.get_text(strip=True) if head else ""
        imgs_in_sp = len(s.find_all(['var', 'img'], class_='postImg'))
        print(f"  Spoiler '{head_txt}': {imgs_in_sp} images")

    all_imgs = pb.find_all(['var', 'img'], class_='postImg')
    print(f"Total postImg elements: {len(all_imgs)}")
    for img in all_imgs[:4]:
        parent_a = img.find_parent('a')
        print(f"  Img: title={img.get('title')}, src={img.get('src')}, parent_a={parent_a.get('href') if parent_a else None}")
