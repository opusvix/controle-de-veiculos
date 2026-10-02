"""Modelos de dados: veículos, abastecimentos e documento (arquivo)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

FUELS = ["Gasolina", "Etanol", "Flex", "Diesel", "GNV", "Elétrico", "Híbrido", "Outro"]

# Tipos de serviço sugeridos no formulário de manutenções (aceita texto livre).
MAINT_TYPES = [
    "Troca de óleo",
    "Filtro de óleo",
    "Filtro de ar",
    "Filtro de combustível",
    "Filtro de cabine",
    "Pastilhas de freio",
    "Discos de freio",
    "Fluido de freio",
    "Correia dentada",
    "Bateria",
    "Balanceamento",
    "Alinhamento",
    "Pneus",
    "Suspensão",
    "Amortecedores",
    "Óleo/câmbio",
    "Lavagem",
    "Revisão",
    "Documentação",
    "Outro",
]


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def _f(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _i(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _s(value) -> str:
    return value if isinstance(value, str) else ("" if value is None else str(value))


@dataclass
class Vehicle:
    id: str = field(default_factory=new_id)
    name: str = ""
    plate: str = ""
    year: int | None = None
    fuel: str = "Gasolina"
    initial_km: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "plate": self.plate,
            "year": self.year,
            "fuel": self.fuel,
            "initial_km": self.initial_km,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Vehicle":
        return cls(
            id=_s(d.get("id")) or new_id(),
            name=_s(d.get("name")),
            plate=_s(d.get("plate")),
            year=_i(d.get("year")),
            fuel=_s(d.get("fuel")) or "Gasolina",
            initial_km=_f(d.get("initial_km")),
            notes=_s(d.get("notes")),
        )


@dataclass
class Refuel:
    id: str = field(default_factory=new_id)
    vehicle_id: str = ""
    date: str = ""  # ISO: 2026-09-25
    odometer: float = 0.0  # km no odômetro
    liters: float = 0.0
    price: float = 0.0  # R$ por litro
    total: float = 0.0  # R$ total
    full_tank: bool = False
    station: str = ""
    notes: str = ""

    @property
    def total_computed(self) -> float:
        return round(self.liters * self.price, 2)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "vehicle_id": self.vehicle_id,
            "date": self.date,
            "odometer": self.odometer,
            "liters": self.liters,
            "price": self.price,
            "total": self.total,
            "full_tank": bool(self.full_tank),
            "station": self.station,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Refuel":
        liters = _f(d.get("liters"))
        price = _f(d.get("price"))
        total = d.get("total")
        return cls(
            id=_s(d.get("id")) or new_id(),
            vehicle_id=_s(d.get("vehicle_id")),
            date=_s(d.get("date")),
            odometer=_f(d.get("odometer")),
            liters=liters,
            price=price,
            total=_f(total, liters * price),
            full_tank=bool(d.get("full_tank")),
            station=_s(d.get("station")),
            notes=_s(d.get("notes")),
        )


@dataclass
class Maintenance:
    """Serviço feito no veículo: troca de óleo, alinhamento, freios etc."""

    id: str = field(default_factory=new_id)
    vehicle_id: str = ""
    date: str = ""  # ISO: 2026-09-25
    odometer: float = 0.0  # km no momento do serviço
    type: str = ""  # "Troca de óleo" (aceita texto livre)
    details: str = ""  # descrição dos serviços/executados
    cost: float = 0.0  # R$ total
    shop: str = ""  # oficina/local
    notes: str = ""
    next_km: float | None = None  # repetir a cada X km
    next_date: str | None = None  # próxima em data (ISO)

    @property
    def due_km(self) -> float | None:
        """Quilometragem em que este serviço vence (intervalo informado)."""
        if self.next_km and self.next_km > 0:
            return self.odometer + self.next_km
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "vehicle_id": self.vehicle_id,
            "date": self.date,
            "odometer": self.odometer,
            "type": self.type,
            "details": self.details,
            "cost": self.cost,
            "shop": self.shop,
            "notes": self.notes,
            "next_km": self.next_km,
            "next_date": self.next_date,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Maintenance":
        next_km = _f(d.get("next_km"), 0.0)
        return cls(
            id=_s(d.get("id")) or new_id(),
            vehicle_id=_s(d.get("vehicle_id")),
            date=_s(d.get("date")),
            odometer=_f(d.get("odometer")),
            type=_s(d.get("type")),
            details=_s(d.get("details")),
            cost=_f(d.get("cost")),
            shop=_s(d.get("shop")),
            notes=_s(d.get("notes")),
            next_km=next_km if next_km > 0 else None,
            next_date=_s(d.get("next_date")) or None,
        )


@dataclass
class Document:
    """Conteúdo do arquivo JSON salvo no computador."""

    version: int = 2
    vehicles: list[Vehicle] = field(default_factory=list)
    refuels: list[Refuel] = field(default_factory=list)
    maintenances: list[Maintenance] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "vehicles": [v.to_dict() for v in self.vehicles],
            "refuels": [r.to_dict() for r in self.refuels],
            "maintenances": [m.to_dict() for m in self.maintenances],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Document":
        doc = cls(version=_i(d.get("version")) or 2)
        seen_vehicles: set[str] = set()
        seen_refuels: set[str] = set()
        seen_maint: set[str] = set()
        for item in d.get("vehicles") or []:
            try:
                vehicle = Vehicle.from_dict(item)
            except Exception:
                continue
            if vehicle.id in seen_vehicles:  # arquivo editado à mão: garante ids únicos
                vehicle.id = new_id()
            seen_vehicles.add(vehicle.id)
            doc.vehicles.append(vehicle)
        for item in d.get("refuels") or []:
            try:
                refuel = Refuel.from_dict(item)
            except Exception:
                continue
            if refuel.id in seen_refuels:
                refuel.id = new_id()
            seen_refuels.add(refuel.id)
            doc.refuels.append(refuel)
        for item in d.get("maintenances") or []:
            try:
                maintenance = Maintenance.from_dict(item)
            except Exception:
                continue
            if maintenance.id in seen_maint:
                maintenance.id = new_id()
            seen_maint.add(maintenance.id)
            doc.maintenances.append(maintenance)
        return doc

    def get_vehicle(self, vehicle_id: str | None) -> Vehicle | None:
        if not vehicle_id:
            return None
        for v in self.vehicles:
            if v.id == vehicle_id:
                return v
        return None

    def vehicle_refuels(self, vehicle_id: str) -> list[Refuel]:
        return [r for r in self.refuels if r.vehicle_id == vehicle_id]

    def vehicle_maintenances(self, vehicle_id: str) -> list[Maintenance]:
        return [m for m in self.maintenances if m.vehicle_id == vehicle_id]

    def get_refuel(self, refuel_id: str) -> Refuel | None:
        for r in self.refuels:
            if r.id == refuel_id:
                return r
        return None

    def get_maintenance(self, maintenance_id: str) -> Maintenance | None:
        for m in self.maintenances:
            if m.id == maintenance_id:
                return m
        return None
