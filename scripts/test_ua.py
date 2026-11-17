import os
from curl_cffi import requests as cf

cookies_raw = open('.env', encoding='utf-8').read()
cookies = {}
for line in cookies_raw.splitlines():
    if line.startswith('RUTRACKER_COOKIES='):
        val = line.split('=', 1)[1].strip().strip('\'\"')
        for item in val.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                cookies[k.strip()] = v.strip()

print(f"Loaded {len(cookies)} cookies: {list(cookies.keys())}")

for imp in ['chrome120', 'chrome124', 'chrome', 'safari15_5', 'edge101']:
    try:
        kwargs = {'impersonate': imp, 'timeout': 10, 'cookies': cookies}
        r = cf.get('https://rutracker.org/forum/tracker.php?f=5&nm=portable', **kwargs)
        chal = ('Just a moment' in r.text or 'cf-browser-verification' in r.text)
        has_table = 'forumtable' in r.text or 'hl-tr' in r.text
        print(f"Imp: {imp:12} | Status: {r.status_code} | Len: {len(r.text):6} | CF-Chal: {chal} | Has Table: {has_table}")
    except Exception as e:
        print(f"Imp: {imp:12} | Error: {e}")
