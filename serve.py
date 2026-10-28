"""Servidor para correr a plataforma num PC (Windows, macOS ou Linux) sem Docker.

Uso: python serve.py   (lê as definições do ficheiro .env, se existir)
"""
import os
import secrets
import socket
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)
# Sem SECRET_KEY, gera uma aleatória e guarda-a no .env para as sessões sobreviverem a reinícios.
if not os.environ.get("SECRET_KEY"):
    key = secrets.token_hex(32)
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    lines = [line for line in lines if not line.startswith("SECRET_KEY=")] + [f"SECRET_KEY={key}"]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ["SECRET_KEY"] = key

from waitress import serve  # noqa: E402

from app import create_app  # noqa: E402


def local_ip():
    """IP deste PC na rede local (o que os colegas usam para aceder)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    # HOST=127.0.0.1 aceita só ligações deste PC (ex.: quando o acesso é feito pelo Cloudflare Tunnel).
    host = os.environ.get("HOST", "0.0.0.0")
    public_url = os.environ.get("PUBLIC_URL")
    app = create_app()
    print(f"\n  {app.config['COMPANY_NAME']} a correr.")
    print(f"  Neste PC:         http://localhost:{port}")
    if host == "0.0.0.0":
        print(f"  Na rede local:    http://{local_ip()}:{port}")
    if public_url:
        print(f"  Pela internet:    {public_url}")
    print("  Para parar: Ctrl+C\n")
    # O cloudflared liga-se a partir deste PC; confiar no esquema (https) que ele indica.
    serve(app, host=host, port=port, threads=8, trusted_proxy="127.0.0.1",
          trusted_proxy_headers={"x-forwarded-proto"}, clear_untrusted_proxy_headers=True)
