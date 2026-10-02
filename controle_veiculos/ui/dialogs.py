"""Diálogos modais: novo/editar abastecimento e novo/editar veículo."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .. import format as fmt
from ..models import FUELS, MAINT_TYPES, Maintenance, Refuel, Vehicle, new_id


def _center(window: tk.Misc, parent: tk.Misc) -> None:
    window.update_idletasks()
    try:
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        w = window.winfo_width()
        h = window.winfo_height()
        x = max(px + (pw - w) // 2, 0)
        y = max(py + (ph - h) // 2, 0)
        window.geometry(f"+{x}+{y}")
    except tk.TclError:
        pass


class _Dialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, title: str):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)
        self.result = None
        self.body = ttk.Frame(self, padding=16)
        self.body.pack(fill="both", expand=True)
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def open(self):
        _center(self, self.master)  # type: ignore[arg-type]
        self.lift()
        self.focus_force()
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.wait_window(self)
        return self.result

    def cancel(self):
        self.result = None
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def accept(self, result):
        self.result = result
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()


def _add_entry(parent, row, col, label, var=None, width=14, initial=""):
    ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=(0, 18), pady=(6, 2))
    entry = ttk.Entry(parent, width=width, textvariable=var)
    if var is None:
        entry.insert(0, initial)
    entry.grid(row=row + 1, column=col, sticky="we", padx=(0, 18), pady=(0, 2))
    return entry


def refuel_dialog(parent, doc, vehicle_id, refuel: Refuel | None = None) -> Refuel | None:
    """Abre o formulário de abastecimento. Retorna o registro ou None (cancelado)."""
    editing = refuel is not None
    dlg = _Dialog(parent, "Editar abastecimento" if editing else "Novo abastecimento")
    body = dlg.body
    body.columnconfigure(0, weight=1)
    body.columnconfigure(1, weight=1)

    last = None
    ordered = sorted(
        [r for r in doc.refuels if r.vehicle_id == vehicle_id],
        key=lambda r: (r.odometer, r.date),
    )
    if ordered:
        last = ordered[-1]

    e_date = _add_entry(body, 0, 0, "Data (dd/mm/aaaa)", width=14)
    e_km = _add_entry(body, 0, 1, "Odômetro (km)", width=14)
    e_liters = _add_entry(body, 1, 0, "Litros", width=14)
    e_price = _add_entry(body, 1, 1, "Preço por litro (R$)", width=14)
    e_total = _add_entry(body, 2, 0, "Total (R$)", width=14)
    e_station = _add_entry(body, 2, 1, "Posto", width=18)

    chk_full = tk.BooleanVar(value=True if not editing else refuel.full_tank)  # type: ignore[union-attr]
    ttk.Checkbutton(body, text="Tanque cheio", variable=chk_full).grid(
        row=3, column=0, sticky="w", pady=(8, 2)
    )

    ttk.Label(body, text="Observações").grid(row=4, column=0, columnspan=2, sticky="w",
                                             padx=(0, 18), pady=(6, 2))
    e_notes = ttk.Entry(body, width=44)
    e_notes.grid(row=5, column=0, columnspan=2, sticky="we", pady=(0, 4))

    hint = ttk.Label(
        body,
        text=(
            f"Último registro: {fmt.fmt_number(last.odometer, 1)} km em {fmt.fmt_date(last.date)}"
            if last
            else "Primeiro registro deste veículo (use o odômetro atual)."
        ),
        foreground="#5b6472",
    )
    hint.grid(row=6, column=0, columnspan=2, sticky="w", pady=(4, 2))

    error_var = tk.StringVar(value="")
    err = ttk.Label(body, textvariable=error_var, foreground="#dc2626")
    err.grid(row=7, column=0, columnspan=2, sticky="w", pady=(2, 4))

    if editing:
        e_date.insert(0, fmt.fmt_date(refuel.date))  # type: ignore[union-attr]
        e_km.insert(0, fmt.fmt_number(refuel.odometer, 1))  # type: ignore[union-attr]
        e_liters.insert(0, fmt.fmt_number(refuel.liters, 2))  # type: ignore[union-attr]
        e_price.insert(0, fmt.fmt_number(refuel.price, 3))  # type: ignore[union-attr]
        e_total.insert(0, fmt.fmt_number(refuel.total, 2))  # type: ignore[union-attr]
        e_station.insert(0, refuel.station)  # type: ignore[union-attr]
        e_notes.insert(0, refuel.notes)  # type: ignore[union-attr]
    else:
        e_date.insert(0, fmt.today_input())
        if last:
            e_price.insert(0, fmt.fmt_number(last.price, 3))

    auto_total = tk.BooleanVar(value=not editing)

    def _recalc(_event=None):
        if not auto_total.get():
            return
        liters = fmt.parse_number(e_liters.get())
        price = fmt.parse_number(e_price.get())
        if liters and price and liters > 0 and price > 0:
            e_total.delete(0, "end")
            e_total.insert(0, fmt.fmt_number(round(liters * price, 2), 2))

    for entry in (e_liters, e_price):
        entry.bind("<KeyRelease>", _recalc)

    def _mark_manual(_event=None):
        auto_total.set(False)

    e_total.bind("<KeyRelease>", _mark_manual)
    _recalc()

    def save():
        error_var.set("")
        date = fmt.parse_date(e_date.get())
        if date is None:
            error_var.set("Data inválida. Use o formato dd/mm/aaaa.")
            e_date.focus_set()
            return
        km = fmt.parse_number(e_km.get())
        if km is None or km <= 0:
            error_var.set("Odômetro inválido: informe os quilômetros totais (ex.: 45.120).")
            e_km.focus_set()
            return
        liters = fmt.parse_number(e_liters.get())
        if liters is None or liters <= 0:
            error_var.set("Litros inválidos: informe quantidade maior que zero.")
            e_liters.focus_set()
            return
        price = fmt.parse_number(e_price.get())
        if price is None or price <= 0:
            error_var.set("Preço por litro inválido.")
            e_price.focus_set()
            return
        total = fmt.parse_number(e_total.get())
        if total is None or total <= 0:
            total = round(liters * price, 2)

        others = [r for r in doc.refuels if r.vehicle_id == vehicle_id]
        if refuel is not None:
            others = [r for r in others if r.id != refuel.id]
        if others:
            max_km = max(r.odometer for r in others)
            if km <= max_km:
                error_var.set(
                    f"O odômetro deve ser maior que o último registro "
                    f"({fmt.fmt_number(max_km, 1)} km)."
                )
                e_km.focus_set()
                return

        record = Refuel(
            id=refuel.id if refuel is not None else new_id(),
            vehicle_id=vehicle_id,
            date=date.isoformat(),
            odometer=km,
            liters=liters,
            price=price,
            total=round(total, 2),
            full_tank=bool(chk_full.get()),
            station=e_station.get().strip(),
            notes=e_notes.get().strip(),
        )
        dlg.accept(record)

    buttons = ttk.Frame(body)
    buttons.grid(row=8, column=0, columnspan=2, sticky="e", pady=(10, 0))
    ttk.Button(buttons, text="Salvar", style="Accent.TButton", command=save).pack(
        side="left", padx=(0, 8)
    )
    ttk.Button(buttons, text="Cancelar", command=dlg.cancel).pack(side="left")

    for entry in (e_date, e_km, e_liters, e_price, e_total, e_station, e_notes):
        entry.bind("<Return>", lambda _e: save())
    dlg.bind("<Escape>", lambda _e: dlg.cancel())

    return dlg.open()


def maintenance_dialog(parent, doc, vehicle_id,
                       record: Maintenance | None = None) -> Maintenance | None:
    """Formulário de manutenção. Retorna o registro ou None (cancelado)."""
    editing = record is not None
    dlg = _Dialog(parent, "Editar manutenção" if editing else "Nova manutenção")
    body = dlg.body
    for col in range(4):
        body.columnconfigure(col, weight=1, uniform="m")

    e_date = _add_entry(body, 0, 0, "Data (dd/mm/aaaa)", width=14)
    e_km = _add_entry(body, 0, 1, "Odômetro (km)", width=14)

    ttk.Label(body, text="Tipo de serviço *").grid(row=0, column=2, sticky="w",
                                                   padx=(0, 18), pady=(6, 2))
    cmb_type = ttk.Combobox(body, values=MAINT_TYPES, width=22)
    cmb_type.grid(row=1, column=2, sticky="we", padx=(0, 18), pady=(0, 2))

    e_cost = _add_entry(body, 0, 3, "Custo (R$)", width=12)

    e_shop = _add_entry(body, 2, 0, "Oficina / local", width=20)
    e_next_km = _add_entry(body, 2, 1, "Repetir a cada (km)", width=14)
    e_next_date = _add_entry(body, 2, 2, "Próxima em (data)", width=14)
    e_details = _add_entry(body, 2, 3, "Serviços executados", width=22)

    ttk.Label(body, text="Observações").grid(row=4, column=0, columnspan=4, sticky="w",
                                             pady=(6, 2))
    e_notes = tk.Text(body, width=52, height=3, wrap="word")
    e_notes.grid(row=5, column=0, columnspan=4, sticky="we", pady=(0, 4))

    hint = ttk.Label(
        body,
        text="Preencha data, quilometragem e o tipo do serviço.",
        foreground="#5b6472",
    )
    hint.grid(row=6, column=0, columnspan=4, sticky="w", pady=(4, 2))

    error_var = tk.StringVar(value="")
    ttk.Label(body, textvariable=error_var, foreground="#dc2626").grid(
        row=7, column=0, columnspan=4, sticky="w", pady=(2, 4)
    )

    if editing:
        e_date.insert(0, fmt.fmt_date(record.date))  # type: ignore[union-attr]
        e_km.insert(0, fmt.fmt_number(record.odometer, 1))  # type: ignore[union-attr]
        cmb_type.set(record.type or "")  # type: ignore[union-attr]
        e_cost.insert(0, fmt.fmt_number(record.cost, 2) if record.cost else "")  # type: ignore[union-attr]
        e_shop.insert(0, record.shop)  # type: ignore[union-attr]
        if record.next_km:  # type: ignore[union-attr]
            e_next_km.insert(0, fmt.fmt_number(record.next_km, 0))  # type: ignore[union-attr]
        if record.next_date:  # type: ignore[union-attr]
            e_next_date.insert(0, fmt.fmt_date(record.next_date))  # type: ignore[union-attr]
        e_details.insert(0, record.details)  # type: ignore[union-attr]
        e_notes.insert("1.0", record.notes)  # type: ignore[union-attr]
    else:
        e_date.insert(0, fmt.today_input())

    def save():
        error_var.set("")
        date = fmt.parse_date(e_date.get())
        if date is None:
            error_var.set("Data inválida. Use o formato dd/mm/aaaa.")
            e_date.focus_set()
            return
        km = fmt.parse_number(e_km.get())
        if km is None or km <= 0:
            error_var.set("Odômetro inválido: informe os quilômetros totais (ex.: 45.120).")
            e_km.focus_set()
            return
        service_type = cmb_type.get().strip()
        if not service_type:
            error_var.set("Informe o tipo de serviço (ex.: Troca de óleo).")
            cmb_type.focus_set()
            return
        cost_text = e_cost.get().strip()
        cost = 0.0
        if cost_text:
            cost = fmt.parse_number(cost_text)
            if cost is None or cost < 0:
                error_var.set("Custo inválido: use um valor em reais (ex.: 250,00).")
                e_cost.focus_set()
                return
        next_km = None
        if e_next_km.get().strip():
            value = fmt.parse_number(e_next_km.get())
            if value is None or value <= 0:
                error_var.set("Intervalo inválido: informe a quilometragem entre revisões.")
                e_next_km.focus_set()
                return
            next_km = value
        next_date = None
        if e_next_date.get().strip():
            parsed = fmt.parse_date(e_next_date.get())
            if parsed is None:
                error_var.set("Data da próxima manutenção inválida (dd/mm/aaaa).")
                e_next_date.focus_set()
                return
            next_date = parsed.isoformat()

        updated = Maintenance(
            id=record.id if record is not None else new_id(),
            vehicle_id=vehicle_id,
            date=date.isoformat(),
            odometer=km,
            type=service_type,
            details=e_details.get().strip(),
            cost=round(cost, 2),
            shop=e_shop.get().strip(),
            notes=e_notes.get("1.0", "end").strip(),
            next_km=round(next_km, 1) if next_km else None,
            next_date=next_date,
        )
        dlg.accept(updated)

    buttons = ttk.Frame(body)
    buttons.grid(row=8, column=0, columnspan=4, sticky="e", pady=(10, 0))
    ttk.Button(buttons, text="Salvar", style="Accent.TButton", command=save).pack(
        side="left", padx=(0, 8)
    )
    ttk.Button(buttons, text="Cancelar", command=dlg.cancel).pack(side="left")

    for entry in (e_date, e_km, cmb_type, e_cost, e_shop, e_next_km, e_next_date,
                  e_details):
        entry.bind("<Return>", lambda _e: save())
    dlg.bind("<Escape>", lambda _e: dlg.cancel())

    return dlg.open()


def vehicle_dialog(parent, vehicle: Vehicle | None = None) -> Vehicle | None:
    """Formulário de veículo. Retorna o veículo ou None (cancelado)."""
    editing = vehicle is not None
    dlg = _Dialog(parent, "Editar veículo" if editing else "Novo veículo")
    body = dlg.body
    body.columnconfigure(0, weight=1)
    body.columnconfigure(1, weight=1)

    e_name = _add_entry(body, 0, 0, "Nome / apelido *", width=24)
    e_plate = _add_entry(body, 0, 1, "Placa", width=14)
    e_year = _add_entry(body, 1, 0, "Ano", width=10)

    ttk.Label(body, text="Combustível").grid(row=2, column=1, sticky="w", padx=(0, 18),
                                             pady=(6, 2))
    cmb_fuel = ttk.Combobox(body, values=FUELS, state="readonly", width=16)
    cmb_fuel.grid(row=3, column=1, sticky="we", padx=(0, 18), pady=(0, 2))

    e_km = _add_entry(body, 2, 0, "Km inicial (odômetro)", width=14)

    ttk.Label(body, text="Observações").grid(row=4, column=0, columnspan=2, sticky="w",
                                             pady=(6, 2))
    e_notes = tk.Text(body, width=46, height=3, wrap="word")
    e_notes.grid(row=5, column=0, columnspan=2, sticky="we", pady=(0, 4))

    if editing:
        e_name.insert(0, vehicle.name)  # type: ignore[union-attr]
        e_plate.insert(0, vehicle.plate)  # type: ignore[union-attr]
        if vehicle.year:  # type: ignore[union-attr]
            e_year.insert(0, str(vehicle.year))  # type: ignore[union-attr]
        e_km.insert(0, fmt.fmt_number(vehicle.initial_km, 1))  # type: ignore[union-attr]
        e_notes.insert("1.0", vehicle.notes)  # type: ignore[union-attr]
        cmb_fuel.set(vehicle.fuel if vehicle.fuel in FUELS else FUELS[0])  # type: ignore[union-attr]
    else:
        cmb_fuel.set("Gasolina")

    error_var = tk.StringVar(value="")
    ttk.Label(body, textvariable=error_var, foreground="#dc2626").grid(
        row=6, column=0, columnspan=2, sticky="w", pady=(2, 2)
    )

    def save():
        name = e_name.get().strip()
        if not name:
            error_var.set("Informe um nome para o veículo (ex.: 'Gol 2019', 'Carro da firma').")
            e_name.focus_set()
            return
        year_text = e_year.get().strip()
        year = None
        if year_text:
            if not year_text.isdigit() or len(year_text) != 4:
                error_var.set("Ano inválido: use 4 dígitos (ex.: 2019) ou deixe em branco.")
                e_year.focus_set()
                return
            year = int(year_text)
        initial_km = fmt.parse_number(e_km.get()) or 0.0
        if initial_km < 0:
            initial_km = 0.0

        record = Vehicle(
            id=vehicle.id if vehicle is not None else new_id(),
            name=name,
            plate=e_plate.get().strip(),
            year=year,
            fuel=cmb_fuel.get() or "Gasolina",
            initial_km=round(initial_km, 1),
            notes=e_notes.get("1.0", "end").strip(),
        )
        dlg.accept(record)

    buttons = ttk.Frame(body)
    buttons.grid(row=7, column=0, columnspan=2, sticky="e", pady=(12, 0))
    ttk.Button(buttons, text="Salvar", style="Accent.TButton", command=save).pack(
        side="left", padx=(0, 8)
    )
    ttk.Button(buttons, text="Cancelar", command=dlg.cancel).pack(side="left")

    for entry in (e_name, e_plate, e_year, e_km):
        entry.bind("<Return>", lambda _e: save())
    dlg.bind("<Escape>", lambda _e: dlg.cancel())

    return dlg.open()
