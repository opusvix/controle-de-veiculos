"""Onde estão os arquivos do próprio programa (manual, pasta web, servidor).

No programa compilado (.exe) tudo é procurado ao lado do executável - por isso
o instalador leva a pasta web\\, as imagens e os manuais junto.
"""
from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path

MANUAL_TXT = "INSTALAR-COMO-USAR.txt"
MANUAL_MD = "INSTALAR-COMO-USAR.md"
URL_LOCAL = "http://127.0.0.1:8000/controle-veiculos.html"


def raiz_programa() -> Path:
    """Pasta onde está o programa (ao lado do .exe, ou a raiz do código)."""
    if getattr(sys, "frozen", False):  # rodando como .exe compilado
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def pasta_web() -> Path:
    return raiz_programa() / "web"


def caminho_manual() -> Path | None:
    """Acha o manual em texto (e, na falta, em .md). None = não encontrou."""
    raiz = raiz_programa()
    candidatos = [
        raiz / MANUAL_TXT,
        raiz / MANUAL_MD,
        raiz / "web" / MANUAL_TXT,
        Path.cwd() / MANUAL_TXT,
        Path.cwd() / MANUAL_MD,
    ]
    for caminho in candidatos:
        try:
            if caminho.exists():
                return caminho
        except OSError:
            continue
    return None


def abrir_manual() -> str | None:
    """Abre o manual com o programa padrão do Windows. Devolve erro (ou None)."""
    caminho = caminho_manual()
    if caminho is None:
        return ("Não encontrei o arquivo do manual.\n\n"
                f"Procurei por \"{MANUAL_TXT}\" na pasta:\n{raiz_programa()}")
    try:
        os.startfile(str(caminho))  # noqa: S606 - abre no programa padrão do Windows
    except OSError as exc:
        return f"Não consegui abrir o manual:\n{caminho}\n\n{exc}"
    return None


def servidor_disponivel() -> bool:
    return (pasta_web() / "Servidor Wi-Fi.bat").exists()


def iniciar_servidor() -> bool:
    """Liga o Servidor Wi-Fi numa janela nova. False se não existir o .bat."""
    bat = pasta_web() / "Servidor Wi-Fi.bat"
    if not bat.exists():
        return False
    try:
        subprocess.Popen(
            [str(bat)],
            cwd=str(bat.parent),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    except OSError:
        return False
    return True


def esperar_servidor(timeout: float = 12.0) -> bool:
    """Espera o servidor responder (dá tempo de o .bat subir)."""
    import time
    import urllib.request

    limite = time.time() + timeout
    while time.time() < limite:
        try:
            with urllib.request.urlopen(URL_LOCAL, timeout=2) as resposta:
                if getattr(resposta, "status", 200) == 200:
                    return True
        except Exception:  # noqa: BLE001 - ainda subindo: tenta de novo
            time.sleep(0.3)
    return False


def abrir_versao_web() -> str | None:
    """Abre a versão web no navegador padrão. Devolve erro (ou None)."""
    if not esperar_servidor():
        return ("O servidor não respondeu.\n\n"
                "Olhe a janela preta que abriu: se houver mensagem de erro, "
                "feche a janela e tente de novo.")
    try:
        webbrowser.open(URL_LOCAL)
    except Exception as exc:  # noqa: BLE001 - navegador ausente/raro
        return f"Não consegui abrir o navegador:\n{exc}"
    return None
