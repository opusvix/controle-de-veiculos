"""Conta local (usuário + senha) usada pela tela de login.

Tudo fica neste computador, no arquivo %APPDATA%\\ControleVeiculos\\conta.json.
A senha nunca é guardada assim mesmo: guardamos só um resumo (PBKDF2 com sal),
então quem abrir o arquivo não lê a senha. Isto protege contra curiosos na
mesma máquina - não é segurança de internet.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from pathlib import Path

ITERACOES = 200_000
MINIMO_SENHA = 4


class ContaError(Exception):
    """Problema ao criar/ler a conta."""


def conta_file() -> Path:
    from . import storage  # importa aqui: storage cuida do %APPDATA%

    return storage.config_file().with_name("conta.json")


def _ler() -> dict:
    try:
        dados = json.loads(conta_file().read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - ausente/ilegível = sem conta
        return {}
    return dados if isinstance(dados, dict) else {}


def existe() -> bool:
    dados = _ler()
    return bool(dados.get("usuario") and dados.get("hash"))


def usuario_salvo() -> str:
    return str(_ler().get("usuario") or "")


def _resumo(senha: str, sal: bytes, iteracoes: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, iteracoes)


def validar(usuario: str, senha: str) -> bool:
    """True quando usuário e senha batem com a conta criada neste computador."""
    dados = _ler()
    if not dados:
        return False
    if not hmac.compare_digest(str(dados.get("usuario") or "").strip(),
                               (usuario or "").strip()):
        return False
    try:
        sal = bytes.fromhex(str(dados.get("sal") or ""))
        guardado = bytes.fromhex(str(dados.get("hash") or ""))
        iteracoes = int(dados.get("iteracoes") or ITERACOES)
    except ValueError:
        return False
    if not sal or not guardado:
        return False
    return hmac.compare_digest(_resumo(senha.strip(), sal, iteracoes), guardado)


def criar(usuario: str, senha: str) -> None:
    """Cria (ou recria) a conta local. Levanta ContaError se faltar algo."""
    usuario = (usuario or "").strip()
    senha = (senha or "").strip()
    if not usuario:
        raise ContaError("Digite um usuário.")
    if len(senha) < MINIMO_SENHA:
        raise ContaError(f"A senha precisa ter pelo menos {MINIMO_SENHA} caracteres.")
    sal = secrets.token_bytes(16)
    dados = {
        "usuario": usuario,
        "sal": sal.hex(),
        "hash": _resumo(senha, sal, ITERACOES).hex(),
        "iteracoes": ITERACOES,
    }
    alvo = conta_file()
    try:
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(json.dumps(dados, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    except OSError as exc:
        raise ContaError(f"Não foi possível gravar a conta:\n{exc}") from exc


def apagar() -> None:
    """Apaga só a conta de acesso (os dados do programa não são tocados)."""
    try:
        conta_file().unlink(missing_ok=True)
    except OSError:
        pass
