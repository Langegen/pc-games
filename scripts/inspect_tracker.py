from bs4 import BeautifulSoup

# Let's check how tracker.php search form is structured
# We have a driver script that can save the HTML or inspect the form
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

options = uc.ChromeOptions()
driver = uc.Chrome(options=options)
driver.get("https://rutracker.org/forum/index.php")
time.sleep(1)

for k, v in cookies.items():
    try:
        driver.add_cookie({'name': k, 'value': v, 'domain': '.rutracker.org'})
    except Exception as e:
        pass

# Try searching with f=5
driver.get("https://rutracker.org/forum/tracker.php?f=5&nm=portable")
time.sleep(2)

soup = BeautifulSoup(driver.page_source, 'html.parser')
# Save page snippet or form elements
with open('data/tracker_test.html', 'w', encoding='utf-8') as f:
    f.write(driver.page_source)

# Check for table or message
print("Title:", driver.title)
tables = soup.find_all('table')
print(f"Found {len(tables)} tables")
for t in tables:
    t_id = t.get('id', '')
    t_class = t.get('class', [])
    if t_id or t_class:
        print(f"Table id={t_id} class={t_class}")

msg = soup.find(class_='msg')
if msg:
    print("Msg:", msg.get_text(strip=True))

driver.quit()
