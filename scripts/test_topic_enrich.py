import sys
import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.topic_parser import get_topic_data

games = json.load(open('data/pc_games.json', encoding='utf-8'))

for g in games[:2]:
    tid = g['topic_id']
    print(f"\n=== Testing topic {tid}: {g['title']} ===")
    data = get_topic_data(tid)
    for k, v in data.items():
        if k == 'description':
            print(f"  {k}: {repr(v[:100])}...")
        elif k == 'screenshots':
            print(f"  {k}: {len(v)} screenshots: {v[:2]}")
        else:
            print(f"  {k}: {repr(v)}")
