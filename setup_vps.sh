#!/bin/bash
# ============================================================
# Автоматическая установка парсера pc-games на VPS
# Debian/Ubuntu, x86_64. Запуск: bash setup_vps.sh
# ============================================================
set -e

REPO_URL_DEFAULT="https://github.com/Langegen/pc-games.git"
INSTALL_DIR="${INSTALL_DIR:-/root/pc-games-bot}"

log()  { echo -e "\n\033[1;32m[setup]\033[0m $1"; }
warn() { echo -e "\n\033[1;33m[!]\033[0m $1"; }
ask()  { read -r -p "$1" "$2" < /dev/tty; }

# ---------- 0. Проверки ----------
if [ "$(id -u)" != "0" ]; then
    echo "Запустите от root: sudo bash setup_vps.sh"
    exit 1
fi
if [ "$(uname -m)" != "x86_64" ]; then
    echo "Нужен VPS с архитектурой x86_64 (Google Chrome не поддерживает $(uname -m))"
    exit 1
fi
export DEBIAN_FRONTEND=noninteractive

# ---------- 1. Системные пакеты ----------
log "Установка системных пакетов (git, python3, xvfb, cron)..."
apt-get update -qq -o Acquire::Retries=3 || warn "apt-get update неполный — продолжаем со старыми индексами"
apt-get install -y -qq --no-install-recommends git python3 python3-venv wget cron xvfb >/dev/null

# ---------- 2. Google Chrome ----------
if command -v google-chrome >/dev/null 2>&1; then
    log "Google Chrome уже установлен: $(google-chrome --version)"
else
    log "Установка Google Chrome..."
    wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    apt-get install -y -qq /tmp/chrome.deb >/dev/null
    rm -f /tmp/chrome.deb
fi

# ---------- 2.5 CloudflareBypassForScraping (Docker) ----------
if [ -z "${SKIP_CF_BYPASS:-}" ] && ! command -v docker >/dev/null 2>&1; then
    log "Установка Docker..."
    apt-get install -y -qq docker.io >/dev/null 2>&1 || curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker >/dev/null 2>&1 || true
fi

if [ -z "${SKIP_CF_BYPASS:-}" ]; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^cf-bypass$'; then
        log "CloudflareBypassForScraping уже запущен."
    else
        log "Запуск CloudflareBypassForScraping (docker, порт 8000)..."
        docker rm -f cf-bypass >/dev/null 2>&1 || true
        docker run -d --name cf-bypass --restart unless-stopped -p 8000:8000 \
            ghcr.io/sarperavci/cloudflarebypassforscraping:latest >/dev/null
        sleep 5
        if curl -fsS http://localhost:8000/ >/dev/null 2>&1; then
            log "Сервис CF-bypass работает: http://localhost:8000"
        else
            warn "Сервис не отвечает — проверьте: docker logs cf-bypass"
        fi
    fi
fi

# ---------- 3. Репозиторий ----------
if [ -d "$INSTALL_DIR/.git" ]; then
    log "Обновление репозитория в $INSTALL_DIR..."
    git -C "$INSTALL_DIR" pull --rebase || warn "git pull не удался"
elif [ -f "$(pwd)/run.sh" ] && [ -d "$(pwd)/.git" ]; then
    INSTALL_DIR="$(pwd)"
    log "Используем текущий каталог: $INSTALL_DIR"
else
    log "Клонирование репозитория в $INSTALL_DIR..."
    git clone "$REPO_URL_DEFAULT" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# ---------- 4. Python-окружение ----------
if [ ! -x venv/bin/python3 ]; then
    log "Создание виртуального окружения..."
    python3 -m venv venv
fi
log "Установка Python-зависимостей..."
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt

# ---------- 5. Настройка GitHub Remote ----------
current_url="$(git remote get-url origin 2>/dev/null || echo "$REPO_URL_DEFAULT")"
if echo "$current_url" | grep -q 'github_pat_\|ghp_'; then
    log "GitHub-токен уже настроен в remote."
else
    echo ""
    log "Настройка доступа к GitHub для выгрузки изменений (git push):"
    echo "  Нужен Personal Access Token с правами repo (ghp_... или github_pat_...)"
    ask "  Введите ваш GitHub токен (или Enter для пропуска): " GITHUB_TOKEN
    if [ -n "$GITHUB_TOKEN" ]; then
        clean_url="$(echo "$current_url" | sed -E 's#https://[^@]+@#https://#')"
        authed_url="$(echo "$clean_url" | sed -E "s#https://#https://${GITHUB_TOKEN}@#")"
        git remote set-url origin "$authed_url"
        log "Remote origin обновлён с токеном."
    else
        warn "Токен не введён — cron не сможет делать git push."
    fi
fi

# ---------- 6. Настройка .env ----------
if [ -f .env ] && grep -q '^RUTRACKER_COOKIES=' .env 2>/dev/null; then
    log "Файл .env уже настроен."
else
    cat > .env <<'EOF'
RUTRACKER_CF_BYPASS=http://localhost:8000
EOF
    chmod 600 .env
    log "Создан базовый .env файл."
fi

# ---------- 7. Настройка Cron ----------
CRON_CMD="cd $INSTALL_DIR && bash run.sh >> $INSTALL_DIR/cron_log.txt 2>&1"
if crontab -l 2>/dev/null | grep -Fq "$INSTALL_DIR/run.sh"; then
    log "Задание cron уже настроено."
else
    ask "В какой час запускать ежедневный сбор (0-23, по умолчанию 4): " CRON_HOUR
    CRON_HOUR="${CRON_HOUR:-4}"
    (crontab -l 2>/dev/null || true; echo "0 $CRON_HOUR * * * $CRON_CMD") | crontab -
    log "Cron настроен: ежедневно в ${CRON_HOUR}:00."
fi

log "Установка pc-games успешно завершена!"
echo "  Ручной запуск: bash run.sh"
echo "  Диагностика:   ./venv/bin/python3 scripts/test_connection.py"
