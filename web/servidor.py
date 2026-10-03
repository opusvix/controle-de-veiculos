"""Servidor do Controle de Veículos: mostra a página e sincroniza os dados.

- Serve os arquivos da pasta web\\ (como o servidor simples do Windows).
- GET  /__sync  -> devolve o dados.json que está no computador.
- POST /__sync  -> junta os dados do celular com os do computador, grava o
  arquivo do computador e devolve o resultado pronto (a página web chama
  este endereço no botão "Sincronizar").

Só usa a biblioteca padrão do Python. É chamado pelo "Servidor Wi-Fi.bat";
se ele falhar, o .bat volta para o servidor simples (aí sem sincronização).
"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

PASTA = Path(__file__).resolve().parent
PORTA = 8000
MAX_CORPO = 32 * 1024 * 1024  # 32 MB: proteção contra corpo gigante
LISTAS = ("vehicles", "refuels", "maintenances")
TRAVA = threading.Lock()  # dois aparelhos ao mesmo tempo: um por vez

# igual a controle_veiculos/storage.py (sem importar o pacote: este script
# roda sozinho, até em PC que só tem o .exe instalado): a raiz é a pasta que
# contém esta (web\ -> pasta onde o programa está)
RAIZ_PREFERIDA = Path(__file__).resolve().parents[1]
PASTA_APP = "ControleVeiculos"
PASTA_LEGADA = "ControleKm"


def _utf8_seguro() -> None:
    """Evita travar a janela preta quando o console não é UTF-8."""
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - sem reconfigure = segue normal
            pass


def documentos() -> Path:
    perfil = Path(os.environ.get("USERPROFILE") or str(Path.home()))
    docs = perfil / "Documents"
    return docs if docs.exists() else perfil


def _pasta_gravavel(pasta: Path) -> bool:
    """Igual ao storage: testa de verdade se dá para gravar (Windows/ACL)."""
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        teste = pasta / ".permissao-teste.tmp"
        try:
            teste.write_bytes(b"x")
        finally:
            try:
                teste.unlink()
            except OSError:
                pass
        return True
    except OSError:
        return False


def arquivo_dados() -> Path:
    """Mesmo dados.json usado pelo aplicativo do computador."""
    override = os.environ.get("CONTROLE_VEICULOS_DADOS")  # teste/avançado
    if override:
        return Path(override)
    base = Path(os.environ.get("APPDATA") or str(documentos())) / PASTA_APP
    cfg = {}
    try:
        cfg = json.loads((base / "config.json").read_text(encoding="utf-8"))
        if not isinstance(cfg, dict):
            cfg = {}
    except Exception:  # noqa: BLE001 - sem configuração = usa o padrão
        pass

    candidatos = []
    if cfg.get("last_file"):
        candidatos.append(Path(str(cfg["last_file"])))
    if cfg.get("data_dir"):
        candidatos.append(Path(str(cfg["data_dir"])) / "dados.json")
    candidatos += [
        RAIZ_PREFERIDA / PASTA_APP / "dados.json",
        documentos() / PASTA_APP / "dados.json",
        documentos() / PASTA_LEGADA / "dados.json",
    ]
    for caminho in candidatos:
        try:
            if caminho.exists():
                return caminho
        except OSError:
            continue
    # ainda não criado: escolhe um local onde dá para gravar (a pasta do
    # programa pode ser o Program Files, que não aceita dados novos sem
    # permissão de administrador - aí o padrão vira o Documentos)
    for caminho in candidatos:
        try:
            if _pasta_gravavel(caminho.parent):
                return caminho
        except OSError:
            continue
    return candidatos[0]  # último caso: o padrão antigo


# --------------------------------------------------------------- documentos
def doc_vazio() -> dict:
    return {"version": 2, "vehicles": [], "refuels": [], "maintenances": []}


def normalizar(doc) -> dict:
    """Só aceita dicionário com listas de registros que tenham id."""
    if not isinstance(doc, dict):
        return doc_vazio()
    saida = doc_vazio()
    try:
        saida["version"] = int(doc.get("version") or 2)
    except (TypeError, ValueError):
        saida["version"] = 2
    for nome in LISTAS:
        itens = doc.get(nome)
        if isinstance(itens, list):
            saida[nome] = [x for x in itens
                           if isinstance(x, dict) and str(x.get("id") or "").strip()]
    return saida


def ler_documento(caminho: Path):
    """Lê o dados.json do computador. None = não existe; exceção = corrompido."""
    try:
        texto = caminho.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    if not texto.strip():
        return None
    return json.loads(texto)  # ValueError se estiver corrompido


def salvar_documento(caminho: Path, doc: dict) -> None:
    """Grava sem risco de arquivo pela metade (escreve em seguida e troca)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_name(caminho.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, caminho)


# -------------------------------------------------------------- sincronizar
def _mesclar_veiculo(pc: dict, cel: dict) -> dict:
    """Veículo: vale o do computador; o celular só completa o que faltar."""
    juntos = dict(pc)
    for chave, valor in cel.items():
        if chave == "id":
            continue
        atual = juntos.get(chave)
        if atual in (None, "", 0, 0.0) and valor not in (None, "", 0, 0.0):
            juntos[chave] = valor
    return juntos


def _mesclar_lancamento(pc: dict, cel: dict) -> dict:
    """Abastecimento/manutenção: a data mais recente vence (empate = PC)."""
    return cel if str(cel.get("date") or "") > str(pc.get("date") or "") else pc


