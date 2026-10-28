#!/usr/bin/env bash
# Instala a plataforma como serviço systemd: arranca com o PC e reinicia sozinha em caso de erro.
# Uso: ./instalar-servico.sh   (pede a palavra-passe de sudo)
set -euo pipefail
cd "$(dirname "$0")"
DIR="$(pwd)"
USER_NAME="$(id -un)"

if [ ! -d .venv ]; then
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

sudo tee /etc/systemd/system/bs-manager.service > /dev/null <<UNIT
[Unit]
Description=BS Manager
After=network-online.target
Wants=network-online.target

[Service]
User=${USER_NAME}
WorkingDirectory=${DIR}
ExecStart=${DIR}/.venv/bin/python ${DIR}/serve.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now bs-manager
echo
echo "Serviço instalado. Estado: sudo systemctl status bs-manager"
echo "Registos:               journalctl -u bs-manager -f"
