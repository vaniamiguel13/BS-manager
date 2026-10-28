#!/usr/bin/env bash
# Liga a plataforma à internet através de um Cloudflare Tunnel (HTTPS, sem abrir portas no router).
#
# Antes de correr, crie o túnel no painel da Cloudflare (ver README, secção "Cloudflare Tunnel")
# e copie o token que aparece no comando de instalação.
#
# Uso: ./instalar-cloudflare-tunnel.sh <TOKEN> https://gestao.suaempresa.pt
set -euo pipefail
cd "$(dirname "$0")"

TOKEN="${1:-}"
PUBLIC_URL="${2:-}"
if [ -z "$TOKEN" ] || [[ "$PUBLIC_URL" != https://* ]]; then
    echo "Uso: $0 <TOKEN> https://gestao.suaempresa.pt"
    exit 1
fi

# 1. Instalar o cloudflared
if ! command -v cloudflared > /dev/null; then
    if command -v apt-get > /dev/null; then
        echo "A instalar o cloudflared..."
        sudo mkdir -p --mode=0755 /usr/share/keyrings
        curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \
            | sudo tee /usr/share/keyrings/cloudflare-main.gpg > /dev/null
        echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" \
            | sudo tee /etc/apt/sources.list.d/cloudflared.list > /dev/null
        sudo apt-get update
        sudo apt-get install -y cloudflared
    else
        echo "Instale o cloudflared manualmente e volte a correr este script:"
        echo "  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        exit 1
    fi
fi

# 2. Instalar o túnel como serviço (arranca com o PC)
if systemctl list-unit-files cloudflared.service > /dev/null 2>&1 \
        && systemctl list-unit-files cloudflared.service | grep -q cloudflared; then
    echo "O serviço cloudflared já existe; a reinstalar com o novo token."
    sudo cloudflared service uninstall || true
fi
sudo cloudflared service install "$TOKEN"

# 3. Configurar a plataforma para HTTPS e só aceitar ligações através do túnel
set_env() {
    touch .env
    if grep -q "^$1=" .env; then
        sed -i "s|^$1=.*|$1=$2|" .env
    else
        echo "$1=$2" >> .env
    fi
}
set_env SESSION_COOKIE_SECURE 1
set_env HOST 127.0.0.1
set_env PUBLIC_URL "$PUBLIC_URL"

if systemctl list-unit-files bs-manager.service 2>/dev/null | grep -q bs-manager; then
    sudo systemctl restart bs-manager
else
    echo "Aviso: o serviço bs-manager ainda não está instalado. Corra ./instalar-servico.sh"
fi

echo
echo "Pronto! A plataforma fica disponível em $PUBLIC_URL (pode demorar 1-2 minutos)."
echo "Todos, incluindo quem está no escritório, devem passar a usar este endereço."
echo "Estado do túnel: sudo systemctl status cloudflared"
