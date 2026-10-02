# -*- coding: utf-8 -*-
"""Gera as artes de divulgação do programa (QR code, posts, stories e Reels).

Uso:
    python tools\\divulgacao.py

Requisitos extras (SÓ para estas artes — o programa continua sem bibliotecas):
    python -m pip install pillow qrcode

Sai na pasta divulgacao\\:
    qr-release.png            QR code do link de download (quadrado)
    post-feed-1080x1080.png   arte para feed (Instagram/Facebook/LinkedIn)
    story-1080x1920.png       arte vertical para stories (com QR)
    capa-reels-1080x1920.png  capa de Reels/TikTok (texto no centro)

O QR e os links apontam para a página da release mais nova
(https://github.com/opusvix/controle-de-veiculos/releases/latest): quando
sair uma versão nova, estas artes continuam valendo sem mudar nada.

Os textos (legendas por rede e roteiro de Reels) ficam em
divulgacao\\DIVULGACAO.md.
"""
from __future__ import annotations

from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
PASTA_IMG = RAIZ / "imagens"
SAIDA = RAIZ / "divulgacao"

LINK = "https://github.com/opusvix/controle-de-veiculos/releases/latest"
LINK_CURTO = "github.com/opusvix/controle-de-veiculos/releases"

# cores do programa (controle_veiculos/ui/app.py)
AZUL = "#2563eb"        # ACCENT
AZUL_MEDIO = "#3b82f6"
AZUL_FUNDO = "#1d4ed8"
NOITE = "#1e3a8a"
TINTA = "#111827"       # texto do app
CINZA = "#5b6472"       # texto suave do app
NUVEM = "#dbeafe"       # texto claro sobre o azul
BRANCO = "#ffffff"


def _rgb(cor: str) -> tuple[int, int, int]:
    return tuple(int(cor[i:i + 2], 16) for i in (1, 3, 5))


def fonte(tam: int, *nomes: str) -> ImageFont.FreeTypeFont:
    pasta = Path("C:/Windows/Fonts")
    for nome in nomes:
        arquivo = pasta / nome
        if arquivo.exists():
            return ImageFont.truetype(str(arquivo), tam)
    return ImageFont.load_default()


F_REG = lambda tam: fonte(tam, "segoeui.ttf", "arial.ttf")          # normal
F_SEMI = lambda tam: fonte(tam, "seguisb.ttf", "segoeuib.ttf", "arialbd.ttf")
F_NEG = lambda tam: fonte(tam, "segoeuib.ttf", "arialbd.ttf")        # negrito


# ----------------------------------------------------------------- utilidades
def gradiente(w: int, h: int, topo: str, base: str) -> Image.Image:
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    c1, c2 = _rgb(topo), _rgb(base)
    for y in range(h):
        t = y / max(1, h - 1)
        cor = tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))
        d.line([(0, y), (w, y)], fill=cor)
    return img.convert("RGBA")


def cartao(img: Image.Image, box, raio: int = 24, cor: str = BRANCO,
           desloc=(8, 12), opacidade: int = 70) -> None:
    """Retângulo arredondado com sombra macia, desenhado sobre img."""
    x0, y0, x1, y1 = box
    sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(sombra)
    ds.rounded_rectangle((x0 + desloc[0], y0 + desloc[1],
                          x1 + desloc[0], y1 + desloc[1]),
                         raio, fill=(15, 23, 42, opacidade))
    img.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(16)))
    ImageDraw.Draw(img).rounded_rectangle(box, raio, fill=cor)


def quebra(d: ImageDraw.ImageDraw, texto: str, f, larg: int) -> list[str]:
    linhas, atual = [], ""
    for palavra in texto.split():
        candidato = (atual + " " + palavra).strip()
        if not atual or d.textlength(candidato, font=f) <= larg:
            atual = candidato
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def paragrafo(d, xy, texto, f, cor, larg, entrelinha, ancora="la") -> int:
    x, y = xy
    linhas = quebra(d, texto, f, larg)
    for i, linha in enumerate(linhas):
        d.text((x, y + i * entrelinha), linha, font=f, fill=cor, anchor=ancora)
    return y + len(linhas) * entrelinha


def icone(tam: int, raio: int | None = None) -> Image.Image:
    im = Image.open(PASTA_IMG / "icone.png").convert("RGBA")
    im = im.resize((tam, tam), Image.LANCZOS)
    if raio:
        mascara = Image.new("L", (tam, tam), 0)
        ImageDraw.Draw(mascara).rounded_rectangle((0, 0, tam - 1, tam - 1),
                                                  raio, fill=255)
        im.putalpha(mascara)
    return im


