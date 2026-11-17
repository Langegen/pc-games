import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stats import parse_tracker_page

with open('data/tracker_test.html', 'r', encoding='utf-8') as f:
    html = f.read()

items = parse_tracker_page(html)
print(f"Extracted {len(items)} items from tracker_test.html")
if items:
    print("First item sample:")
    for k, v in items[0].items():
        print(f"  {k}: {v}")