def _mesclar_lista(base_l, pc_l, cel_l, conflito, estat: dict) -> list:
    """Junta uma lista pelo id, usando a cópia da última sincronização."""
    base = {r["id"]: r for r in base_l}
    pc = {r["id"]: r for r in pc_l}
    cel = {r["id"]: r for r in cel_l}
    ids = [r["id"] for r in pc_l]
    ids += [r["id"] for r in cel_l if r["id"] not in pc]

    fora: list = []
    for ident in ids:
        b, p, c = base.get(ident), pc.get(ident), cel.get(ident)
        if p is not None and c is not None:
            if p == c:
                mantido = p
            elif b is None or (p != b and c != b):
                mantido = conflito(p, c)
                estat["conflitos"] += 1
            elif p == b:      # só o celular mudou
                mantido = c
                estat["atualizados"] += 1
            else:             # só o computador mudou
                mantido = p
                estat["atualizados"] += 1
        elif p is not None:   # só no computador
            if b is not None and p == b:
                estat["removidos"] += 1   # o celular apagou
                continue
            if b is None:
                estat["novos_pc"] += 1
            mantido = p
        else:                 # só no celular
            if b is not None and c == b:
                estat["removidos"] += 1   # o computador apagou
                continue
            if b is None:
                estat["novos_celular"] += 1
            else:             # o computador apagou e o celular mudou
                estat["conflitos"] += 1
            mantido = c
        fora.append(mantido)
    return fora


def mesclar(base, pc, celular) -> tuple[dict, dict]:
    """Junta os três documentos. Devolve (resultado, estatísticas)."""
    base_n = normalizar(base) if base else normalizar({})
    pc_n = normalizar(pc) if pc else normalizar({})
    cel_n = normalizar(celular)
    estat = {"novos_celular": 0, "novos_pc": 0, "atualizados": 0,
             "removidos": 0, "conflitos": 0}

    resultado = {
        "version": max(pc_n["version"], cel_n["version"], base_n["version"]),
        "vehicles": _mesclar_lista(base_n["vehicles"], pc_n["vehicles"],
                                   cel_n["vehicles"], _mesclar_veiculo, estat),
        "refuels": _mesclar_lista(base_n["refuels"], pc_n["refuels"],
                                  cel_n["refuels"], _mesclar_lancamento, estat),
        "maintenances": _mesclar_lista(base_n["maintenances"], pc_n["maintenances"],
                                       cel_n["maintenances"], _mesclar_lancamento,
                                       estat),
    }
    estat["total"] = sum(len(resultado[n]) for n in LISTAS)
    return resultado, estat


# ------------------------------------------------------------------ handler
class Handler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".md": "text/plain; charset=utf-8",
        ".csv": "text/csv; charset=utf-8",
        ".tsv": "text/csv; charset=utf-8",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PASTA), **kwargs)

    def log_message(self, formato, *args):
        try:
            sys.stdout.write("  " + (formato % args) + "\n")
        except Exception:  # noqa: BLE001 - log nunca pode derrubar o servidor
            pass

    def _json(self, dados, status=200):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        caminho = urlsplit(self.path).path
        if caminho == "/__sync":
            self._sync_get()
        elif caminho == "/":
            self.path = "/controle-veiculos.html"
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != "/__sync":
            self.send_error(405, "Method Not Allowed")
            return
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            tamanho = 0
        if tamanho <= 0 or tamanho > MAX_CORPO:
            self._json({"ok": False, "erro": "Corpo do pedido inválido."}, 400)
            return
        try:
            payload = json.loads(self.rfile.read(tamanho).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("esperado um objeto JSON")
        except (ValueError, UnicodeDecodeError) as exc:
            self._json({"ok": False, "erro": f"JSON inválido: {exc}"}, 400)
            return
        self._sync_post(payload)

    def _sync_get(self):
        caminho = arquivo_dados()
        try:
            doc = ler_documento(caminho)
        except ValueError:
            self._json({"ok": False,
                        "erro": f"O arquivo não é um JSON válido: {caminho}"}, 500)
            return
        self._json({"ok": True, "dados": doc, "arquivo": str(caminho)})

    def _sync_post(self, payload: dict):
        caminho = arquivo_dados()
        if payload.get("dados") is None:
            self._json({"ok": False, "erro": "Faltou o campo 'dados'."}, 400)
            return

        with TRAVA:  # lê, junta e grava de uma vez só
            try:
                atual = ler_documento(caminho)
            except ValueError:
                self._json({"ok": False,
                            "erro": f"O arquivo não é um JSON válido: {caminho}. "
                                    "Corrija o arquivo antes de sincronizar "
                                    "(nada foi apagado)."}, 500)
                return
            try:
                resultado, estat = mesclar(payload.get("base"), atual,
                                           payload.get("dados"))
                salvar_documento(caminho, resultado)
            except (OSError, ValueError) as exc:
                self._json({"ok": False, "erro": f"Não consegui gravar: {exc}"}, 500)
                return

        print(f"  sincronizado: +{estat['novos_celular']} do celular, "
              f"+{estat['novos_pc']} para o celular, {estat['conflitos']} "
              f"conflito(s), {estat['removidos']} removido(s)")
        self._json({"ok": True, "dados": resultado, "estat": estat,
                    "arquivo": str(caminho)})


def ip_local() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def main() -> int:
    _utf8_seguro()
    servidor = ThreadingHTTPServer(("0.0.0.0", PORTA), Handler)
    print()
    print("  Servidor do Controle de Veiculos ligado.")
    print(f"  Sincronizacao ativa - dados em: {arquivo_dados()}")
    print(f"  Endereco deste PC: http://{ip_local()}:{PORTA}/")
    print("  Para encerrar, feche esta janela ou pressione Ctrl+C.")
    print()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print()
        print("  Servidor encerrado.")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OSError as exc:
        _utf8_seguro()
        print(f"  Nao foi possivel abrir a porta {PORTA}: {exc}")
        print("  Talvez outro programa ja esteja usando. Feche e tente de novo.")
        raise SystemExit(1)
