"""Monta o zip da release (Controle-de-veiculos.zip) com os arquivos ATUAIS.

Usa a mesma lista das 23 entradas que o pacote sempre teve: instalador,
programa (dist\\), versao web para o celular (web\\), fotos (imagens\\) e
os guias .md/.txt. Nada de pasta-raiz dentro do zip.

Uso:
    python tools\\gerar_zip.py            # grava .\\Controle-de-veiculos.zip
    python tools\\gerar_zip.py C:\\x\\a.zip   # destino outro
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# as entradas do pacote (barra para frente, sem pasta-raiz)
ENTRADAS = [
    "Instalar.bat",
    "README.md",
    "README.txt",
    "INSTALAR-COMO-USAR.md",
    "INSTALAR-COMO-USAR.txt",
    "dist/Controle de Veículos.exe",
    "tools/instalar.ps1",
    "web/controle-veiculos.html",
    "web/servidor.py",
    "web/servidor-wifi.ps1",
    "web/Servidor Wi-Fi.bat",
    "web/INSTALAR-COMO-USAR.txt",
    "web/README.txt",
    "imagens/01-instalar.png",
    "imagens/02-pasta-dados.png",
    "imagens/03-tela-inicial.png",
    "imagens/04-cadastrar-veiculo.png",
    "imagens/05-manutencoes.png",
    "imagens/06-relatorios.png",
    "imagens/07-servidor-wifi.png",
    "imagens/08-celular.png",
    "imagens/09-tela-acesso.png",
    "imagens/icone.png",
]


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "Controle-de-veiculos.zip"

    faltando = [e for e in ENTRADAS if not (RAIZ / e).is_file()]
    if faltando:
        print("faltam arquivos para o zip: " + ", ".join(faltando))
        return 1

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for entrada in ENTRADAS:
            z.write(RAIZ / entrada, entrada)

    with zipfile.ZipFile(destino) as z:
        nomes = z.namelist()
        quebrado = z.testzip()
    if len(nomes) != len(ENTRADAS) or set(nomes) != set(ENTRADAS) or quebrado:
        print(f"zip inconsistente: {len(nomes)} entradas, quebrado={quebrado}")
        return 1
    print(f"ok: {destino}  ({len(nomes)} entradas, {destino.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
