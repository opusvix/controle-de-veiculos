"""Ponto de entrada do aplicativo Controle de Veículos."""
from __future__ import annotations

import sys

from controle_veiculos.ui.app import App
from controle_veiculos.ui.login import LoginWindow


def main() -> int:
    # Tela de acesso: primeiro usuário/senha (local) e a escolha do modo.
    login = LoginWindow()
    login.mainloop()
    modo = login.modo
    if not modo:  # fechou sem entrar
        login.destroy()
        return 0

    if modo in ("computador", "smartphone"):
        # O Servidor Wi-Fi já foi ligado pela tela de acesso.
        login.destroy()
        return 0

    login.destroy()
    try:
        app = App(ask_folder=True)
    except Exception as exc:  # noqa: BLE001 - informar qualquer falha de abertura
        print(f"Falha ao iniciar: {exc}", file=sys.stderr)
        return 1
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
