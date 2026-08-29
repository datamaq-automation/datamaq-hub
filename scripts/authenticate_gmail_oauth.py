#!/usr/bin/env python3
"""Script interactivo para autorizar una cuenta de Google Workspace / Gmail y obtener el REFRESH_TOKEN."""

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import re

from src.infrastructure.pydantic.config import get_settings

SCOPES = [
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/userinfo.email",
]


def extract_auth_code(raw_input: str) -> str:
    """Extrae de forma robusta el código de autorización desde URL, headers HTTP o texto copiado."""
    raw = raw_input.strip()
    match = re.search(r"code=([^&\s]+)", raw)
    if match:
        return urllib.parse.unquote(match.group(1))
    match_code = re.search(r"(4/[a-zA-Z0-9_\-]+)", raw)
    if match_code:
        return match_code.group(1)
    return raw


def copy_to_clipboard(text: str) -> bool:
    """Copia el texto al portapapeles del sistema operativo usando xclip, wl-copy o xsel."""
    commands = [
        ["xclip", "-selection", "clipboard"],
        ["xclip", "-selection", "primary"],
        ["wl-copy"],
        ["xsel", "--clipboard", "--input"],
    ]
    for cmd in commands:
        try:
            p = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            p.communicate(input=text.encode("utf-8"))
            if p.returncode == 0:
                return True
        except (subprocess.SubprocessError, OSError):
            continue
    return False


