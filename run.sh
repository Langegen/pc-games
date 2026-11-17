#!/bin/bash
# Обновление базы pc-games: git pull -> парсер -> git commit -> git push
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd "$(dirname "$0")"

# Взаимная блокировка от параллельных запусков
LOCK_FILE="/tmp/pc-games-scraper.lock"
exec 200>"$LOCK_FILE"
if ! flock -w 7200 200; then
    echo "[$(date)] Другой экземпляр парсера всё ещё работает спустя 2 часа ожидания. Выход."
    exit 1
fi

# Очистка осиротевших временных папок
rm -rf /tmp/tmp* /tmp/playwright* /tmp/xvfb* 2>/dev/null || true

if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi

echo "[$(date)] Обновление кода из репозитория..."
git pull --rebase origin main || true

echo "[$(date)] Запуск парсера pc-games..."
# Таймаут на выполнение 2 часа (защита от зависаний)
if command -v xvfb-run >/dev/null 2>&1; then
    timeout 7200 xvfb-run -a ./venv/bin/python3 scraper.py "$@" 200>&-
else
    timeout 7200 ./venv/bin/python3 scraper.py "$@" 200>&-
fi

rm -rf /tmp/tmp* /tmp/playwright* /tmp/xvfb* 2>/dev/null || true

echo "[$(date)] Выгрузка изменений на GitHub..."
git add data/pc_games.json data/subforums.json data/pc_games_stats.json changes.txt
if git diff --staged --quiet; then
    echo "[$(date)] Изменений нет - коммит не нужен."
else
    git commit -m "Auto-update pc-games: $(date +'%Y-%m-%d %H:%M:%S')"
    git pull --rebase origin main || true
    git push origin main
    git gc --auto 2>/dev/null || true
    echo "[$(date)] Завершено успешно!"
fi

# Ротация лога
LOG_FILE="$(pwd)/cron_log.txt"
if [ -f "$LOG_FILE" ] && [ "$(wc -l < "$LOG_FILE")" -gt 4000 ]; then
    tail -n 3000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi
