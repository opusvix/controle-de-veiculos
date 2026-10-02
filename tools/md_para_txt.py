"""Converte os manuais .md em .txt (texto puro, para o Bloco de Notas).

Gera na raiz:
    INSTALAR-COMO-USAR.txt
    README.txt
e copia os dois para a pasta web\\, para que o celular também consiga
abrir o help pelo Servidor Wi-Fi (que serve só a pasta web\\).

Uso:
    python tools\\md_para_txt.py
"""
from __future__ import annotations

import re
import sys
import textwrap
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"

# nome do arquivo .md -> texto do cabeçalho do .txt
CABECALHOS = {
    "INSTALAR-COMO-USAR.txt": (
        "CONTROLE DE VEICULOS - COMO INSTALAR E USAR (versao em texto)",
        "Este e o mesmo guia de INSTALAR-COMO-USAR.md, em texto puro para abrir "
        "no Bloco de Notas. Onde no original ha uma foto aparece [foto: ...] - "
        "as imagens estao na pasta imagens\\.",
    ),
    "README.txt": (
        "CONTROLE DE VEICULOS - LEIA-ME (versao em texto)",
        "Este e o mesmo arquivo README.md, em texto puro para abrir no Bloco de "
        "Notas. As fotos do original aparecem como [foto: ...].",
    ),
}

RE_IMG = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
RE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]*)\)")
RE_CODE = re.compile(r"`([^`]+)`")
RE_BOLD = re.compile(r"\*\*([^*]+)\*\*")
RE_ITAL = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
RE_SEP_TABELA = re.compile(r":?-{2,}:?")


def _link(texto: str, alvo: str) -> str:
    texto = texto.replace("`", "").strip()
    alvo = (alvo or "").strip()
    if not alvo or alvo.startswith("#"):  # atalho interno: só o texto
        return texto
    if texto == alvo or texto.rstrip(".") == alvo:
        return alvo
    if alvo.startswith("http"):
        return f"{texto} ({alvo})"
    return f"{texto} [{alvo}]"


def inline(linha: str) -> str:
    """Tira a formatação markdown de uma linha, deixando legível no Notepad."""
    # fotos primeiro (senão o [texto](caminho) da foto vira link)
    linha = RE_IMG.sub(lambda m: f"[foto: {m.group(1).strip()}]" if m.group(1).strip() else "[foto]",
                       linha)
    linha = RE_LINK.sub(lambda m: _link(m.group(1), m.group(2)), linha)
    linha = RE_CODE.sub(lambda m: f'"{m.group(1)}"', linha)
    linha = RE_BOLD.sub(r"\1", linha)
    linha = RE_ITAL.sub(r"\1", linha)
    return linha


def _celulas(linha: str) -> list[str]:
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def largura(texto: str) -> int:
    """Largura visível (emoji/símbolos contam como 2 colunas, acentos como 1)."""
    total = 0
    for ch in texto:
        cod = ord(ch)
        if unicodedata.combining(ch):
            total += 0
        elif 0x2600 <= cod <= 0x27BF or 0x1F000 <= cod <= 0x1FAFF or cod == 0xFE0F:
            total += 2
        else:
            total += 1
    return total


def _preenche(texto: str, w: int) -> str:
    return texto + " " * max(0, w - largura(texto))


LARGURA_MAX = 96  # largura máxima de uma linha de tabela no Notepad
COL_MIN = 14


def _tabela(bloco: list[str], saida: list[str]) -> None:
    linhas = [[inline(c) for c in _celulas(l)] for l in bloco]
    corpo = [l for l in linhas if not all(RE_SEP_TABELA.fullmatch(c) for c in l)]
    if not corpo:
        return
    ncols = max(len(l) for l in corpo)
    corpo = [l + [""] * (ncols - len(l)) for l in corpo]

    larguras = [max(largura(l[i]) for l in corpo) for i in range(ncols)]
    # encolhe as colunas mais largas até a linha caber em LARGURA_MAX
    while sum(larguras) + 2 * (ncols - 1) > LARGURA_MAX and max(larguras) > COL_MIN:
        i = larguras.index(max(larguras))
        larguras[i] -= 1

    for n, l in enumerate(corpo):
        quebradas = [textwrap.wrap(c, width=max(w, 4), break_long_words=True) or [""]
                     for c, w in zip(l, larguras)]
        for linha in range(max(len(q) for q in quebradas)):
            celulas = [_preenche(q[linha] if linha < len(q) else "", w)
                       for q, w in zip(quebradas, larguras)]
            saida.append("  ".join(celulas).rstrip())
        if n == 0:  # sob o cabeçalho, uma linha de traços
            saida.append("  ".join("-" * w for w in larguras))
    saida.append("")