def encaixa(img: Image.Image, caminho: Path, cx: int, cy: int,
            larg_max: int, alt_max: int, moldura: int = 14) -> None:
    """Coloca uma captura de tela centralizada em (cx, cy), com moldura."""
    foto = Image.open(caminho).convert("RGB")
    esc = min((larg_max - 2 * moldura) / foto.width,
              (alt_max - 2 * moldura) / foto.height)
    foto = foto.resize((round(foto.width * esc), round(foto.height * esc)),
                       Image.LANCZOS)
    # cantos arredondados na captura
    mascara = Image.new("L", foto.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        (0, 0, foto.width - 1, foto.height - 1), 12, fill=255)
    foto = foto.convert("RGBA")
    foto.putalpha(mascara)

    cw = foto.width + 2 * moldura
    ch = foto.height + 2 * moldura
    box = (cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2)
    cartao(img, box, raio=20)
    img.alpha_composite(foto, (box[0] + moldura, box[1] + moldura))


def qr_pil(box_size: int) -> Image.Image:
    """QR do LINK no tamanho nativo (sem escala — fica nítido para leitura)."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=box_size, border=4)
    qr.add_data(LINK)
    qr.make(fit=True)
    img = qr.make_image(fill_color=TINTA, back_color="white")
    img = getattr(img, "_img", img)
    return img.convert("RGBA")


def cola_centro(destino: Image.Image, pedaco: Image.Image,
                cx: int, cy: int) -> None:
    if pedaco.mode != "RGBA":
        pedaco = pedaco.convert("RGBA")
    destino.alpha_composite(pedaco, (cx - pedaco.width // 2,
                                     cy - pedaco.height // 2))


def cabecalho(img: Image.Image, y: int, tam_icone: int, tam_fonte: int) -> None:
    d = ImageDraw.Draw(img)
    titulo = "Controle de Veículos"
    f = F_SEMI(tam_fonte)
    largura_titulo = d.textlength(titulo, font=f)
    total = tam_icone + 20 + largura_titulo
    x0 = int((img.width - total) / 2)
    img.alpha_composite(icone(tam_icone, raio=tam_icone // 4), (x0, y))
    d.text((x0 + tam_icone + 20, y + tam_icone // 2), titulo,
           font=f, fill=BRANCO, anchor="lm")


def pilula(d, cx: int, cy: int, texto: str, f, cor_txt=AZUL) -> None:
    w = d.textlength(texto, font=f)
    alt = f.size + 22
    box = (cx - w / 2 - 26, cy - alt / 2, cx + w / 2 + 26, cy + alt / 2)
    d.rounded_rectangle(box, alt // 2, fill=BRANCO)
    d.text((cx, cy), texto, font=f, fill=cor_txt, anchor="mm")


# ----------------------------------------------------------------- as artes
def gerar_qr() -> None:
    q = qr_pil(box_size=16)                     # ≈ 656 px nativos
    lado = q.width + 184                        # folga branca ao redor
    arte = Image.new("RGBA", (lado, lado), BRANCO)
    cola_centro(arte, q, lado // 2, lado // 2)

    # ícone do programa no centro (o QR aguenta: corrigir M cobre 15%)
    ic = icone(132)
    fundo = Image.new("RGBA", (176, 176), (0, 0, 0, 0))
    ImageDraw.Draw(fundo).rounded_rectangle((0, 0, 175, 175), 44, fill=BRANCO)
    fundo.alpha_composite(ic, (22, 22))
    cola_centro(arte, fundo, lado // 2, lado // 2)
    arte.convert("RGB").save(SAIDA / "qr-release.png")
    print(f"  qr-release.png ({lado}x{lado})")


def gerar_post() -> None:
    img = gradiente(1080, 1080, AZUL_MEDIO, AZUL_FUNDO)
    d = ImageDraw.Draw(img)

    # cabeçalho
    img.alpha_composite(icone(88, raio=22), (64, 54))
    d.text((172, 58), "Controle de Veículos", font=F_SEMI(46), fill=BRANCO)
    d.text((172, 116), "abastecimentos • manutenções • consumo",
           font=F_REG(26), fill=NUVEM)

    # manchete
    paragrafo(d, (64, 214), "Quanto você gastou no carro mês passado?",
              F_SEMI(60), BRANCO, 952, 74)

    # marcadores (coluna esquerda)
    itens = ["Abastecimentos e consumo por km",
             "Manutenção com lembrete",
             "Relatórios do gasto do mês",
             "Offline: dados só no seu PC"]
    y = 440
    f_item = F_REG(28)
    for texto in itens:
        d.ellipse((64, y, 96, y + 32), fill=BRANCO)
        # marca desenhada com linhas (fonte nenhuma garante o glifo ✓)
        d.line([(72, y + 16), (78, y + 23), (90, y + 8)],
               fill=AZUL, width=4, joint="curve")
        d.text((112, y + 16), texto, font=f_item, fill=BRANCO, anchor="lm")
        y += 60

    # captura da tela à direita
    encaixa(img, PASTA_IMG / "03-tela-inicial.png",
            cx=788, cy=578, larg_max=470, alt_max=336)

    # barra branca embaixo com o QR
    d.rounded_rectangle((0, 790, 1080, 1140), 48, fill=BRANCO)
    q = qr_pil(box_size=5)                       # ≈ 205 px nativos
    qx, qy = 64, 833
    d.rounded_rectangle((qx - 12, qy - 12, qx + q.width + 12,
                         qy + q.height + 12), 16, fill=BRANCO,
                        outline="#e5e7eb", width=3)
    img.alpha_composite(q, (qx, qy))

    tx = qx + q.width + 48
    d.text((tx, 848), "Escaneie e baixe grátis", font=F_SEMI(42), fill=TINTA)
    d.text((tx, 908), LINK_CURTO, font=F_REG(26), fill=AZUL)
    d.text((tx, 952), "Windows 10/11 • grátis • sem cadastro • sem internet",
           font=F_REG(24), fill=CINZA)

    img.convert("RGB").save(SAIDA / "post-feed-1080x1080.png")
    print("  post-feed-1080x1080.png (1080x1080)")


def gerar_story() -> None:
    img = gradiente(1080, 1920, AZUL_MEDIO, NOITE)
    d = ImageDraw.Draw(img)

    cabecalho(img, y=120, tam_icone=96, tam_fonte=46)
    d.text((540, 252), "abastecimentos • manutenções • consumo",
           font=F_REG(30), fill=NUVEM, anchor="ma")

    # manchete
    f_h = F_SEMI(80)
    linhas = quebra(d, "Quanto custa manter seu carro?", f_h, 900)
    y = 340
    for i, linha in enumerate(linhas):
        d.text((540, y + i * 94), linha, font=f_h, fill=BRANCO, anchor="ma")
    y_fim = y + len(linhas) * 94
    d.text((540, y_fim + 16), "Faça a conta em 2 minutos — de graça",
           font=F_REG(34), fill=NUVEM, anchor="ma")

    # captura grande
    encaixa(img, PASTA_IMG / "03-tela-inicial.png",
            cx=540, cy=905, larg_max=920, alt_max=580)

    # cartão do QR (acima da barra de resposta dos stories)
    box = (200, 1230, 880, 1770)
    cartao(img, box, raio=40)
    q = qr_pil(box_size=8)                       # ≈ 328 px nativos
    cola_centro(img, q, 540, 1280 + q.height // 2)
    d.text((540, 1648), "Aponte a câmera do celular", font=F_SEMI(34),
           fill=TINTA, anchor="ma")
    d.text((540, 1700), LINK_CURTO, font=F_REG(26), fill=AZUL, anchor="ma")

    img.convert("RGB").save(SAIDA / "story-1080x1920.png")
    print("  story-1080x1920.png (1080x1920)")


def gerar_capa_reels() -> None:
    img = gradiente(1080, 1920, AZUL_MEDIO, AZUL_FUNDO)
    d = ImageDraw.Draw(img)

    # topo só com o ícone (o nome já aparece na zona segura, embaixo)
    img.alpha_composite(icone(88, raio=22), ((1080 - 88) // 2, 130))

    # ---- zona segura (o recorte quadrado do feed pega y 420..1500) ----
    d.text((540, 452), "Controle de Veículos", font=F_SEMI(40),
           fill=NUVEM, anchor="ma")

    f_h = F_SEMI(84)
    linhas = quebra(d, "Quanto você gastou no carro mês passado?", f_h, 900)
    y = 520
    for i, linha in enumerate(linhas):
        d.text((540, y + i * 96), linha, font=f_h, fill=BRANCO, anchor="ma")
    y_fim = y + len(linhas) * 96

    pilula(d, 540, y_fim + 54, "grátis • offline • sem cadastro", F_SEMI(30))

    encaixa(img, PASTA_IMG / "03-tela-inicial.png",
            cx=540, cy=1200, larg_max=760, alt_max=520)

    # rodapé (fora do recorte quadrado: aparece só na tela cheia)
    d.text((540, 1545), "Baixe pelo link na bio", font=F_SEMI(40),
           fill=BRANCO, anchor="ma")

    img.convert("RGB").save(SAIDA / "capa-reels-1080x1920.png")
    print("  capa-reels-1080x1920.png (1080x1920)")


def main() -> int:
    SAIDA.mkdir(exist_ok=True)
    print("Gerando as artes de divulgacao em divulgacao\\:")
    gerar_qr()
    gerar_post()
    gerar_story()
    gerar_capa_reels()
    print("Pronto. Legendas e roteiro: divulgacao\\DIVULGACAO.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
