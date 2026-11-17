import sys
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def log(msg):
    print(msg, flush=True)

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from config.subforums import SUBFORUMS, EXCLUDED_SUBFORUM_IDS

cookies_raw = open('.env', encoding='utf-8').read()
cookies = {}
for line in cookies_raw.splitlines():
    if line.startswith('RUTRACKER_COOKIES='):
        val = line.split('=', 1)[1].strip().strip('\'\"')
        for item in val.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                cookies[k.strip()] = v.strip()

# Launch non-headless Chrome (which doesn't get blocked by CF)
options = uc.ChromeOptions()
driver = uc.Chrome(options=options)
log("Chrome started")

driver.get("https://rutracker.org/forum/index.php")
time.sleep(1)

for k, v in cookies.items():
    try:
        driver.add_cookie({'name': k, 'value': v, 'domain': '.rutracker.org'})
    except Exception:
        pass

# Build query with all allowed subforum IDs: f[]=635&f[]=127...
sub_params = "&".join(f"f[]={sid}" for sid in SUBFORUMS.keys())
search_url = f"https://rutracker.org/forum/tracker.php?{sub_params}&nm=portable&o=1&s=1"
log(f"Navigating to tracker search across all {len(SUBFORUMS)} subforums...")
driver.get(search_url)
time.sleep(3)

log(f"Page title: {driver.title}")
soup = BeautifulSoup(driver.page_source, 'html.parser')
rows = soup.select('#tor-tbl tr[id^="trs-tr-"]') or soup.select('tr.hl-tr')
log(f"FOUND {len(rows)} topics on page 1!")

for r in rows[:5]:
    title_el = r.select_one('a.tt-text')
    sz_el = r.select_one('.tor-size')
    f_el = r.select_one('.f-name a, td.f a')
    t_text = title_el.get_text(strip=True)[:50] if title_el else "N/A"
    s_text = sz_el.get_text(strip=True) if sz_el else "N/A"
    f_text = f_el.get_text(strip=True) if f_el else "N/A"
    log(f"  [{f_text}] {t_text} | {s_text}")

# Check pagination: how many pages?
pgs = soup.select('.pg')
log(f"Pagination elements: {len(pgs)}")
if pgs:
    log(f"Pages text: {' '.join([p.get_text(strip=True) for p in pgs[:10]])}")

# Save updated cookies to .env!
latest_cookies = {c['name']: c['value'] for c in driver.get_cookies()}
log(f"Got {len(latest_cookies)} cookies from Chrome session")
cookie_str = "; ".join(f"{k}={v}" for k, v in latest_cookies.items())
with open('.env', 'w', encoding='utf-8') as f:
    f.write(f"RUTRACKER_COOKIES='{cookie_str}'\n")
    f.write(f"RUTRACKER_UA='{driver.execute_script('return navigator.userAgent;')}'\n")
log("Saved fresh cookies to .env")

driver.quit()
log("Done!")
