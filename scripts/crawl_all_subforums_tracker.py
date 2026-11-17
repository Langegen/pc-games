import sys
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.subforums import SUBFORUMS
from core.stats import crawl_tracker_portable
from core.storage import load_json, save_json, update_subforums_catalog, GAMES_FILE, STATS_FILE, SUBFORUMS_FILE

existing_data = load_json(GAMES_FILE) or []
existing_map = {str(item["topic_id"]): item for item in existing_data if item.get("topic_id")}
print(f"Current database size: {len(existing_data)} games")

existing_stats = load_json(STATS_FILE) or {}
total_added = 0

for fid, info in SUBFORUMS.items():
    name = info['name']
    print(f"\n--- Checking f={fid} ({name}) ---")
    games, stats = crawl_tracker_portable(subforum_id=fid, max_size_gb=60.0)
    new_in_sub = 0
    for g in games:
        tid = str(g["topic_id"])
        if tid not in existing_map:
            existing_data.append(g)
            existing_map[tid] = g
            new_in_sub += 1
            total_added += 1
        else:
            item = existing_map[tid]
            if g.get("subforum_id") and g["subforum_id"] != "Unknown" and item.get("subforum_id") in (None, "Unknown"):
                item["subforum_id"] = g["subforum_id"]
                item["subforum"] = g["subforum"]
                item["subforum_slug"] = g["subforum_slug"]
            if g.get("size_bytes") and not item.get("size_bytes"):
                item["size_bytes"] = g["size_bytes"]

    existing_stats.update(stats)
    print(f"  f={fid} done: {len(games)} found, {new_in_sub} new added")
    time.sleep(0.3)

save_json(existing_data, GAMES_FILE)
save_json(existing_stats, STATS_FILE)
update_subforums_catalog(existing_data, SUBFORUMS_FILE)

print(f"\n[+] FINISHED: Added {total_added} new games! Total now: {len(existing_data)}")
