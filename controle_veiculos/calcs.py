"""Cálculos de consumo, custo e relatórios."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from .format import fmt_number
from .models import Document, Maintenance, Refuel


@dataclass
class Segment:
    """Trecho entre um abastecimento e a referência anterior (tanque cheio)."""

    refuel_id: str
    distance: float = 0.0
    liters: float = 0.0
    cost: float = 0.0
    km_per_l: float | None = None
    l_per_100km: float | None = None
    cost_per_km: float | None = None
    approximate: bool = True  # True quando a referência não era tanque cheio


@dataclass
class Stats:
    count: int = 0
    km: float = 0.0
    liters: float = 0.0
    spent: float = 0.0
    maint_count: int = 0
    maint_spent: float = 0.0
    total_spent: float = 0.0
    avg_price: float | None = None
    km_per_l: float | None = None
    l_per_100km: float | None = None
    cost_per_km: float | None = None
    cost_per_km_total: float | None = None
    avg_spent: float | None = None


@dataclass
class MonthRow:
    label: str  # 09/2026
    count: int = 0
    km: float = 0.0
    liters: float = 0.0
    spent: float = 0.0  # combustível
    maint_spent: float = 0.0  # manutenção
    total: float = 0.0  # combustível + manutenção
    km_per_l: float | None = None
    cost_per_km: float | None = None


@dataclass
class Reminder:
    """Aviso da próxima manutenção pendente de um tipo de serviço."""

    maintenance: Maintenance
    level: str = "ok"  # "atrasada" | "proxima" | "ok"
    label: str = ""  # "Em 480 km" / "Em 12 dias"
    detail: str = ""  # "vence em 15/10/2026 (45.500 km)"
    remaining_km: float | None = None
    remaining_days: int | None = None


@dataclass
class ReportView:
    stats: Stats
    series: list[tuple[Refuel, Segment | None]] = field(default_factory=list)
    months: list[MonthRow] = field(default_factory=list)


def ordered_refuels(doc: Document, vehicle_id: str) -> list[Refuel]:
    """Abastecimentos do veículo em ordem crescente de odômetro."""
    refs = doc.vehicle_refuels(vehicle_id)
    refs.sort(key=lambda r: (r.odometer, r.date, r.id))
    return refs


def ordered_maintenances(doc: Document, vehicle_id: str) -> list[Maintenance]:
    """Manutenções do veículo em ordem crescente de data."""
    items = doc.vehicle_maintenances(vehicle_id)
    items.sort(key=lambda m: (m.date, m.odometer, m.id))
    return items


def current_km(doc: Document, vehicle_id: str) -> float:
    """Maior quilometragem conhecida do veículo (abastecimentos, manutenções e km inicial)."""
    vehicle = doc.get_vehicle(vehicle_id)
    km = float(vehicle.initial_km) if vehicle else 0.0
    for record in doc.vehicle_refuels(vehicle_id):
        km = max(km, record.odometer)
    for record in doc.vehicle_maintenances(vehicle_id):
        km = max(km, record.odometer)
    return km


def reminders(doc: Document, vehicle_id: str, today: dt.date | None = None) -> list[Reminder]:
    """Próxima manutenção pendente de cada tipo de serviço.

    Só o registro mais recente de cada tipo gera aviso (um serviço novo "fecha"
    o aviso do anterior), e apenas se ele tiver km intervalo ou data informados.
    """
    today = today or dt.date.today()
    km_now = current_km(doc, vehicle_id)
    latest: dict[str, Maintenance] = {}
    for record in ordered_maintenances(doc, vehicle_id):
        key = (record.type or "").strip().lower()
        if key:
            latest[key] = record  # iteração em ordem crescente -> fica o mais recente

    out: list[Reminder] = []
    for record in latest.values():
        if not (record.next_km or record.next_date):
            continue
        due_km = record.due_km
        remaining_km = None if due_km is None else due_km - km_now
        remaining_days = None
        due_date = None
        if record.next_date:
            try:
                due_date = dt.date.fromisoformat(record.next_date)
            except ValueError:
                due_date = None
            if due_date:
                remaining_days = (due_date - today).days

        overdue = ((remaining_km is not None and remaining_km <= 0)
                   or (remaining_days is not None and remaining_days <= 0))
        soon_km = (remaining_km is not None
                   and remaining_km <= max(500.0, (record.next_km or 0.0) * 0.1))
        soon_days = remaining_days is not None and remaining_days <= 30
        level = "atrasada" if overdue else ("proxima" if (soon_km or soon_days) else "ok")

        if remaining_km is not None:
            label = ("Atrasada: " if remaining_km <= 0 else "Em ") + \
                    f"{fmt_number(remaining_km, 0)} km"
        elif remaining_days is not None:
            label = ("Atrasada: " if remaining_days <= 0 else "Em ") + \
                    f"{abs(remaining_days)} dia(s)"
        else:
            label = "—"

        detalhes = []
        if due_km is not None:
            detalhes.append(f"{fmt_number(due_km, 0)} km")
        if due_date:
            detalhes.append(due_date.strftime("%d/%m/%Y"))
        detail = " · ".join(detalhes)
        out.append(Reminder(
            maintenance=record,
            level=level,
            label=label,
            detail=detail,
            remaining_km=remaining_km,
            remaining_days=remaining_days,
        ))
    out.sort(key=lambda r: {"atrasada": 0, "proxima": 1, "ok": 2}[r.level])
    return out


def build_segments(refuels: list[Refuel]) -> dict[str, Segment]:
    """Calcula km/L de cada abastecimento a partir do último tanque cheio.

    Sem tanque cheio registrado o valor sai como aproximado ('~').
    """
    out: dict[str, Segment] = {}
    last_full: int | None = None
    for i, current in enumerate(refuels):
        if i == 0:
            if current.full_tank:
                last_full = 0
            continue
        base = last_full if last_full is not None else i - 1
        approximate = last_full is None or not current.full_tank
        chunk = refuels[base + 1 : i + 1]
        distance = current.odometer - refuels[base].odometer
        liters = sum(r.liters for r in chunk)
        cost = sum(r.total for r in chunk)
        seg = Segment(
            refuel_id=current.id,
            distance=distance,
            liters=liters,
            cost=cost,
            approximate=approximate,
        )
        if distance > 0 and liters > 0:
            seg.km_per_l = distance / liters
            if seg.km_per_l > 0:
                seg.l_per_100km = 100.0 / seg.km_per_l
            seg.cost_per_km = cost / distance
        out[current.id] = seg
        if current.full_tank:
            last_full = i
    return out


def build_distances(refuels: list[Refuel], initial_km: float) -> dict[str, float]:
    """Distância desde o registro anterior (base para os totais do período)."""
    out: dict[str, float] = {}
    previous = float(initial_km or 0.0)
    for r in refuels:
        delta = r.odometer - previous if previous > 0 else 0.0
        out[r.id] = delta if delta > 0 else 0.0
        previous = r.odometer
    return out


def in_period(iso_date: str, start_iso: str | None, end_iso: str | None) -> bool:
    if start_iso and iso_date < start_iso:
        return False
    if end_iso and iso_date > end_iso:
        return False
    return True


def report(
    doc: Document,
    vehicle_ids: list[str],
    start_iso: str | None = None,
    end_iso: str | None = None,
) -> ReportView:
    """Monta estatísticas, série do gráfico e resumo mensal do período."""
    triples: list[tuple[Refuel, Segment | None, float]] = []
    for vid in vehicle_ids:
        vehicle = doc.get_vehicle(vid)
        ordered = ordered_refuels(doc, vid)
        if not ordered:
            continue
        segments = build_segments(ordered)
        initial = vehicle.initial_km if vehicle else 0.0
        distances = build_distances(ordered, initial)
        for ref in ordered:
            if in_period(ref.date, start_iso, end_iso):
                triples.append((ref, segments.get(ref.id), distances.get(ref.id, 0.0)))

    triples.sort(key=lambda t: (t[0].date, t[0].odometer))

    stats = Stats(count=len(triples))
    stats.km = sum(triple[2] for triple in triples)
    stats.liters = sum(triple[0].liters for triple in triples)
    stats.spent = sum(triple[0].total for triple in triples)
    if stats.liters > 0:
        stats.avg_price = stats.spent / stats.liters
    if stats.liters > 0 and stats.km > 0:
        stats.km_per_l = stats.km / stats.liters
        stats.l_per_100km = 100.0 / stats.km_per_l
    if stats.km > 0:
        stats.cost_per_km = stats.spent / stats.km
    if stats.count:
        stats.avg_spent = stats.spent / stats.count

    series = [(r, seg) for r, seg, _ in triples]

    # Manutenções do período (entram no relatório em linha separada)
    maints: list[Maintenance] = []
    for vid in vehicle_ids:
        for record in doc.vehicle_maintenances(vid):
            if in_period(record.date, start_iso, end_iso):
                maints.append(record)
    stats.maint_count = len(maints)
    stats.maint_spent = sum(record.cost for record in maints)
    stats.total_spent = stats.spent + stats.maint_spent
    if stats.km > 0:
        stats.cost_per_km_total = stats.total_spent / stats.km

    # Resumo mensal
    grouped: dict[str, list[tuple[Refuel, float]]] = {}
    for record, _, delta in triples:
        grouped.setdefault(record.date[:7], []).append((record, delta))
    maint_grouped: dict[str, float] = {}
    for record in maints:
        if len(record.date) < 7 or not record.date[:4].isdigit():
            continue  # data inválida: conta no total do período, não no resumo mensal
        key = record.date[:7]
        maint_grouped[key] = maint_grouped.get(key, 0.0) + record.cost

    months: list[MonthRow] = []
    for key in sorted(set(grouped) | set(maint_grouped), reverse=True):
        items = grouped.get(key, [])
        row = MonthRow(label=f"{key[5:7]}/{key[0:4]}", count=len(items))
        row.km = sum(d for _, d in items)
        row.liters = sum(r.liters for r, _ in items)
        row.spent = sum(r.total for r, _ in items)
        row.maint_spent = maint_grouped.get(key, 0.0)
        row.total = row.spent + row.maint_spent
        if row.liters > 0 and row.km > 0:
            row.km_per_l = row.km / row.liters
        if row.km > 0:
            row.cost_per_km = row.spent / row.km
        months.append(row)

    return ReportView(stats=stats, series=series, months=months)
