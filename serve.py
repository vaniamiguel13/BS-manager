"""Servidor para correr a plataforma num PC (Windows, macOS ou Linux) sem Docker.

Uso: python serve.py   (lê as definições do ficheiro .env, se existir)
"""
import errno
import os
import secrets
import socket
import stat
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


def open_env_file(flags, mode=None):
    """Open .env without following symlinks where the platform supports it."""
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    if not no_follow and ENV_FILE.is_symlink():
        raise RuntimeError("Refusing to read or write a symlinked .env file.")
    try:
        fd = os.open(ENV_FILE, flags | no_follow, mode) if mode is not None else os.open(ENV_FILE, flags | no_follow)
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise RuntimeError("Refusing to read or write a symlinked .env file.") from error
        raise
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise RuntimeError("The .env path must be a regular file.")
    return fd


try:
    env_fd = open_env_file(os.O_RDONLY)
except FileNotFoundError:
    pass
else:
    with os.fdopen(env_fd, "r", encoding="utf-8") as env_stream:
        load_dotenv(stream=env_stream)

# Sem SECRET_KEY, gera uma aleatória e guarda-a no .env para as sessões sobreviverem a reinícios.
if not os.environ.get("SECRET_KEY"):
    key = secrets.token_hex(32)
    env_fd = open_env_file(os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(env_fd, 0o600)
        else:  # Windows exposes chmod but not fchmod; mode is best-effort there.
            os.chmod(ENV_FILE, 0o600)
        with os.fdopen(env_fd, "r+", encoding="utf-8") as env_file:
            env_fd = -1
            lines = env_file.read().splitlines()
            lines = [line for line in lines if not line.startswith("SECRET_KEY=")] + [f"SECRET_KEY={key}"]
            env_file.seek(0)
            env_file.truncate()
            env_file.write("\n".join(lines) + "\n")
            env_file.flush()
            os.fsync(env_file.fileno())
    finally:
        if env_fd >= 0:
            os.close(env_fd)
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
    host = os.environ.get("HOST", "127.0.0.1")
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
