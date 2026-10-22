"""Monta o site estático (GitHub Pages) na pasta docs\\.

Copia para docs\\app\\ o que a demonstração online precisa, tirando de
web\\ (fonte única - o mesmo arquivo que vai dentro do pacote do programa):

    web\\controle-veiculos.html  ->  docs\\app\\index.html
    web\\INSTALAR-COMO-USAR.txt  ->  docs\\app\\INSTALAR-COMO-USAR.txt
    INSTALAR-COMO-USAR.md        ->  docs\\app\\INSTALAR-COMO-USAR.md

e leva as fotos usadas pela landing para docs\\imagens\\.

A landing (docs\\index.html) é editada à mão; o app vem sempre do
repositório - mude em web\\ e rode isto de novo (a suíte cobra cópias
idênticas, igual faz com os manuais .txt).

Uso:
    python tools\\publicar_site.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"

# origem (relativa à raiz) -> destino (relativa a docs\)
APP = {
    "web/controle-veiculos.html": "app/index.html",
    "web/INSTALAR-COMO-USAR.txt": "app/INSTALAR-COMO-USAR.txt",
    "INSTALAR-COMO-USAR.md": "app/INSTALAR-COMO-USAR.md",
}
FOTOS = [
    "03-tela-inicial.png",
    "05-manutencoes.png",
    "06-relatorios.png",
    "08-celular.png",
    "09-tela-acesso.png",
]


def main() -> int:
    print("Montando o site em docs\\:")
    faltando = [origem for origem in APP if not (RAIZ / origem).exists()]
    faltando += [f"imagens/{f}" for f in FOTOS
                 if not (RAIZ / "imagens" / f).exists()]
    if faltando:
        print("  faltam arquivos de origem: " + ", ".join(faltando))
        return 1

    for origem, destino in APP.items():
        alvo = DOCS / destino
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RAIZ / origem, alvo)
        print(f"  ok: {destino}")

    for foto in FOTOS:
        alvo = DOCS / "imagens" / foto
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RAIZ / "imagens" / foto, alvo)
        print(f"  ok: imagens/{foto}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
