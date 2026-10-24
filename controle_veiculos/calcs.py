"""Cálculos de consumo, custo e relatórios."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from .format import fmt_number
from .models import Document, Maintenance, Refuel

# Emissão de CO2 estimada pela queima do combustível (kg de CO2 por litro).
# Etanol e elétrico contam como zero fóssil; flex e híbrido, na falta do
# combustível de cada abastecimento, usam o fator da gasolina.
CO2_FACTORS = {
    "gasolina": 2.21, "flex": 2.21, "híbrido": 2.21, "hibrido": 2.21,
    "diesel": 2.60, "gnv": 1.96, "etanol": 0.0,
    "elétrico": 0.0, "eletrico": 0.0, "outro": 0.0,
}
CO2_NOTE = ("CO₂ estimado pela queima do combustível. Etanol e elétrico contam "
            "como zero fóssil; flex e híbrido usam o fator da gasolina.")


def co2_per_liter(fuel: str) -> float:
    return CO2_FACTORS.get((fuel or "").strip().lower(), 0.0)


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
    co2: float = 0.0  # kg de CO2 estimado (queima do combustível)
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
    co2: float = 0.0  # kg de CO2 estimado
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

    fuel_of = {v.id: v.fuel for v in doc.vehicles}
    stats = Stats(count=len(triples))
    stats.km = sum(triple[2] for triple in triples)
    stats.liters = sum(triple[0].liters for triple in triples)
    stats.spent = sum(triple[0].total for triple in triples)
    stats.co2 = sum(triple[0].liters * co2_per_liter(fuel_of.get(triple[0].vehicle_id, ""))
                    for triple in triples)
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
        row.co2 = sum(r.liters * co2_per_liter(fuel_of.get(r.vehicle_id, "")) for r, _ in items)
        row.maint_spent = maint_grouped.get(key, 0.0)
        row.total = row.spent + row.maint_spent
        if row.liters > 0 and row.km > 0:
            row.km_per_l = row.km / row.liters
        if row.km > 0:
            row.cost_per_km = row.spent / row.km
        months.append(row)

    return ReportView(stats=stats, series=series, months=months)


# ===================== Frota: painel, documentos, motoristas =====================

@dataclass
class FleetCard:
    """Linha do painel da frota: um veículo e seus números do mês atual."""
    vehicle: object  # Vehicle
    km: float = 0.0
    km_per_l: float | None = None
    month_spent: float = 0.0
    month_co2: float = 0.0
    worst: Reminder | None = None  # revisão mais urgente (ou None)


@dataclass
class FleetSummary:
    cards: list[FleetCard] = field(default_factory=list)
    total_spent: float = 0.0
    total_co2: float = 0.0
    alert_vehicles: int = 0  # veículos com revisão atrasada/próxima


def _month_start(today: dt.date) -> str:
    return f"{today.year:04d}-{today.month:02d}-01"


def fleet_summary(doc: Document, today: dt.date | None = None) -> FleetSummary:
    today = today or dt.date.today()
    m_start = _month_start(today)
    m_end = today.isoformat()
    out = FleetSummary()
    for v in doc.vehicles:
        all_view = report(doc, [v.id])
        month_view = report(doc, [v.id], m_start, m_end)
        rem = reminders(doc, v.id, today)
        worst = next((r for r in rem if r.level != "ok"), None)
        card = FleetCard(
            vehicle=v,
            km=current_km(doc, v.id),
            km_per_l=all_view.stats.km_per_l,
            month_spent=month_view.stats.total_spent,
            month_co2=month_view.stats.co2,
            worst=worst,
        )
        out.cards.append(card)
        out.total_spent += card.month_spent
        out.total_co2 += card.month_co2
        if worst:
            out.alert_vehicles += 1
    return out


@dataclass
class DocReminder:
    document: dict
    vehicle_name: str = "—"
    remaining_days: int | None = None
    level: str = "ok"  # "atrasada" | "proxima" | "ok"


def doc_reminders(doc: Document, today: dt.date | None = None) -> list[DocReminder]:
    """Documentos pendentes (não resolvidos), ordenados por urgência."""
    today = today or dt.date.today()
    nomes = {v.id: v.name for v in doc.vehicles}
    out: list[DocReminder] = []
    for dc in doc.documents:
        if not isinstance(dc, dict) or dc.get("done"):
            continue
        remaining = None
        level = "ok"
        due = dc.get("due_date")
        if due:
            try:
                remaining = (dt.date.fromisoformat(str(due)) - today).days
                level = "atrasada" if remaining <= 0 else ("proxima" if remaining <= 30 else "ok")
            except ValueError:
                remaining = None
        out.append(DocReminder(
            document=dc,
            vehicle_name=nomes.get(dc.get("vehicle_id"), "—"),
            remaining_days=remaining,
            level=level,
        ))
    out.sort(key=lambda x: ({"atrasada": 0, "proxima": 1, "ok": 2}[x.level],
                            x.remaining_days if x.remaining_days is not None else 10**9))
    return out


def doc_alert_count(doc: Document, today: dt.date | None = None) -> int:
    return sum(1 for x in doc_reminders(doc, today) if x.level != "ok")


def refuel_flags(doc: Document, vehicle_id: str) -> dict[str, list[str]]:
    """Abastecimentos suspeitos: litros acima do tanque, odômetro que retrocede
    ou consumo muito fora da mediana. Retorna {refuel_id: [motivos...]}."""
    vehicle = doc.get_vehicle(vehicle_id)
    tank = float(getattr(vehicle, "tank_capacity", 0.0) or 0.0) if vehicle else 0.0
    by_date = sorted(
        (r for r in doc.refuels if r.vehicle_id == vehicle_id),
        key=lambda r: (r.date, r.odometer, r.id),
    )
    segs = build_segments(ordered_refuels(doc, vehicle_id))
    kmpls = sorted(s.km_per_l for s in segs.values()
                   if s and not s.approximate and s.km_per_l and s.km_per_l > 0)
    median = kmpls[len(kmpls) // 2] if kmpls else None
    out: dict[str, list[str]] = {}
    prev_odo = None
    for r in by_date:
        w: list[str] = []
        if tank > 0 and r.liters > tank * 1.05:
            w.append(f"Litros ({fmt_number(r.liters, 0)}) acima do tanque ({fmt_number(tank, 0)} L)")
        if prev_odo is not None and r.odometer < prev_odo:
            w.append(f"Odômetro ({fmt_number(r.odometer, 0)} km) menor que o anterior ({fmt_number(prev_odo, 0)} km)")
        seg = segs.get(r.id)
        if (median and seg and not seg.approximate and seg.km_per_l
                and abs(seg.km_per_l - median) / median > 0.45):
            w.append(f"Consumo ({fmt_number(seg.km_per_l, 1)} km/L) fora da média ({fmt_number(median, 1)} km/L)")
        if w:
            out[r.id] = w
        prev_odo = r.odometer
    return out


@dataclass
class DriverRow:
    name: str
    count: int = 0
    km: float = 0.0
    liters: float = 0.0
    spent: float = 0.0
    co2: float = 0.0

    @property
    def km_per_l(self) -> float | None:
        return self.km / self.liters if self.km > 0 and self.liters > 0 else None


def driver_report(doc: Document, vehicle_ids: list[str],
                  start_iso: str | None = None, end_iso: str | None = None) -> list[DriverRow]:
    """Consumo/gasto por motorista no período. 'Sem motorista' vai por último."""
    names = {d.get("id"): d.get("name", "") for d in doc.drivers if isinstance(d, dict)}
    buckets: dict[str, DriverRow] = {}
    for vid in vehicle_ids:
        vehicle = doc.get_vehicle(vid)
        ordered = ordered_refuels(doc, vid)
        distances = build_distances(ordered, vehicle.initial_km if vehicle else 0.0)
        fuel = vehicle.fuel if vehicle else ""
        for r in ordered:
            if not in_period(r.date, start_iso, end_iso):
                continue
            key = getattr(r, "driver_id", "") or "__none__"
            row = buckets.get(key)
            if row is None:
                nome = "Sem motorista" if key == "__none__" else (names.get(key) or "—")
                row = buckets[key] = DriverRow(name=nome)
            row.count += 1
            row.km += distances.get(r.id, 0.0)
            row.liters += r.liters
            row.spent += r.total
            row.co2 += r.liters * co2_per_liter(fuel)
    assigned = [row for k, row in buckets.items() if k != "__none__"]
    assigned.sort(key=lambda x: -x.spent)
    if "__none__" in buckets:
        assigned.append(buckets["__none__"])
    # Só faz sentido mostrar se houver ao menos um motorista atribuído
    return assigned if any(k != "__none__" for k in buckets) else []
