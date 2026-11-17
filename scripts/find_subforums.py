from bs4 import BeautifulSoup

soup = BeautifulSoup(open('data/tracker_test.html', encoding='utf-8'), 'html.parser')
options = soup.select('select[name="f[]"] option')

found = []
in_win = False
for o in options:
    val = o.get('value')
    txt = o.text.strip()
    if 'Игры для Windows' in txt:
        in_win = True
    elif in_win and o.get('class') and 'root_forum' in o.get('class'):
        in_win = False
    
    if in_win:
        found.append((val, txt))

print(f"Found {len(found)} subforums under 'Игры для Windows':")
for val, txt in found[:20]:
    print(f"  val={val:6} | {txt}")
