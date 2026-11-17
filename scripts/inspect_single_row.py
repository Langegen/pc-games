import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.subforums import SUBFORUMS
from core.network import fetch_url
from bs4 import BeautifulSoup

sub_params = "&".join(f"f[]={sid}" for sid in SUBFORUMS.keys())
url = f"https://rutracker.org/forum/tracker.php?{sub_params}&nm=portable&o=1&s=1&start=0"

html = fetch_url(url, forum_url=True)
soup = BeautifulSoup(html, 'html.parser')
rows = soup.select('#tor-tbl tr[id^="trs-tr-"]')

if rows:
    first_row = rows[0]
    print("Row HTML:")
    print(first_row.prettify())