class TemporaryPortManager:
    """Libera temporalmente el puerto especificado deteniendo el proceso que lo usa y restaurándolo al salir."""

    def __init__(self, port: int) -> None:
        self.port = port
        self.saved_processes: list[tuple[list[str], str]] = []

    def __enter__(self):
        pids: list[int] = []
        try:
            out = subprocess.check_output(
                ["lsof", "-ti", f":{self.port}"], text=True
            ).strip()
            pids = [int(p) for p in out.splitlines() if p.isdigit()]
        except (subprocess.SubprocessError, OSError):
            pids = []

        for pid in pids:
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    raw_cmd = f.read().split(b"\x00")
                    cmd = [c.decode("utf-8", errors="ignore") for c in raw_cmd if c]
                cwd = os.readlink(f"/proc/{pid}/cwd")
                if cmd:
                    proc_name = Path(cmd[0]).name
                    print(
                        f"⚠️ Puerto {self.port} ocupado por '{proc_name}' (PID {pid}). Pausando temporalmente..."
                    )
                    os.kill(pid, signal.SIGTERM)
                    self.saved_processes.append((cmd, cwd))
            except (OSError, RuntimeError) as e:
                print(f"No se pudo pausar proceso PID {pid}: {e}")

        if self.saved_processes:
            # Esperar hasta que el puerto quede liberado
            for _ in range(15):
                time.sleep(0.2)
                try:
                    s = socket.socket()
                    s.settimeout(0.5)
                    s.bind(("0.0.0.0", self.port))
                    s.close()
                    break
                except OSError:
                    continue

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for cmd, cwd in self.saved_processes:
            proc_name = Path(cmd[0]).name
            print(f"\n🔄 Restaurando proceso '{proc_name}' en segundo plano...")
            try:
                subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except (subprocess.SubprocessError, OSError) as e:
                print(f"Error restaurando '{proc_name}': {e}")


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Manejador HTTP simple para recibir el callback de autorización de Google."""

    auth_code: str | None = None
    error: str | None = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<h1>Autorizacion Exitosa!</h1><p>Ya podes volver a la terminal. El Hub esta guardando tu refresh_token.</p>"
            )
        elif "error" in params:
            OAuthCallbackHandler.error = params["error"][0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                f"<h1>Error de Autorizacion: {OAuthCallbackHandler.error}</h1>".encode()
            )
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Silenciar logs HTTP en consola


def exchange_code_for_tokens(
    code: str, client_id: str, client_secret: str, redirect_uri: str
) -> dict:
    """Canjea el código de autorización por tokens de acceso y actualización."""
    token_url = "https://oauth2.googleapis.com/token"
    payload = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        token_url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8", errors="ignore")
        print(f"\n❌ Error al canjear el código con Google ({e.code}): {error_msg}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Genera el REFRESH_TOKEN de Google Workspace / Gmail para Datamaq Hub."
    )
    parser.add_argument(
        "--email",
        "-e",
        default="agustinbustos@abc.gob.ar",
        help="Email a autorizar (default: agustinbustos@abc.gob.ar)",
    )
    parser.add_argument(
        "--client-id",
        help="Google OAuth Client ID (default: tomado de .env GOOGLE_ADS_CLIENT_ID)",
    )
    parser.add_argument(
        "--client-secret",
        help="Google OAuth Client Secret (default: tomado de .env GOOGLE_ADS_CLIENT_SECRET)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Puerto local para recibir el callback (default: 8080)",
    )
    parser.add_argument(
        "--variant",
        choices=[
            "localhost_slash",
            "localhost",
            "ip_slash",
            "ip",
            "playground",
        ],
        default="localhost_slash",
        help="Formato exacto del Redirect URI autorizado en GCP (default: localhost_slash = http://localhost:8080/)",
    )
    parser.add_argument(
        "--redirect-uri",
        help="URL de redirección personalizada exacta registrada en GCP",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Modo manual (copiar y pegar código desde consola)",
    )
    args = parser.parse_args()

    settings = get_settings()
    client_id = args.client_id or settings.google_ads_client_id
    client_secret = args.client_secret or settings.google_ads_client_secret

    if not client_id or not client_secret:
        print("❌ Error: No se encontró Client ID o Client Secret de Google.")
        print(
            "   Asegurate de que GOOGLE_ADS_CLIENT_ID y GOOGLE_ADS_CLIENT_SECRET estén en .env"
        )
        print("   o pasalos con --client-id y --client-secret.")
        sys.exit(1)

    if args.redirect_uri:
        redirect_uri = args.redirect_uri
    elif args.variant == "localhost_slash":
        redirect_uri = f"http://localhost:{args.port}/"
    elif args.variant == "localhost":
        redirect_uri = f"http://localhost:{args.port}"
    elif args.variant == "ip_slash":
        redirect_uri = f"http://127.0.0.1:{args.port}/"
    elif args.variant == "ip":
        redirect_uri = f"http://127.0.0.1:{args.port}"
    elif args.variant == "playground":
        redirect_uri = "https://developers.google.com/oauthplayground"
        args.manual = True
    else:
        redirect_uri = f"http://localhost:{args.port}/"

    if args.manual and not args.redirect_uri and args.variant != "playground":
        redirect_uri = "urn:ietf:wg:oauth:2.0:oob"

    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "select_account consent",
        "login_hint": args.email,
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(auth_params)}"

    print("\n" + "=" * 70)
    print("🔐 \033[1;36mAUTORIZACIÓN GOOGLE WORKSPACE / GMAIL (OAUTH 2.0)\033[0m")
    print("=" * 70)
    print(f"Cuenta objetivo: \033[1;33m{args.email}\033[0m")
    print(f"Redirect URI:    \033[1;36m{redirect_uri}\033[0m\n")

    copied = copy_to_clipboard(auth_url)
    if copied:
        print(
            "📋 \033[1;32mURL de autorización copiada automáticamente al portapapeles!\033[0m"
        )
        print(
            "   (Solo tenés que abrir tu ventana de incógnito y presionar \033[1mCtrl+V\033[0m).\n"
        )

    code = None

    try:
        if (
            not args.manual
            and "localhost" in redirect_uri
            or "127.0.0.1" in redirect_uri
        ):
            with TemporaryPortManager(args.port):
                HTTPServer.allow_reuse_address = True
                server = HTTPServer(("0.0.0.0", args.port), OAuthCallbackHandler)

                print("1. Abriendo navegador...")
                print(f"   \033[1;34m{auth_url}\033[0m\n")

                try:
                    webbrowser.open(auth_url)
                except (webbrowser.Error, OSError):
                    pass

                print(f"2. Esperando autorización en {redirect_uri}...")
                try:
                    server.handle_request()
                finally:
                    server.server_close()

                code = OAuthCallbackHandler.auth_code

            if not code:
                print(
                    f"\n❌ Error: No se recibió el código de autorización ({OAuthCallbackHandler.error})."
                )
                sys.exit(1)

        if args.manual or not code:
            print("1. Ingresá a este enlace en tu navegador:")
            print(f"\n   \033[1;34m{auth_url}\033[0m\n")
            raw_input = input(
                "2. Pegá acá el código o la URL completa de la redirección: "
            ).strip()
            code = extract_auth_code(raw_input)

        print("\n⏳ Canjeando código por REFRESH_TOKEN...")
        tokens = exchange_code_for_tokens(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )

        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            print(
                "⚠️ Google devolvió tokens pero sin refresh_token (es posible que ya estuviera autorizada)."
            )
            refresh_token = tokens.get("access_token", "")

        print("\n" + "=" * 70)
        print("✅ \033[1;32mREFRESH TOKEN OBTENIDO CON ÉXITO!\033[0m")
        print("=" * 70)
        config_dict = {
            "abc": {
                "host": "imap.gmail.com",
                "port": 993,
                "user": args.email,
                "oauth2_client_id": client_id,
                "oauth2_client_secret": client_secret,
                "oauth2_refresh_token": refresh_token,
                "use_ssl": True,
                "timeout_seconds": 15,
            }
        }
        json_str = json.dumps(config_dict)
        print(
            "\nCopiá y pegá esta línea en tu archivo .env (tanto en local como en VPS):\n"
        )
        print(f"\033[1;32mMAIL_ACCOUNTS={json_str}\033[0m\n")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n🛑 Operación cancelada por el usuario.")
        sys.exit(0)


if __name__ == "__main__":
    main()
