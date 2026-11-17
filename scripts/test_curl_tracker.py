import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.subforums import SUBFORUMS
from core.network import fetch_url
from core.stats import parse_tracker_page

sub_params = "&".join(f"f[]={sid}" for sid in SUBFORUMS.keys())
url = f"https://rutracker.org/forum/tracker.php?{sub_params}&nm=portable&o=1&s=1&start=0"

print("Fetching via curl_cffi...")
html = fetch_url(url, forum_url=True)
print(f"HTML length: {len(html) if html else 0}")

if html:
    results = parse_tracker_page(html)
    print(f"Extracted {len(results)} portable games from page 1!")
    if results:
        print("Sample item 0:")
        for k, v in results[0].items():
            print(f"  {k}: {v}")
        print("Sample item 1:")
        for k, v in results[1].items():
            print(f"  {k}: {v}")