def md_para_txt(md: str) -> str:
    saida: list[str] = []
    em_codigo = False
    tabela: list[str] = []

    def fecha_tabela() -> None:
        if tabela:
            _tabela(tabela, saida)
            tabela.clear()

    for bruta in md.split("\n"):
        linha = bruta.rstrip()

        if linha.lstrip().startswith("```"):
            fecha_tabela()
            em_codigo = not em_codigo
            saida.append("")
            continue
        if em_codigo:
            saida.append(("    " + linha).rstrip() if linha.strip() else "")
            continue

        if linha.startswith("|"):  # tabela: junta e desenha depois
            tabela.append(linha)
            continue
        fecha_tabela()

        # citação (> ...) - vira texto indentado
        citacao = False
        if re.match(r"^>\s?", linha):
            citacao = True
            linha = re.sub(r"^>\s?", "", linha)
            if not linha.strip():
                saida.append("")
                continue

        # títulos
        m = re.match(r"^(#{1,6})\s+(.*)$", linha)
        if m and not citacao:
            nivel, texto = len(m.group(1)), inline(m.group(2)).strip()
            saida.append("")
            if nivel == 1:
                saida += [texto, "=" * max(len(texto), 8), ""]
            elif nivel == 2:
                saida += [texto, "-" * max(len(texto), 8), ""]
            else:
                saida += [">>> " + texto, ""]
            continue

        # régua horizontal
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", linha.strip()):
            fecha_tabela()
            saida += ["", "-" * 60, ""]
            continue

        texto = inline(linha)
        if citacao:
            saida.append(("    " + texto).rstrip())
            continue
        if not texto.strip():
            saida.append("")
            continue

        # listas comuns (mantém marcador/numeração)
        m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", texto)
        if m:
            recuo, marc, resto = m.group(1), m.group(2), m.group(3)
            if marc in "-*+":
                marc = "-"
            saida.append(f"{recuo}{marc} {resto}".rstrip())
            continue
        saida.append(texto.rstrip())

    fecha_tabela()

    # limpa linhas em branco repetidas
    limpo: list[str] = []
    for l in saida:
        if not l.strip() and limpo and not limpo[-1].strip():
            continue
        limpo.append(l)
    while limpo and not limpo[0].strip():
        limpo.pop(0)
    while limpo and not limpo[-1].strip():
        limpo.pop()
    return "\n".join(limpo) + "\n"


def gerar(nome_txt: str, nome_md: str, destinos: list[Path]) -> None:
    origem = RAIZ / nome_md
    if not origem.exists():
        raise SystemExit(f"Nao encontrei {origem}")
    titulo, nota = CABECALHOS[nome_txt]
    corpo = md_para_txt(origem.read_text(encoding="utf-8"))
    barra = "=" * 66
    nota_quebrada = textwrap.fill(nota, width=96)
    texto = (f"{barra}\n {titulo}\n{barra}\n\n{nota_quebrada}\n\n{barra}\n\n{corpo}")
    for alvo in destinos:
        alvo.parent.mkdir(parents=True, exist_ok=True)
        with open(alvo, "w", encoding="utf-8", newline="\r\n") as fh:
            fh.write(texto)
        print(f"  ok: {alvo.relative_to(RAIZ)}  ({len(texto.splitlines())} linhas)")


def main() -> int:
    print("Gerando os manuais em texto (.txt):")
    for nome_md, nome_txt in [("INSTALAR-COMO-USAR.md", "INSTALAR-COMO-USAR.txt"),
                              ("README.md", "README.txt")]:
        gerar(nome_txt, nome_md, [RAIZ / nome_txt, WEB / nome_txt])
    return 0


if __name__ == "__main__":
    sys.exit(main())
