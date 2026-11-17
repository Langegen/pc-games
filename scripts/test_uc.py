import undetected_chromedriver as uc
import time

cookies_raw = open('.env', encoding='utf-8').read()
cookies = {}
for line in cookies_raw.splitlines():
    if line.startswith('RUTRACKER_COOKIES='):
        val = line.split('=', 1)[1].strip().strip('\'\"')
        for item in val.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                cookies[k.strip()] = v.strip()

print(f"Loaded {len(cookies)} cookies.")

options = uc.ChromeOptions()
driver = uc.Chrome(options=options)
driver.get("https://rutracker.org/forum/index.php")
time.sleep(1)

for k, v in cookies.items():
    try:
        driver.add_cookie({'name': k, 'value': v, 'domain': '.rutracker.org'})
    except Exception as e:
        print("add_cookie error:", e)

ua = driver.execute_script("return navigator.userAgent;")
print("Chrome UA:", ua)

driver.get("https://rutracker.org/forum/tracker.php?f=5&nm=portable")
time.sleep(2)
print("Page Title:", driver.title)
print("Page length:", len(driver.page_source))
has_results = 'forumtable' in driver.page_source or 'hl-tr' in driver.page_source
print("Has results table:", has_results)

# Let's check updated cookies
all_cookies = driver.get_cookies()
print("Total cookies now in Chrome:", len(all_cookies))
for c in all_cookies:
    print(f"  {c['name']} = {c['value'][:25]}... (domain: {c['domain']})")

try:
    driver.quit()
except Exception:
    pass
