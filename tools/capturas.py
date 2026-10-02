"""Gera as imagens usadas nos guias (README.md e INSTALAR-COMO-USAR.md).

Uso:  python tools/capturas.py

Requisito extra: Pillow (python -m pip install pillow). Só ESTE script usa
Pillow — o programa em si continua sem nenhuma biblioteca fora da biblioteca
padrão. As imagens ficam na pasta imagens/ e mudam quando a tela muda.

O que é gerado aqui:
    icone.png                 o ícone do programa
    01-instalar.png           janela do Instalar.bat perguntando a pasta
    02-pasta-dados.png        janela que pergunta onde guardar os dados
    03-tela-inicial.png       aba Abastecimentos
    04-cadastrar-veiculo.png  aba Veículos
    05-manutencoes.png        aba Manutenções (com os avisos)
    06-relatorios.png         aba Relatórios
    07-servidor-wifi.png      janela do Servidor Wi-Fi

A imagem 08-celular.png (versão no celular) é feita pelo navegador, não por
este script. Os dados mostrados nas fotos são de exemplo, criados aqui.
"""
from __future__ import annotations

import ctypes
import inspect
import os
import subprocess
import sys
import tempfile
import threading
import time
from ctypes import wintypes
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

PASTA_IMG = RAIZ / "imagens"

WM_CLOSE = 0x0010
WM_COMMAND = 0x0111
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_ESCAPE = 0x1B
IDCANCEL = 2
GA_ROOT = 2
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010

user32 = ctypes.windll.user32


# --------------------------------------------------------------- janelas
def retangulo(hwnd: int):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def _titulo(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def _classe(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(hwnd, buf, 64)
    return buf.value


def _pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def _visivel(hwnd: int) -> bool:
    return bool(user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd))


def janela_por_titulo(contem: str, timeout: float = 12.0) -> int | None:
    """Espera uma janela visível cujo título contenha `contem`."""
    procurar = contem.lower()
    fim = time.time() + timeout
    while time.time() < fim:
        achadas: list[int] = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def cb(hwnd, _lparam):
            if _visivel(hwnd) and procurar in _titulo(hwnd).lower():
                achadas.append(hwnd)
            return True

        user32.EnumWindows(cb, 0)
        if achadas:
            return achadas[0]
        time.sleep(0.2)
    return None


def dialogo_da_nossa_app(app_hwnd: int, timeout: float = 10.0) -> int | None:
    """Janela de diálogo (classe #32770) criada pelo nosso programa."""
    meu_pid = os.getpid()
    fim = time.time() + timeout
    while time.time() < fim:
        achados: list[int] = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def cb(hwnd, _lparam):
            if (_visivel(hwnd) and _classe(hwnd) == "#32770"
                    and hwnd != app_hwnd and _pid(hwnd) == meu_pid):
                achados.append(hwnd)
            return True

        user32.EnumWindows(cb, 0)
        if achados:
            return achados[0]
        time.sleep(0.15)
    return None


def fechar_janela(hwnd: int) -> bool:
    """Fecha educadamente: WM_CLOSE, depois Cancelar, depois Esc."""
    for msg, wparam in ((WM_CLOSE, 0), (WM_COMMAND, IDCANCEL),
                        (WM_KEYDOWN, VK_ESCAPE), (WM_KEYUP, VK_ESCAPE)):
        user32.PostMessageW(hwnd, msg, wparam, 0)
        time.sleep(0.4)
        if not _visivel(hwnd):
            return True
    return not _visivel(hwnd)


def _vazia(img) -> bool:
    """Detecta imagem lisa (janela não renderizou no PrintWindow)."""
    try:
        baixo, alto = img.convert("L").getextrema()
    except Exception:  # noqa: BLE001
        return True
    return alto - baixo < 8


def _printwindow(hwnd: int):
    """Desenha a janela mesmo coberta (PrintWindow + repintura completa)."""
    from PIL import Image

    gdi32 = ctypes.windll.gdi32
    r = retangulo(hwnd)
    w, h = r[2] - r[0], r[3] - r[1]
    if w <= 0 or h <= 0:
        return None

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]

    hdc_tela = user32.GetDC(0)
    try:
        mem = gdi32.CreateCompatibleDC(hdc_tela)
        bmp = gdi32.CreateCompatibleBitmap(hdc_tela, w, h)
        gdi32.SelectObject(mem, bmp)
        # 2 = PW_RENDERFULLCONTENT (senão o Windows Terminal sai pela metade)
        if not user32.PrintWindow(hwnd, mem, 2):
            return None
        info = BITMAPINFOHEADER()
        info.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        info.biWidth = w
        info.biHeight = -h          # negativo = de cima para baixo
        info.biPlanes = 1
        info.biBitCount = 32
        info.biCompression = 0
        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(info), 0)
        img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)
        return img.convert("RGB")
    except Exception:  # noqa: BLE001
        return None
    finally:
        try:
            user32.ReleaseDC(0, hdc_tela)
        except Exception:  # noqa: BLE001
            pass


