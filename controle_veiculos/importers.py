"""Importação de planilhas (CSV / TSV / XLSX) para o formato do aplicativo.

Somente biblioteca padrão: CSV com ``csv`` e XLSX com ``zipfile`` + ``xml.etree``.

Formato reconhecido (o nome do cabeçalho é o que importa, a ordem não):

Abastecimentos
    Veículo, Data, Odômetro, Litros, Preço por litro, Total,
    Tanque cheio, Posto, Observações

Veículos (aba "Veículos" de um .xlsx)
    Nome, Placa, Ano, Combustível, Km inicial, Observações
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import math
import posixpath
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .models import FUELS, Document, Refuel, Vehicle

ORDEM_PADRAO = ["data", "odometro", "litros", "preco", "total", "tanque", "posto", "obs"]

MAPEAMENTO: list[tuple[str, list[str]]] = [
    ("veiculo", ["veiculo", "carro", "moto", "automovel", "vehicle", "car",
                 "nome do veiculo", "vehicle name"]),
    ("kminicial", ["km inicial", "km iniciais", "odometro inicial", "initial km",
                   "starting km", "inicial"]),
    ("nome", ["nome", "apelido", "identificacao", "nome do carro", "name"]),
    ("placa", ["placa", "plate", "renavam"]),
    ("ano", ["ano", "year", "ano do veiculo", "ano de fabricacao"]),
    ("combustivel", ["combustivel", "fuel type", "tipo de combustivel", "fuel", "tipo"]),
    ("data", ["data", "date", "dia"]),
    ("odometro", ["odometro", "quilometragem", "quilometros", "odometer", "mileage",
                  "km total", "hodometro", "km"]),
    ("litros", ["litros", "litro", "litragem", "liters", "litres", "litre",
                "qtd litros", "quantidade", "volume"]),
    ("preco", ["preco por litro", "price per liter", "preco/l", "valor por litro",
               "price/l", "unit price", "valor/l", "r$/l", "custo por litro",
               "preco", "price", "valor unitario"]),
    ("total", ["total", "valor total", "custo", "cost", "amount", "gasto", "valor"]),
    ("tanque", ["tanque cheio", "full tank", "tank full", "cheio", "full", "tanque"]),
    ("posto", ["posto", "gas station", "station"]),
    ("obs", ["observacoes", "observations", "obs", "notas", "notes", "nota", "note",
             "comentario", "comments"]),
]

ALIAS: dict[str, str] = {}  # preenchido depois de norm() (ordem do arquivo importa)

SIM = {"sim", "s", "yes", "y", "1", "true", "x", "verdadeiro", "cheio", "tanque cheio"}


class ImportFileError(Exception):
    """Erro de leitura/interpretação do arquivo importado."""


# ----------------------------------------------------------------- texto
def norm(value) -> str:
    """Minúsculas, sem acentos e sem pontuação: 'Odômetro (km)' -> 'odometro km'."""
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9$/ ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


for _campo, _lista in MAPEAMENTO:          # cabeçalho normalizado -> campo
    for _alias in _lista:
        ALIAS.setdefault(norm(_alias), _campo)
ALIAS.setdefault("l", "litros")             # cabeçalho curto do Excel


def campo_do_cabecalho(cabecalho) -> str | None:
    t = norm(cabecalho)
    if not t:
        return None
    if t in ALIAS:
        return ALIAS[t]
    melhor, tam = None, 0
    for alias, campo in ALIAS.items():
        if len(alias) >= 3 and alias in t and len(alias) > tam:
            melhor, tam = campo, len(alias)
    return melhor


def mapear_cabecalho(linha) -> dict[str, int]:
    mapa: dict[str, int] = {}
    for i, cab in enumerate(linha):
        campo = campo_do_cabecalho(cab)
        if campo and campo not in mapa:
            mapa[campo] = i
    return mapa


# ------------------------------------------------------------- conversão
def parse_num_any(valor) -> float | None:
    """'1.234,56' (pt-BR), '1,234.56' (en) ou número puro -> float."""
    if isinstance(valor, bool):
        valor = str(valor)
    if isinstance(valor, (int, float)):
        return float(valor) if math.isfinite(float(valor)) else None
    if valor is None:
        return None
    t = re.sub(r"[^\d.,-]", "", str(valor))
    if not re.search(r"\d", t):
        return None
    negative = "-" in t
    t = t.replace("-", "")
    vc, vd = t.rfind(","), t.rfind(".")
    if vc >= 0 and vd >= 0:
        t = t.replace(".", "").replace(",", ".") if vc > vd else t.replace(",", "")
    elif vc >= 0:
        t = t.replace(",", "") if t.count(",") > 1 else t.replace(",", ".", 1)
    elif vd >= 0:
        parts = t.split(".")
        if len(parts) > 2:
            t = "".join(parts[:-1]) + "." + parts[-1]
        elif len(parts) == 2 and len(parts[1]) == 3 and len(t.replace(".", "")) > 4:
            t = "".join(parts)
    try:
        value = float(t)
    except ValueError:
        return None
    return -value if negative else value


def _iso(year: int, month: int, day: int) -> str | None:
    try:
        return dt.date(year, month, day).isoformat()
    except ValueError:
        return None


def parse_data_any(valor) -> str | None:
    """Data em ISO (aaaa-mm-dd) a partir de texto, data ou série do Excel."""
    if isinstance(valor, bool):
        valor = str(valor)
    if isinstance(valor, (int, float)):
        if not math.isfinite(float(valor)) or not 20 <= float(valor) <= 80000:
            return None
        return (dt.date(1899, 12, 30) + dt.timedelta(days=int(round(float(valor))))).isoformat()
    t = str(valor or "").strip()
    if not t:
        return None
    if re.fullmatch(r"\d{5}", t):
        return parse_data_any(int(t))
    m = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", t)
    if m:
        return _iso(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})", t)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000 if year < 70 else 1900
        return _iso(year, month, day)
    return None


def parse_bool_any(valor) -> bool:
    if valor is True or valor == 1:
        return True
    return str(valor if valor is not None else "").strip().lower() in SIM


def _texto(valor) -> str:
    """Célula -> texto limpo (2021.0 do Excel vira '2021')."""
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return str(valor)
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def fuel_any(valor) -> str | None:
    t = norm(valor)
    if not t:
        return None
    for fuel in FUELS:
        if norm(fuel) == t:
            return fuel
    if "alcool" in t or "etanol" in t:
        return "Etanol"
    if "diesel" in t:
        return "Diesel"
    if "flex" in t:
        return "Flex"
    if "gnv" in t or "gas natural" in t:
        return "GNV"
    if "eletr" in t:
        return "Elétrico"
    if "hibri" in t:
        return "Híbrido"
    return "Outro"


# ------------------------------------------------------------------ CSV
def detectar_separador(texto: str) -> str:
    linha = ""
    for candidata in texto.splitlines():
        if candidata.strip() and not candidata.lower().startswith("sep="):
            linha = candidata
            break
    melhor, n = ";", 0
    for sep in (";", "\t", ",", "|"):
        conta, aspas = 0, False
        for ch in linha:
            if ch == '"':
                aspas = not aspas
            elif not aspas and ch == sep:
                conta += 1
        if conta > n:
            melhor, n = sep, conta
    return melhor if n else ";"


def ler_delimitado(texto: str) -> list[list[str]]:
    if texto.startswith("\ufeff"):
        texto = texto[1:]
    linhas = texto.splitlines()
    sep = None
    if linhas and linhas[0].lower().startswith("sep="):
        sep = linhas[0].split("=", 1)[1].strip() or None
        texto = "\n".join(linhas[1:])
    sep = sep or detectar_separador(texto)
    if sep not in (";", "\t", ",", "|"):
        sep = detectar_separador(texto)
    try:
        return [linha for linha in csv.reader(io.StringIO(texto), delimiter=sep)]
    except csv.Error as exc:
        raise ImportFileError(f"não consegui ler o texto: {exc}") from exc


# ----------------------------------------------------------------- XLSX
def _local(tag: str) -> str:
    return tag.split("}")[-1]


def _col_index(ref: str) -> int:
    n = 0
    for ch in ref.upper():
        v = ord(ch) - 64
        if v < 1 or v > 26:
            break
        n = n * 26 + v
    return max(0, n - 1)


def _shared_strings(zf: zipfile.ZipFile, names: set[str]) -> list[str]:
    if "xl/sharedStrings.xml" not in names:
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    saida = []
    for si in root:
        if _local(si.tag) != "si":
            continue
        saida.append("".join(t.text or "" for t in si.iter() if _local(t.tag) == "t"))
    return saida


def _rel_targets(zf: zipfile.ZipFile, names: set[str]) -> dict[str, str]:
    caminho = "xl/_rels/workbook.xml.rels"
    if caminho not in names:
        return {}
    root = ET.fromstring(zf.read(caminho))
    alvos: dict[str, str] = {}
    for rel in root:
        if _local(rel.tag) != "Relationship":
            continue
        rid, target = rel.attrib.get("Id"), rel.attrib.get("Target")
        if rid and target:
            alvos[rid] = target
    return alvos


def _sheet_path(target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    if target.startswith("xl/"):
        return target
    return posixpath.normpath(posixpath.join("xl", target))


def _sheet_rows(xml: bytes, shared: list[str]) -> list[list]:
    root = ET.fromstring(xml)
    rows: list[list] = []
    for row in root.iter():
        if _local(row.tag) != "row":
            continue
        line: list = []
        for cell in row:
            if _local(cell.tag) != "c":
                continue
            ref = cell.attrib.get("r", "")
            kind = cell.attrib.get("t", "n")
            col = _col_index(ref) if ref else len(line)
            value: object = ""
            if kind == "inlineStr":
                value = "".join(t.text or "" for t in cell.iter() if _local(t.tag) == "t")
            else:
                raw = None
                for child in cell:
                    if _local(child.tag) == "v":
                        raw = child.text
                        break
                if raw is not None:
                    if kind == "s":
                        try:
                            value = shared[int(raw)]
                        except (ValueError, IndexError):
                            value = ""
                    elif kind == "b":
                        value = raw == "1"
                    elif kind in ("str", "d"):
                        value = raw
                    else:
                        try:
                            value = float(raw)
                        except ValueError:
                            value = raw
            while len(line) <= col:
                line.append("")
            line[col] = value
        if any(str(item).strip() for item in line):
            rows.append(line)
    return rows


def ler_xlsx(data: bytes) -> list[tuple[str, list[list]]]:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ImportFileError("arquivo .xlsx inválido (zip não encontrado)") from exc
    with zf:
        names = set(zf.namelist())
        if "xl/workbook.xml" not in names:
            raise ImportFileError("não é uma planilha .xlsx válida")
        shared = _shared_strings(zf, names)
        alvos = _rel_targets(zf, names)
        root = ET.fromstring(zf.read("xl/workbook.xml"))
        abas: list[tuple[str, list[list]]] = []
        for sheet in root.iter():
            if _local(sheet.tag) != "sheet":
                continue
            nome = sheet.attrib.get("name", "")
            rid = (sheet.attrib.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                or sheet.attrib.get("r:id"))
            alvo = alvos.get(rid or "")
            if not nome or not alvo:
                continue
            caminho = _sheet_path(alvo)
            if caminho not in names:
                continue
            abas.append((nome, _sheet_rows(zf.read(caminho), shared)))
        if not abas:
            raise ImportFileError("nenhuma aba encontrada no .xlsx")
        return abas


# ---------------------------------------------------------------- arquivo
def _ler_texto(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("cp1252", errors="replace")


def ler_arquivo(caminho) -> list[tuple[str, list[list]]]:
    """Lê o arquivo e devolve [(nome_da_aba, linhas), ...]."""
    path = Path(caminho)
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        return ler_xlsx(path.read_bytes())
    if ext == ".json":
        raise ImportFileError(
            "Arquivo .json é do próprio aplicativo: use Arquivo > Abrir...")
    if ext in (".xls", ".xlsb"):
        raise ImportFileError(
            "O formato antigo .xls não é lido. No Excel use "
            "'Salvar como' -> .xlsx ou .csv e importe de novo.")
    try:
        texto = _ler_texto(path)
    except OSError as exc:
        raise ImportFileError(f"não consegui abrir o arquivo: {exc}") from exc
    if not texto.strip():
        raise ImportFileError("o arquivo está vazio")
    return [(path.name, ler_delimitado(texto))]


# --------------------------------------------------------------- montagem
def montar_documento(planilhas: list[tuple[str, list[list]]],
                     nome_padrao: str = "Meu veículo") -> tuple[Document, dict, list[str]]:
    """Converte as linhas lidas em um Document novo.

    Devolve (documento, resumo, mensagens_de_linhas_ignoradas).
    """
    doc = Document()
    resumo: dict = {"abas": [], "linhas": 0, "novos": 0, "veiculos": 0}
    ignoradas: list[str] = []
    por_nome: dict[str, Vehicle] = {}
    inicial: dict[str, float | None] = {}

    def garantir(nome: str, dados: dict | None = None) -> Vehicle | None:
        chave = norm(nome)
        if not chave:
            return None
        veiculo = por_nome.get(chave)
        if veiculo is None:
            veiculo = Vehicle(name=str(nome).strip())
            por_nome[chave] = veiculo
            doc.vehicles.append(veiculo)
            inicial[veiculo.id] = None
        if dados:
            if dados.get("plate") and not veiculo.plate:
                veiculo.plate = dados["plate"]
            if dados.get("year") and not veiculo.year:
                veiculo.year = dados["year"]
            if dados.get("fuel") and veiculo.fuel == "Gasolina":
                veiculo.fuel = dados["fuel"]
            if dados.get("notes") and not veiculo.notes:
                veiculo.notes = dados["notes"]
            km = dados.get("initial_km")
            if km and (inicial[veiculo.id] is None or km < inicial[veiculo.id]):
                inicial[veiculo.id] = km
        return veiculo

    preparadas: list[dict] = []
    for nome_aba, linhas in planilhas:
        brutas = [linha for linha in linhas
                  if linha and any(str(c).strip() for c in linha)]
        if not brutas:
            continue
        mapa = mapear_cabecalho(brutas[0])
        dados = brutas[1:]
        eh_veiculo = False
        if not mapa:
            if parse_data_any(brutas[0][0]) and parse_num_any(brutas[0][1]) is not None:
                mapa = {campo: i for i, campo in enumerate(ORDEM_PADRAO)}
                dados = brutas
            else:
                resumo["abas"].append(f"{nome_aba}: cabeçalhos não reconhecidos")
                continue
        elif ("odometro" in mapa and "litros" in mapa and "data" in mapa):
            eh_veiculo = False
        elif any(c in mapa for c in ("nome", "veiculo", "kminicial", "placa")):
            eh_veiculo = True
        else:
            resumo["abas"].append(f"{nome_aba}: colunas não reconhecidas")
            continue
        if not eh_veiculo:
            faltam = [c for c in ("data", "odometro", "litros") if c not in mapa]
            if faltam:
                resumo["abas"].append(
                    f"{nome_aba}: faltam colunas obrigatórias ({', '.join(faltam)})")
                continue
        preparadas.append({"nome": nome_aba, "mapa": mapa, "dados": dados,
                           "eh_veiculo": eh_veiculo})

    preparadas.sort(key=lambda a: 0 if a["eh_veiculo"] else 1)  # veículos primeiro

    for aba in preparadas:
        mapa, dados = aba["mapa"], aba["dados"]

        def val(linha, campo):
            i = mapa.get(campo)
            return linha[i] if i is not None and i < len(linha) else None

        if aba["eh_veiculo"]:
            n = 1
            for linha in dados:
                n += 1
                nome = _texto(val(linha, "nome") or val(linha, "veiculo"))
                if not nome:
                    ignoradas.append(f"{aba['nome']} · linha {n}: sem nome")
                    continue
                ano = re.sub(r"\D", "", _texto(val(linha, "ano")))
                garantir(nome, {
                    "plate": _texto(val(linha, "placa")),
                    "year": int(ano) if len(ano) == 4 else None,
                    "fuel": fuel_any(val(linha, "combustivel")) or "Gasolina",
                    "notes": _texto(val(linha, "obs")),
                    "initial_km": parse_num_any(val(linha, "kminicial")),
                })
                resumo["linhas"] += 1
            resumo["abas"].append(f"{aba['nome']}: aba de veículos")
            continue

        n_linha, ultimo = 1, nome_padrao
        for linha in dados:
            resumo["linhas"] += 1
            n_linha += 1
            rot = f"{aba['nome']} · linha {n_linha}"
            data = parse_data_any(val(linha, "data"))
            km = parse_num_any(val(linha, "odometro"))
            litros = parse_num_any(val(linha, "litros"))
            preco = parse_num_any(val(linha, "preco"))
            total = parse_num_any(val(linha, "total"))
            if not data:
                ignoradas.append(f"{rot}: data inválida")
                continue
            if not (km and km > 0):
                ignoradas.append(f"{rot}: odômetro inválido")
                continue
            if not (litros and litros > 0):
                ignoradas.append(f"{rot}: litros inválidos")
                continue
            if not ((total and total > 0) or (preco and preco > 0)):
                ignoradas.append(f"{rot}: sem preço nem total")
                continue
            if not preco or preco <= 0:
                preco = total / litros
            if not total or total <= 0:
                total = litros * preco
            nome = _texto(val(linha, "veiculo") or val(linha, "nome")) or ultimo
            veiculo = garantir(nome)
            if veiculo is None:
                ignoradas.append(f"{rot}: veículo sem nome")
                continue
            ultimo = veiculo.name
            doc.refuels.append(Refuel(
                vehicle_id=veiculo.id,
                date=data,
                odometer=km,
                liters=litros,
                price=round(preco, 2),
                total=round(total, 2),
                full_tank=parse_bool_any(val(linha, "tanque")),
                station=_texto(val(linha, "posto")),
                notes=_texto(val(linha, "obs")),
            ))
            resumo["novos"] += 1
        resumo["abas"].append(f"{aba['nome']}: aba de abastecimentos")

    for veiculo in doc.vehicles:
        if inicial.get(veiculo.id) is None:
            kms = [r.odometer for r in doc.refuels if r.vehicle_id == veiculo.id]
            veiculo.initial_km = min(kms) if kms else 0.0
        else:
            veiculo.initial_km = inicial[veiculo.id]
    resumo["veiculos"] = len(doc.vehicles)
    return doc, resumo, ignoradas


def mesclar_documento(novo: Document, atual: Document) -> dict:
    """Junta ``novo`` em ``atual`` sem duplicar. Devolve os contadores."""
    mapa_id: dict[str, str] = {}
    novos_veiculos = novos_refuels = duplicados = 0
    for veiculo in novo.vehicles:
        existente = next(
            (x for x in atual.vehicles if norm(x.name) == norm(veiculo.name)), None)
        if existente is not None:
            if not existente.plate and veiculo.plate:
                existente.plate = veiculo.plate
            if not existente.year and veiculo.year:
                existente.year = veiculo.year
            if veiculo.notes and not existente.notes:
                existente.notes = veiculo.notes
            if veiculo.initial_km and (
                    not existente.initial_km or veiculo.initial_km < existente.initial_km):
                existente.initial_km = veiculo.initial_km
            mapa_id[veiculo.id] = existente.id
        else:
            atual.vehicles.append(veiculo)
            mapa_id[veiculo.id] = veiculo.id
            novos_veiculos += 1

    ids = {v.id for v in atual.vehicles}
    vistas = {(r.vehicle_id, r.date, r.odometer) for r in atual.refuels}
    for refuel in novo.refuels:
        vid = mapa_id.get(refuel.vehicle_id, refuel.vehicle_id)
        chave = (vid, refuel.date, refuel.odometer)
        if vid not in ids or chave in vistas:
            duplicados += 1
            continue
        vistas.add(chave)
        refuel.vehicle_id = vid
        atual.refuels.append(refuel)
        novos_refuels += 1
    return {"veiculos": novos_veiculos, "refuels": novos_refuels,
            "duplicados": duplicados}


TEXTO_FORMATO = """\
IMPORTAR PLANILHA OU CSV (Arquivo > Importar planilha/CSV...)

