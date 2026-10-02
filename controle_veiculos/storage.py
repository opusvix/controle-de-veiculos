"""Leitura e gravação dos dados em arquivo JSON no computador."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .models import Document

APP_DIR_NAME = "ControleVeiculos"
LEGACY_APP_DIR_NAME = "ControleKm"  # pasta antiga (antes da renomeação)


def _raiz_programa() -> Path:
    """Pasta onde o programa está (raiz do projeto ou pasta do executável).

    No exe (PyInstaller) a pasta é a do próprio executável, exceto quando ele
    está em dist/ ou build/ (compilação de teste): aí sobe um nível. Raiz que
    não existe => o app cai no Documentos, nada quebra.
    """
    if getattr(sys, "frozen", False):
        pasta = Path(sys.executable).resolve().parent
        if pasta.name.lower() in {"dist", "build"}:
            pasta = pasta.parent
        return pasta
    return Path(__file__).resolve().parents[1]


# Raiz preferida: é lá que ficam o programa e a pasta de dados.
PREFERRED_ROOT = _raiz_programa()


class StorageError(Exception):
    """Erro ao ler ou gravar o arquivo de dados."""


def documents_dir() -> Path:
    profile = Path(os.environ.get("USERPROFILE") or str(Path.home()))
    docs = profile / "Documents"
    return docs if docs.exists() else profile


def preferred_data_dir() -> Path | None:
    """Pasta de dados dentro da raiz escolhida (None se ela não existir)."""
    try:
        if PREFERRED_ROOT.exists():
            return PREFERRED_ROOT / APP_DIR_NAME
    except OSError:
        pass
    return None


def data_dir() -> Path:
    """Pasta onde os dados ficam por padrão."""
    return preferred_data_dir() or (documents_dir() / APP_DIR_NAME)


def _base_dir(legacy: bool = False) -> Path:
    base = Path(os.environ.get("APPDATA") or str(documents_dir()))
    return base / (LEGACY_APP_DIR_NAME if legacy else APP_DIR_NAME)


def _copy_if_missing(origem: Path, alvo: Path) -> bool:
    """Cópia simples, nunca sobrescreve. Devolve True quando copiou."""
    if alvo.exists() or not origem.exists():
        return False
    try:
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(origem.read_bytes())
        return True
    except OSError:
        return False  # não bloqueia o app: o arquivo de origem continua lá


def _sync_to(origem: Path, alvo: Path) -> bool:
    """Copia origem -> alvo; sobrescreve só se a origem for mais nova.

    Devolve True se, no fim, existe arquivo em `alvo`.
    """
    try:
        if not origem.exists():
            return alvo.exists()
        if not alvo.exists():
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_bytes(origem.read_bytes())
        elif origem.stat().st_mtime > alvo.stat().st_mtime + 1:
            alvo.write_bytes(origem.read_bytes())
        return True
    except OSError:
        return alvo.exists()


def migrate_data() -> None:
    """Leva os dados para a pasta escolhida, sem apagar nada.

    Cadeia: Documentos\\ControleKm -> Documentos\\ControleVeiculos ->
    raiz escolhida. Toda transferência é por cópia e, se algo falhar, o
    arquivo original permanece intacto e o programa segue usando-o.
    Se o usuário já escolheu a pasta na mão, nada é copiado para outro lugar.
    """
    if not _read_config().get("escolhido"):
        docs = documents_dir()
        _copy_if_missing(docs / LEGACY_APP_DIR_NAME / "dados.json",
                         docs / APP_DIR_NAME / "dados.json")
        preferida = preferred_data_dir()
        if preferida is not None:
            _copy_if_missing(docs / APP_DIR_NAME / "dados.json",
                             preferida / "dados.json")
            _copy_if_missing(docs / LEGACY_APP_DIR_NAME / "dados.json",
                             preferida / "dados.json")
    # configuração da pasta antiga (a configuração fica no %APPDATA%)
    _copy_if_missing(_base_dir(legacy=True) / "config.json", config_file())


def default_path() -> Path:
    """Arquivo padrão: <raiz>\\ControleVeiculos\\dados.json (ou Documentos)."""
    migrate_data()
    return data_dir() / "dados.json"


def config_file() -> Path:
    return _base_dir() / "config.json"


def _read_config() -> dict:
    try:
        data = json.loads(config_file().read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - arquivo ausente/ilegível = sem configuração
        return {}
    return data if isinstance(data, dict) else {}


def _auto_dir(pasta: Path) -> bool:
    """True se a pasta é uma das cuidadas pelo programa (Documentos/legada)."""
    try:
        atual = pasta.resolve()
        docs = documents_dir().resolve()
    except OSError:
        return False
    return atual in {docs / APP_DIR_NAME, docs / LEGACY_APP_DIR_NAME}


def load_last_path() -> Path | None:
    """Último arquivo usado, já levado para a raiz escolhida quando couber."""
    migrate_data()
    cfg = _read_config()
    last = cfg.get("last_file")
    if not last:
        return None
    caminho = Path(last)

    # Caminho gravado quando a pasta ainda era ControleKm
    if LEGACY_APP_DIR_NAME in caminho.parts:
        partes = list(caminho.parts)
        partes[partes.index(LEGACY_APP_DIR_NAME)] = APP_DIR_NAME
        caminho = Path(*partes)
        if caminho.exists():
            remember_path(caminho)

    # Dado ainda no Documentos: passa a ser gravado na raiz escolhida, a
    # menos que o usuário tenha mandado gravar em outro lugar.
    preferida = preferred_data_dir()
    if (preferida is not None and not cfg.get("escolhido")
            and _auto_dir(caminho.parent)):
        alvo = preferida / caminho.name
        if _sync_to(caminho, alvo):
            caminho = alvo
            remember_path(caminho)

    return caminho if caminho.exists() else None


def remember_path(path: Path, escolhido: bool = False) -> None:
    """Guarda o arquivo usado (e sua pasta) no %APPDATA%, sem apagar o resto."""
    try:
        cfg = _read_config()
        cfg["last_file"] = str(path)
        cfg["data_dir"] = str(Path(path).parent)
        if escolhido:
            cfg["escolhido"] = True
        alvo = config_file()
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    except Exception:
        pass  # apenas um ajuste de conveniência: não deve quebrar o app


def primeira_execucao() -> bool:
    """True quando ainda não há pasta escolhida nem arquivo de dados."""
    cfg = _read_config()
    if cfg.get("escolhido") or cfg.get("last_file"):
        return False
    return not default_path().exists()


def load(path: Path) -> Document:
    """Carrega o documento de `path`. Arquivo inexistente/vazio = documento novo."""
    path = Path(path)
    if not path.exists():
        return Document()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StorageError(f"Não foi possível ler o arquivo:\n{path}\n\n{exc}") from exc
    if not text.strip():
        return Document()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StorageError(
            f"O arquivo não é um JSON válido:\n{path}\n\n{exc}\n\n"
            "Escolha 'Arquivo > Novo arquivo' para recomeçar."
        ) from exc
    if not isinstance(data, dict):
        raise StorageError(f"Formato inesperado no arquivo:\n{path}")
    return Document.from_dict(data)


def save(doc: Document, path: Path) -> None:
    """Grava o documento de forma atômica (evita corrupção se o PC desligar)."""
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(
            json.dumps(doc.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, path)
    except OSError as exc:
        raise StorageError(f"Não foi possível salvar o arquivo:\n{path}\n\n{exc}") from exc
