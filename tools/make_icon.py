"""Gera o ícone do aplicativo (mostrador de velocímetro).

Saída: assets/controle_veiculos.ico (usado pelo PyInstaller) e assets/preview.png
para conferência visual. Sem dependências externas.

Uso: python tools/make_icon.py
"""
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

BLUE = (0x25, 0x63, 0xEB, 255)
WHITE = (255, 255, 255, 255)
SS = 4  # supersampling: renderiza 4x e reduz com média (antialias)


def _round_rect_alpha(x: float, y: float, size: float, radius: float) -> bool:
    nx = max(radius - x, 0.0, x - (size - 1 - radius))
    ny = max(radius - y, 0.0, y - (size - 1 - radius))
    return nx * nx + ny * ny <= radius * radius


def render(size: int) -> list[list[tuple[int, int, int, int]]]:
    """Retorna a imagem RGBA (top-down) no tamanho final."""
    big = size * SS
    cx = cy = (big - 1) / 2.0
    ring_radius = big * 0.36
    ring_half = big * 0.055
    corner = big * 0.22
    hub = big * 0.085
    needle_len = ring_radius + ring_half * 0.7
    needle_half = big * 0.05

    angle = math.radians(-58.0)  # ponteiro apontando para cima/direita
    ux, uy = math.cos(angle), math.sin(angle)

    acc = [[0, 0, 0, 0] for _ in range(size * size)]

    for py in range(big):
        iy = py // SS
        for px in range(big):
            ix = px // SS
            inside = _round_rect_alpha(px, py, big, corner)
            if not inside:
                continue

            dx, dy = px - cx, py - cy
            dist = math.hypot(dx, dy)
            a = math.degrees(math.atan2(dy, dx)) % 360.0

            on_ring = abs(dist - ring_radius) <= ring_half and not (28.0 < a < 152.0)

            # ponteiro (triângulo que afina na ponta)
            t = dx * ux + dy * uy
            on_needle = False
            if 0.0 <= t <= needle_len:
                perp = abs(dx * uy - dy * ux)
                half = needle_half * (1.0 - 0.75 * max(t, 0.0) / needle_len)
                on_needle = perp <= half

            on_hub = dist <= hub

            if on_ring or on_needle or on_hub:
                r, g, b, alpha = WHITE
            else:
                r, g, b, alpha = BLUE

            cell = acc[iy * size + ix]
            cell[0] += r
            cell[1] += g
            cell[2] += b
            cell[3] += alpha

    scale = 1.0 / (SS * SS)
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            cell = acc[y * size + x]
            row.append((
                int(cell[0] * scale + 0.5),
                int(cell[1] * scale + 0.5),
                int(cell[2] * scale + 0.5),
                int(cell[3] * scale + 0.5),
            ))
        rows.append(row)
    return rows


def encode_bmp(size: int, rows) -> bytes:
    """Bitmap de 32 bits (BGRA, bottom-up) + máscara AND, formato de ícone."""
    header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, 0, 0, 0, 0, 0)
    xor = b"".join(
        bytes((b, g, r, a)) for row in reversed(rows) for (r, g, b, a) in row
    )
    row_bytes = ((size + 31) // 32) * 4
    and_mask = b""
    for row in reversed(rows):
        line = bytearray(row_bytes)
        for i, (_, _, _, a) in enumerate(row):
            if a < 128:
                line[i // 8] |= 0x80 >> (i % 8)
        and_mask += bytes(line)
    return header + xor + and_mask


def write_ico(path: Path, images: dict[int, bytes]) -> None:
    sizes = sorted(images)
    offset = 6 + 16 * len(sizes)
    out = [struct.pack("<HHH", 0, 1, len(sizes))]
    for size in sizes:
        blob = images[size]
        side = 0 if size >= 256 else size
        out.append(struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(blob), offset))
        offset += len(blob)
    for size in sizes:
        out.append(images[size])
    path.write_bytes(b"".join(out))


def write_png(path: Path, rows) -> None:
    height = len(rows)
    width = len(rows[0])
    raw = b"".join(
        b"\x00" + b"".join(bytes(px) for px in row) for row in rows
    )

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    assets = root / "assets"
    assets.mkdir(exist_ok=True)

    images = {}
    for size in (16, 24, 32, 48, 64, 128, 256):
        rows = render(size)
        images[size] = encode_bmp(size, rows)
        if size == 128:
            write_png(assets / "preview.png", rows)

    write_ico(assets / "controle_veiculos.ico", images)
    ico = assets / "controle_veiculos.ico"
    print(f"ícone gerado: {ico} ({ico.stat().st_size} bytes)")
    print(f"prévia: {assets / 'preview.png'}")


if __name__ == "__main__":
    main()