Arquivos aceitos: .csv, .tsv, .txt e .xlsx/.xlsm (até 2 abas).
O separador é detectado sozinho (ponto e vírgula, vírgula, aba do Excel ou |),
as aspas do Excel são respeitadas e a ordem das colunas não importa: o que vale
é o nome do cabeçalho, em português ou inglês.

COLUNAS DA ABA DE ABASTECIMENTOS
  Veículo          opcional  vazio = repete o veículo da linha anterior
  Data             OBRIGATÓRIA  05/07/2026, 2026-07-05 ou data do Excel
  Odômetro (km)    OBRIGATÓRIA  41500 ou 41.500
  Litros           OBRIGATÓRIA  38,00
  Preço por litro  OBRIGATÓRIA  dá para preencher só o Total (aí um calcula o outro)
  Total            opcional    vazio = litros x preço
  Tanque cheio     opcional    sim/não, 1/0, x; vazio = não
  Posto            opcional
  Observações      opcional

COLUNAS DA ABA "VEÍCULOS" DO .XLSX
  Nome, Placa, Ano, Combustível, Km inicial, Observações

SEM CABEÇALHO a ordem padrão é:
  Data; Odômetro; Litros; Preço por litro; Total; Tanque cheio; Posto; Observações

Números aceitam formato brasileiro (1.234,56) e americano (1,234.56).
O formato antigo .xls não é lido: no Excel use "Salvar como" -> .xlsx ou .csv.
"""
