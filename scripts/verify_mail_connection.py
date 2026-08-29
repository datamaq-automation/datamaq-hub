#!/usr/bin/env python3
"""Diagnostic script to verify IMAP mail connectivity for configured accounts."""

import argparse
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.adapters.gateways.imap_mail_gateway import ImapMailGateway
from src.domain.mail.exceptions import (
    AccountNotFoundError,
    MailAuthenticationError,
    MailConnectionError,
    MailDomainException,
)
from src.infrastructure.pydantic.config import get_settings


def verify_account(alias: str, settings) -> bool:
    """Tests IMAP connectivity for a single account alias."""
    print(f"\n🔍 Probando conexión IMAP para la cuenta: \033[1;36m{alias}\033[0m")
    try:
        config = settings.get_mail_account_config(alias)
    except AccountNotFoundError as e:
        print(f"❌ \033[1;31mError:\033[0m {e.message}")
        return False

    print(f"  • Servidor: {config.host}:{config.port} (SSL: {config.use_ssl})")
    print(f"  • Usuario:  {config.user}")
    print(f"  • Timeout:  {config.timeout_seconds}s")

    gateway = ImapMailGateway(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        use_ssl=config.use_ssl,
        timeout_seconds=config.timeout_seconds,
    )

    t0 = time.perf_counter()
    try:
        folders = gateway.get_folders()
        elapsed = (time.perf_counter() - t0) * 1000.0
        print(
            f"✅ \033[1;32mConexión y autenticación exitosa\033[0m ({elapsed:.1f}ms)!"
        )
        print(f"  • Total de carpetas encontradas: {len(folders)}")
        for f in folders[:10]:
            unread_str = (
                f"\033[1;33m{f.no_leidos} sin leer\033[0m"
                if f.no_leidos > 0
                else "0 sin leer"
            )
            print(f"    - [{f.nombre}] {f.total_mensajes} mensajes ({unread_str})")
        if len(folders) > 10:
            print(f"    ... y {len(folders) - 10} carpetas más.")
        return True

    except MailAuthenticationError as e:
        elapsed = (time.perf_counter() - t0) * 1000.0
        print(f"❌ \033[1;31mFalla de Autenticación\033[0m ({elapsed:.1f}ms):")
        print(f"   {e.message}")
        if "AUTHENTICATIONFAILED" in e.message or "Invalid credentials" in e.message:
            print(
                "\n💡 \033[1;33mDiagnóstico:\033[0m El servidor rechazó la contraseña provista."
            )
            if "gmail.com" in config.host:
                print(
                    "   Google Workspace requiere una 'Contraseña de Aplicación' de 16 caracteres"
                )
                print(
                    "   o que la autenticación IMAP básica esté autorizada para esa cuenta."
                )
        return False

    except MailConnectionError as e:
        elapsed = (time.perf_counter() - t0) * 1000.0
        print(f"❌ \033[1;31mError de Conexión\033[0m ({elapsed:.1f}ms):")
        print(f"   {e.message}")
        return False

    except MailDomainException as e:
        elapsed = (time.perf_counter() - t0) * 1000.0
        print(f"❌ \033[1;31mError de Dominio Mail\033[0m ({elapsed:.1f}ms): {e}")
        return False

    except Exception as e:  # noqa: BLE001
        elapsed = (time.perf_counter() - t0) * 1000.0
        print(f"❌ \033[1;31mExcepción Inesperada\033[0m ({elapsed:.1f}ms): {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Verifica la conexión IMAP de las cuentas configuradas en .env."
    )
    parser.add_argument(
        "--account",
        "-a",
        default="abc",
        help="Alias de la cuenta a probar (ej: abc, datamaq, all). Default: abc",
    )
    args = parser.parse_args()

    settings = get_settings()

    if args.account == "all":
        accounts = list(settings.mail_accounts.keys())
        if not accounts:
            accounts = [settings.default_mail_account]
        print(f"Probando {len(accounts)} cuentas configuradas...")
        success = all(verify_account(acc, settings) for acc in accounts)
    else:
        success = verify_account(args.account, settings)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
