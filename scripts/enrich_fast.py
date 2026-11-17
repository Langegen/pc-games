import sys
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.topic_parser import get_topic_data, merge_topic_details
from core.storage import load_json, save_json, GAMES_FILE, METADATA_FIELDS

def is_incomplete(item):
    return (not item.get('description') or 
            not item.get('cover') or 
            item.get('year') in (None, 'Unknown') or
            item.get('genre') in (None, 'Unknown') or
            not item.get('screenshots'))

def enrich_worker(item):
    tid = str(item['topic_id'])
    try:
        details = get_topic_data(tid)
        return tid, details
    except Exception as e:
        return tid, None

def run_enrich_fast(limit=50, max_workers=5):
    games = load_json(GAMES_FILE) or []
    candidates = [g for g in games if is_incomplete(g)]
    
    if limit:
        candidates = candidates[:limit]

    total = len(candidates)
    if total == 0:
        print("[*] Все раздачи уже дообогащены!")
        return

    print(f"[*] Запуск быстрого дообогащения для {total} раздач ({max_workers} потоков)...")
    start_time = time.time()
    
    cand_map = {str(g['topic_id']): g for g in candidates}
    done_count = 0
    success_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(enrich_worker, g): g for g in candidates}
        for fut in as_completed(futures):
            tid, details = fut.result()
            done_count += 1
            if details and (details.get('cover') or details.get('description')):
                merge_topic_details(cand_map[tid], details)
                success_count += 1
            
            if done_count % 10 == 0 or done_count == total:
                elapsed = time.time() - start_time
                speed = done_count / elapsed if elapsed > 0 else 0
                print(f"  Прогресс: {done_count}/{total} ({success_count} успешно) - {speed:.1f} тем/сек")
                save_json(games, GAMES_FILE)

    save_json(games, GAMES_FILE)
    elapsed = time.time() - start_time
    print(f"[+] Готово за {elapsed:.1f} сек! Успешно обогащено: {success_count}/{total}")

if __name__ == '__main__':
    limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    run_enrich_fast(limit=limit_arg, max_workers=5)
