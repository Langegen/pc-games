"""Диагностика сетевого доступа к RuTracker (Atom-ленты, curl_cffi, Chrome, CF).

Запуск:
  python scripts/test_connection.py
"""
import os
import sys
import time

# Добавляем корневую директорию проекта в sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.network import (
    SESSION_COOKIES,
    USER_AGENT,
    PROXY_URL,
    CF_BYPASS_URL,
    is_cf_challenge,
    init_env,
)

init_env()

TEST_FEED_URL = "https://feed.rutracker.cc/atom/f/635.atom"
TEST_TOPIC_URL = "https://rutracker.org/forum/viewtopic.php?t=6935546"


def test_atom_feed():
    print("\n=== 1. Проверка доступа к Atom-лентам (feed.rutracker.cc) ===")
    from curl_cffi import requests as cf
    try:
        kwargs = {"impersonate": "chrome120", "timeout": 10}
        if PROXY_URL:
            kwargs["proxies"] = {"http": PROXY_URL, "https": PROXY_URL}
        r = cf.get(TEST_FEED_URL, **kwargs)
        if r.status_code == 200 and '<feed' in r.text:
            print("  [+] Atom-ленты работают напрямую БЕЗ блокировок!")
            return True
        else:
            print(f"  [!] Статус ответа: {r.status_code}")
    except Exception as e:
        print(f"  [!] Ошибка доступа к Atom-лентам: {e}")
    return False


def test_curl():
    print("\n=== 2. Проверка прямого доступа curl_cffi (rutracker.org) ===")
    from curl_cffi import requests as cf
    kwargs = {
        "headers": {"User-Agent": USER_AGENT},
        "cookies": SESSION_COOKIES,
        "impersonate": "chrome120",
        "timeout": 15,
    }
    if PROXY_URL:
        kwargs["proxies"] = {"http": PROXY_URL, "https": PROXY_URL}
    try:
        r = cf.get(TEST_TOPIC_URL, **kwargs)
        chal = is_cf_challenge(r.text)
        has_post = 'post_body' in r.text
        print(f"  Статус: {r.status_code}, Длина: {len(r.text)}, CF-Challenge: {chal}, Валидная страница: {has_post}")
        if r.status_code == 200 and not chal and has_post:
            print("  [+] curl_cffi успешно проходит Cloudflare!")
            return True
        elif chal:
            print("  [~] Cloudflare заблокировал прямой curl_cffi (требуются cookies или Chrome).")
    except Exception as e:
        print(f"  [!] Ошибка curl_cffi: {e}")
    return False


def test_cf_bypass():
    print("\n=== 3. Проверка локального CF-Bypass сервиса ===")
    if not CF_BYPASS_URL:
        print("  [~] RUTRACKER_CF_BYPASS не настроен в .env (пропущено).")
        return False
    from core.network import _bypass_request
    html = _bypass_request(TEST_TOPIC_URL)
    if html and 'post_body' in html:
        print("  [+] CloudflareBypassForScraping работает штатно!")
        return True
    else:
        print("  [!] CF-Bypass сервис не вернул валидный ответ.")
        return False


def main():
    print(f"=== Диагностика подключения pc-games ===")
    print(f"  Куки в .env: {'есть (' + ', '.join(SESSION_COOKIES.keys()) + ')' if SESSION_COOKIES else 'НЕТ'}")
    print(f"  Прокси: {PROXY_URL or 'нет'}")
    print(f"  CF Bypass URL: {CF_BYPASS_URL or 'нет'}")

    feed_ok = test_atom_feed()
    curl_ok = test_curl()
    bypass_ok = test_cf_bypass()

    print("\n=== ВЕРДИКТ ===")
    if feed_ok:
        print("  [✓] Быстрый ежедневный сбор по Atom-лентам ГОТОВ к работе.")
    if curl_ok or bypass_ok:
        print("  [✓] Дообогащение страниц тем (viewtopic.php) работает.")
    else:
        print("  [i] Для дообогащения страниц тем без браузера рекомендуется указать RUTRACKER_COOKIES в .env")


if __name__ == '__main__':
    main()
