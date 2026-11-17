from bs4 import BeautifulSoup
import re

with open('data/tracker_test.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
tbl = soup.select_one('#tor-tbl')
if not tbl:
    print("No #tor-tbl found!")
else:
    rows = tbl.select('tr')
    print(f"Total rows in #tor-tbl: {len(rows)}")
    for i, r in enumerate(rows[:5]):
        print(f"Row {i}: id={r.get('id')} class={r.get('class')}")
        links = r.select('a')
        print(f"  Links: {[(a.get('href'), a.get_text(strip=True)[:30]) for a in links[:3]]}")
