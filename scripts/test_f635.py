import sys
import os
import time

def log(msg):
    print(msg, flush=True)

log("Starting test...")
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

cookies_raw = open('.env', encoding='utf-8').read()
cookies = {}
for line in cookies_raw.splitlines():
    if line.startswith('RUTRACKER_COOKIES='):
        val = line.split('=', 1)[1].strip().strip('\'\"')
        for item in val.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                cookies[k.strip()] = v.strip()

log(f"Cookies: {len(cookies)}")

options = uc.ChromeOptions()
options.add_argument('--headless')
driver = uc.Chrome(options=options)
log("Chrome started")

driver.get("https://rutracker.org/forum/index.php")
log(f"Index loaded: {driver.title}")

for k, v in cookies.items():
    try:
        driver.add_cookie({'name': k, 'value': v, 'domain': '.rutracker.org'})
    except Exception as e:
        log(f"Cookie err: {e}")

# Let's search f=635 (Новинки) with nm=portable
search_url = "https://rutracker.org/forum/tracker.php?f=635&nm=portable"
log(f"Navigating to {search_url}...")
driver.get(search_url)
time.sleep(2)
log(f"Page title: {driver.title}")

soup = BeautifulSoup(driver.page_source, 'html.parser')
rows = soup.select('#tor-tbl tr[id^="trs-tr-"]') or soup.select('tr.hl-tr')
log(f"Results for f=635 & nm=portable: {len(rows)} topics found!")

for r in rows[:5]:
    title_el = r.select_one('a.tt-text')
    sz_el = r.select_one('.tor-size')
    t_text = title_el.get_text(strip=True)[:60] if title_el else "N/A"
    s_text = sz_el.get_text(strip=True) if sz_el else "N/A"
    log(f"  Topic: {t_text} | Size: {s_text}")

# Also test multiple subforums: what if we pass all subforums or f[]?
# Let's check how tracker.php allows searching across multiple subforums or all of f=5
driver.quit()
log("Done!")
