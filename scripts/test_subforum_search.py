import undetected_chromedriver as uc
import time
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

options = uc.ChromeOptions()
# options.add_argument('--headless')
driver = uc.Chrome(options=options)
driver.get("https://rutracker.org/forum/index.php")
time.sleep(1)

for k, v in cookies.items():
    try:
        driver.add_cookie({'name': k, 'value': v, 'domain': '.rutracker.org'})
    except Exception:
        pass

# Test 1: f=635 & nm=portable
driver.get("https://rutracker.org/forum/tracker.php?f=635&nm=portable")
time.sleep(2)

soup = BeautifulSoup(driver.page_source, 'html.parser')
rows = soup.select('#tor-tbl tr[id^="trs-tr-"]') or soup.select('tr.hl-tr')
print(f"Results for f=635 & nm=portable: {len(rows)} topics found!")

for r in rows[:3]:
    title_el = r.select_one('a.tt-text')
    sz_el = r.select_one('.tor-size')
    print("  Topic:", title_el.get_text(strip=True)[:60] if title_el else "N/A", "| Size:", sz_el.get_text(strip=True) if sz_el else "N/A")

driver.quit()