def capturar(hwnd: int, destino: Path) -> bool:
    """Fotografa a janela do jeito que a pessoa vê na tela.

    Primeiro o PrintWindow (funciona mesmo com a janela coberta); se
    sair em branco, aí sim fotografamos a área da tela.
    """
    from PIL import ImageGrab

    if not hwnd:
        return False

    img = _printwindow(hwnd)
    if img is None or _vazia(img):
        img = None
        assinatura = str(inspect.signature(ImageGrab.grab))
        if "window" in assinatura:
            try:
                img = ImageGrab.grab(window=hwnd, all_screens=True)
            except Exception:  # noqa: BLE001
                img = None
    if img is None or _vazia(img):
        r = retangulo(hwnd)
        if r[2] <= r[0] or r[3] <= r[1]:
            return False
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        time.sleep(0.5)
        try:
            img = ImageGrab.grab(bbox=r, all_screens=True)
        except Exception:  # noqa: BLE001
            img = None
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
    if img is None or _vazia(img):
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(destino, optimize=True)
    return True


def dpi_aware() -> None:
    """Faz as coordenadas das janelas baterem com os pixels da tela."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:  # noqa: BLE001
        try:
            user32.SetProcessDPIAware()
        except Exception:  # noqa: BLE001
            pass


# ------------------------------------------------------------ exemplo
def documento_exemplo():
    from controle_veiculos.models import Document, Maintenance, Refuel, Vehicle

    gol = Vehicle(id="gol", name="Gol 2019", plate="ABC1D23", year=2019,
                  fuel="Flex", initial_km=40000.0)
    moto = Vehicle(id="biz", name="Honda Biz 125", plate="DEF4G56", year=2021,
                   fuel="Gasolina", initial_km=3000.0)
    doc = Document(vehicles=[gol, moto])

    linhas = [
        ("2026-06-03", 40000, 40.0, 5.50, 220.00, True, "Posto Ipiranga", ""),
        ("2026-06-17", 40480, 20.0, 5.60, 112.00, False, "Posto Ipiranga", "encheu só o suficiente"),
        ("2026-06-30", 40960, 36.0, 5.70, 205.20, True, "Shell", ""),
        ("2026-07-14", 41500, 38.0, 5.80, 220.40, True, "Posto Brasil", ""),
        ("2026-07-28", 41980, 35.5, 6.00, 213.00, True, "Shell", ""),
        ("2026-08-11", 42450, 37.0, 5.95, 220.15, True, "Posto Ipiranga", ""),
        ("2026-08-25", 42940, 36.5, 5.99, 218.64, True, "Ale", ""),
        ("2026-09-08", 43400, 38.0, 6.10, 231.80, True, "Posto Brasil", ""),
        ("2026-09-22", 43900, 37.5, 6.05, 226.88, True, "Shell", ""),
    ]
    for i, (data, km, litros, preco, total, cheio, posto, obs) in enumerate(linhas, 1):
        ref = Refuel(id=f"r{i}", vehicle_id="gol", date=data, odometer=float(km),
                     liters=litros, price=preco, total=total, full_tank=cheio)
        ref.station = posto
        ref.notes = obs
        doc.refuels.append(ref)

    for i, (data, km, litros, preco, total) in enumerate([
            ("2026-07-05", 3250, 11.0, 5.85, 64.35),
            ("2026-08-19", 3680, 11.5, 5.95, 68.43),
            ("2026-09-20", 4110, 11.0, 6.00, 66.00)], 1):
        ref = Refuel(id=f"m{i}", vehicle_id="biz", date=data, odometer=float(km),
                     liters=litros, price=preco, total=total, full_tank=True)
        ref.station = "Posto da esquina"
        doc.refuels.append(ref)

    doc.maintenances = [
        Maintenance(id="k1", vehicle_id="gol", date="2026-09-02", odometer=43150.0,
                    type="Troca de óleo", details="Óleo 5W30 sintético + filtro de óleo",
                    cost=190.0, shop="Oficina do Zé", notes="Troca a cada 5.000 km",
                    next_km=48150.0, next_date="2027-03-02"),
        Maintenance(id="k2", vehicle_id="gol", date="2026-03-05", odometer=38000.0,
                    type="Alinhamento e balanceamento", details="Rodas dianteiras e traseiras",
                    cost=130.0, shop="Pneus Roda Viva", notes="",
                    next_km=48000.0, next_date="2026-09-05"),
        Maintenance(id="k3", vehicle_id="gol", date="2026-06-20", odometer=40900.0,
                    type="Revisão", details="Revisão de 40.000 km na concessionária",
                    cost=350.0, shop="Concessionária", notes="Cupom 8842",
                    next_km=50900.0, next_date="2026-10-20"),
        Maintenance(id="k4", vehicle_id="biz", date="2026-08-19", odometer=3680.0,
                    type="Troca de óleo", details="Óleo 10W30",
                    cost=60.0, shop="Moto Center", notes="",
                    next_km=8680.0, next_date="2027-02-19"),
    ]
    return doc


# ------------------------------------------------------------- capturas
def capturar_abas(app) -> list[str]:
    from controle_veiculos import storage

    raiz = user32.GetAncestor(app.winfo_id(), GA_ROOT) or app.winfo_id()

    real = storage.preferred_data_dir() or storage.data_dir()
    app.storage_path = real / "dados.json"   # só para o rodapé mostrar o lugar certo
    app.saved_at = "14:32"
    app.refresh()

    alvos = [
        ("03-tela-inicial", app.refuels_tab),
        ("04-cadastrar-veiculo", app.vehicles_tab),
        ("05-manutencoes", app.maintenance_tab),
        ("06-relatorios", app.reports_tab),
    ]
    feitas: list[str] = []
    for nome, aba in alvos:
        app.notebook.select(aba)
        app.lift()
        app.focus_force()
        app.update_idletasks()
        app.update()
        time.sleep(0.6)
        if capturar(raiz, PASTA_IMG / f"{nome}.png"):
            feitas.append(nome + ".png")
            print(f"  ok: {nome}.png")
        else:
            print(f"  ! nao deu para capturar {nome}.png")
    return feitas


def capturar_dialogo(app) -> None:
    """Abre a janela de escolha da pasta, fotografam e a fecha."""
    from controle_veiculos import storage

    raiz = user32.GetAncestor(app.winfo_id(), GA_ROOT) or app.winfo_id()
    destino = PASTA_IMG / "02-pasta-dados.png"
    achou = threading.Event()

    def trabalhador():
        hwnd = dialogo_da_nossa_app(raiz, timeout=10)
        if not hwnd:
            print("  ! janela de pasta nao apareceu")
            fg = user32.GetForegroundWindow()
            if fg:
                fechar_janela(fg)
            return
        achou.set()
        time.sleep(0.8)
        if capturar(hwnd, destino):
            # a lateral do Windows lista as pastas pessoais de quem usa
            embaralhar(destino, (0, 115, 335, 465))
            print(f"  ok: {destino.name}")
        else:
            print(f"  ! nao deu para capturar {destino.name}")
        time.sleep(0.3)
        fechar_janela(hwnd)

    threading.Thread(target=trabalhador, daemon=True).start()
    time.sleep(0.4)

    padrao = storage.preferred_data_dir() or storage.data_dir()
    original = storage.default_path
    storage.default_path = lambda: padrao / "dados.json"
    try:
        app._ask_data_folder()   # bloqueia até a janela ser fechada
    finally:
        storage.default_path = original
    achou.wait(1.0)


def embaralhar(destino: Path, caixa: tuple[int, int, int, int],
               pixel: int = 10) -> None:
    """Borrão pixelado numa região (aqui: pastas pessoais do usuário)."""
    from PIL import Image

    if not destino.exists():
        return
    img = Image.open(destino).convert("RGB")
    x0, y0, x1, y1 = caixa
    x1, y1 = min(x1, img.size[0]), min(y1, img.size[1])
    recorte = img.crop((x0, y0, x1, y1))
    pequeno = recorte.resize((max(1, (x1 - x0) // pixel),
                              max(1, (y1 - y0) // pixel)), Image.BILINEAR)
    borrado = pequeno.resize((x1 - x0, y1 - y0), Image.NEAREST)
    img.paste(borrado, (x0, y0))
    img.save(destino, optimize=True)


def capturar_processo(comando: list[str], titulo: str, nome_arquivo: str,
                      cwd: Path | None = None) -> None:
    """Abre um programa, espera a janela com `titulo`, fotografa e encerra."""
    # Sem redireção nenhuma: o processo ganha um console próprio e o
    # texto sai NA JANELA (com stdout cortado, o console fica preto).
    proc = subprocess.Popen(
        comando, cwd=str(cwd or RAIZ),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    try:
        hwnd = janela_por_titulo(titulo, timeout=12)
        if not hwnd:
            print(f"  ! janela '{titulo}' nao apareceu")
            return
        user32.SetForegroundWindow(hwnd)
        time.sleep(1.2)
        destino = PASTA_IMG / nome_arquivo
        if capturar(hwnd, destino):
            print(f"  ok: {nome_arquivo}")
        else:
            print(f"  ! nao deu para capturar {nome_arquivo}")
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)


def gerar_icone() -> None:
    from PIL import Image

    origem = RAIZ / "assets" / "controle_veiculos.ico"
    if not origem.exists():
        print("  ! icone nao encontrado")
        return
    img = Image.open(origem)
    tamanhos = getattr(img, "sizes", [])
    if tamanhos:
        maior = max(tamanhos)
        img.size  # noqa: B018 - posiciona o ponteiro
        img = Image.open(origem)
        for _ in range(64):
            if img.size == maior:
                break
            img.seek(img.tell() + 1)
    img = img.convert("RGBA")
    PASTA_IMG.mkdir(parents=True, exist_ok=True)
    img.save(PASTA_IMG / "icone.png", optimize=True)
    print(f"  ok: icone.png ({img.size[0]}x{img.size[1]})")


# ---------------------------------------------------------------- main
def main() -> int:
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("Falta o Pillow para gerar as imagens: "
              "python -m pip install pillow")
        return 1

    dpi_aware()
    PASTA_IMG.mkdir(parents=True, exist_ok=True)

    # isola perfil e configuração: nada no seu computador é tocado
    tmp = Path(tempfile.mkdtemp(prefix="capturas-"))
    (tmp / "Perfil" / "Documents").mkdir(parents=True)
    os.environ["USERPROFILE"] = str(tmp / "Perfil")
    os.environ["APPDATA"] = str(tmp / "AppData")

    from controle_veiculos.ui.app import App

    print("gerando imagens em", PASTA_IMG)
    gerar_icone()

    app = App(ask_folder=False)
    try:
        app.doc = documento_exemplo()
        app.active_vehicle_id = "gol"
        app.refresh()
        app.update()
        time.sleep(0.6)

        capturar_abas(app)
        capturar_dialogo(app)
    finally:
        app.destroy()
        app.update()

    capturar_processo(
        ["cmd", "/c", "call", str(RAIZ / "Instalar.bat")],
        "Instalar Controle de Veiculos", "01-instalar.png")
    capturar_processo(
        ["cmd", "/c", "call", str(RAIZ / "web" / "Servidor Wi-Fi.bat")],
        "Controle de Veiculos - Servidor Wi-Fi", "07-servidor-wifi.png",
        cwd=RAIZ / "web")

    print("pronto. Falta só a imagem do celular (feita pelo navegador).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
