import sys
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.topic_parser import get_topic_data, merge_topic_details
from core.storage import load_json, save_json, GAMES_FILE

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
    except Exception:
        return tid, None

def run_enrich_fast(limit=None, max_workers=6, save_interval=50):
    games = load_json(GAMES_FILE) or []
    candidates = [g for g in games if is_incomplete(g)]
    
    if limit and limit > 0:
        candidates = candidates[:limit]

    total = len(candidates)
    if total == 0:
        print("[*] Все раздачи уже дообогащены! (100% базы заполнено)")
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
            
            if done_count % save_interval == 0 or done_count == total:
                elapsed = time.time() - start_time
                speed = done_count / elapsed if elapsed > 0 else 0
                remaining = total - done_count
                eta_sec = remaining / speed if speed > 0 else 0
                eta_min = eta_sec / 60
                print(f"  [{done_count:4d}/{total:4d}] Успешно: {success_count} | Скорость: {speed:.1f} тем/сек | ETA: {eta_min:.1f} мин", flush=True)
                save_json(games, GAMES_FILE)

    save_json(games, GAMES_FILE)
    elapsed = time.time() - start_time
    print(f"\n[+] Дообогащение завершено за {elapsed/60:.1f} мин! Успешно обогащено: {success_count}/{total}")

if __name__ == '__main__':
    limit_val = None
    if len(sys.argv) > 1 and sys.argv[1].lower() not in ('all', '0'):
        limit_val = int(sys.argv[1])
    workers_val = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    run_enrich_fast(limit=limit_val, max_workers=workers_val)
