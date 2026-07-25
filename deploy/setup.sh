#!/bin/bash
# Tagall server installer — run as root from /root/tagall/
# Safe to re-run: reuses the venv, upgrades deps, (re)installs the service.
set -e
cd /root/tagall

if [ ! -f .env ]; then
    echo "ERROR: /root/tagall/.env is missing. Create it first:"
    echo "  printf 'BOT_TOKEN=<token from BotFather>\n' > /root/tagall/.env"
    exit 1
fi

[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --upgrade -r requirements.txt

cp deploy/tagall.service /etc/systemd/system/tagall.service
systemctl daemon-reload
systemctl enable tagall
systemctl restart tagall
sleep 2
systemctl is-active tagall && echo "Tagall is up." || journalctl -u tagall -n 20 --no-pager
