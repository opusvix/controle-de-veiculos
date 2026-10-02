"""Aba 'Veículos': cadastro, edição e seleção do veículo ativo."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .. import format as fmt
from ..models import FUELS, Vehicle, new_id
from .dialogs import vehicle_dialog

COLUMNS = (
    ("name", "Nome", 170, "w"),
    ("plate", "Placa", 100, "center"),
    ("year", "Ano", 70, "center"),
    ("fuel", "Combustível", 110, "w"),
    ("initial_km", "Km inicial", 110, "e"),
    ("count", "Abastecimentos", 130, "e"),
    ("active", "Ativo", 70, "center"),
)


class VehiclesTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=14)
        self.app = app
        self._editing_id: str | None = None
        self._build_form()
        self._build_list()
        self.refresh()

    # ------------------------------------------------------------------ form
    def _build_form(self):
        form = ttk.LabelFrame(self, text=" Cadastrar veículo ", padding=12)
        form.pack(fill="x")
        for col in range(5):
            form.columnconfigure(col, weight=1, uniform="v")

        def entry(row, col, label, width=16):
            ttk.Label(form, text=label).grid(row=row, column=col, sticky="w",
                                             padx=(0, 14), pady=(0, 2))
            box = ttk.Entry(form, width=width)
            box.grid(row=row + 1, column=col, sticky="we", padx=(0, 14), pady=(0, 4))
            return box

        self.e_name = entry(0, 0, "Nome / apelido *", 22)
        self.e_plate = entry(0, 1, "Placa", 14)
        self.e_year = entry(0, 2, "Ano", 8)
        self.e_km = entry(0, 3, "Km inicial (odômetro)", 14)

        ttk.Label(form, text="Combustível").grid(row=0, column=4, sticky="w",
                                                 padx=(0, 4), pady=(0, 2))
        self.cmb_fuel = ttk.Combobox(form, values=FUELS, state="readonly", width=14)
        self.cmb_fuel.grid(row=1, column=4, sticky="we", padx=(0, 4), pady=(0, 4))
        self.cmb_fuel.set("Gasolina")

        ttk.Label(form, text="Observações").grid(row=2, column=0, sticky="w", pady=(8, 2))
        self.e_notes = ttk.Entry(form)
        self.e_notes.grid(row=3, column=0, columnspan=4, sticky="we", pady=(0, 2))

        btns = ttk.Frame(form)
        btns.grid(row=3, column=4, sticky="e", padx=(8, 0))
        self.btn_save = ttk.Button(btns, text="Adicionar veículo",
                                   style="Accent.TButton", command=self.save_vehicle)
        self.btn_save.pack(side="left", padx=(0, 8))
        self.btn_cancel = ttk.Button(btns, text="Cancelar edição",
                                     command=self.reset_form)
        self.btn_cancel.pack(side="left")

        self.error_var = tk.StringVar(value="")
        ttk.Label(form, textvariable=self.error_var, foreground="#dc2626").grid(
            row=4, column=0, columnspan=5, sticky="w", pady=(6, 0)
        )

        for box in (self.e_name, self.e_plate, self.e_year, self.e_km, self.e_notes):
            box.bind("<Return>", lambda _e: self.save_vehicle())

    # ------------------------------------------------------------------ list
    def _build_list(self):
        box = ttk.LabelFrame(self, text=" Veículos cadastrados ", padding=10)
        box.pack(fill="both", expand=True, pady=(12, 0))

        self.tree = ttk.Treeview(box, columns=[c[0] for c in COLUMNS], show="headings",
                                 selectmode="browse")
        for key, title, width, anchor in COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor=anchor)
        vsb = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", lambda _e: self.edit_selected())

        foot = ttk.Frame(box)
        foot.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(foot, text="Usar este veículo",
                   command=self.set_active_selected).pack(side="left")
        ttk.Button(foot, text="Editar", command=self.edit_selected).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(foot, text="Excluir", style="Danger.TButton",
                   command=self.delete_selected).pack(side="left", padx=(8, 0))
        ttk.Label(
            foot,
            text="O 'ativo' é usado no lançamento e nas estatísticas.",
            foreground="#5b6472",
        ).pack(side="right")

    # -------------------------------------------------------------- actions
    def save_vehicle(self):
        self.error_var.set("")
        name = self.e_name.get().strip()
        if not name:
            self.error_var.set("Informe um nome (ex.: 'Gol 2019', 'Carro da firma').")
            self.e_name.focus_set()
            return
        year_text = self.e_year.get().strip()
        year = None
        if year_text:
            if not year_text.isdigit() or len(year_text) != 4:
                self.error_var.set("Ano inválido: use 4 dígitos (ex.: 2019) ou deixe em branco.")
                self.e_year.focus_set()
                return
            year = int(year_text)
        initial_km = fmt.parse_number(self.e_km.get()) or 0.0

        if self._editing_id:
            vehicle = self.app.doc.get_vehicle(self._editing_id)
            if vehicle is None:
                self.reset_form()
                return
            vehicle.name = name
            vehicle.plate = self.e_plate.get().strip()
            vehicle.year = year
            vehicle.fuel = self.cmb_fuel.get() or "Gasolina"
            vehicle.initial_km = round(max(initial_km, 0.0), 1)
            vehicle.notes = self.e_notes.get().strip()
        else:
            vehicle = Vehicle(
                id=new_id(),
                name=name,
                plate=self.e_plate.get().strip(),
                year=year,
                fuel=self.cmb_fuel.get() or "Gasolina",
                initial_km=round(max(initial_km, 0.0), 1),
                notes=self.e_notes.get().strip(),
            )
            self.app.doc.vehicles.append(vehicle)
            if self.app.active_vehicle_id is None:
                self.app.set_active_vehicle(vehicle.id)

        self.reset_form()
        self.app.changed()

    def edit_selected(self):
        vehicle_id = self._selected_id()
        if not vehicle_id:
            return
        vehicle = self.app.doc.get_vehicle(vehicle_id)
        if vehicle is None:
            return
        updated = vehicle_dialog(self.app, vehicle)
        if updated is None:
            return
        index = self.app.doc.vehicles.index(vehicle)
        self.app.doc.vehicles[index] = updated
        self.app.changed()

    def set_active_selected(self):
        vehicle_id = self._selected_id()
        if vehicle_id:
            self.app.set_active_vehicle(vehicle_id)

    def delete_selected(self):
        vehicle_id = self._selected_id()
        vehicle = self.app.doc.get_vehicle(vehicle_id)
        if vehicle is None:
            return
        refs = self.app.doc.vehicle_refuels(vehicle.id)
        detail = (
            f"\n\nO veículo tem {len(refs)} abastecimento(s), que também serão excluídos."
            if refs
            else ""
        )
        if not messagebox.askyesno("Excluir veículo",
                                   f"Excluir '{vehicle.name}' e todo o histórico dele?{detail}",
                                   parent=self.app):
            return
        self.app.doc.vehicles.remove(vehicle)
        self.app.doc.refuels = [r for r in self.app.doc.refuels if r.vehicle_id != vehicle.id]
        if self.app.active_vehicle_id == vehicle.id:
            self.app.active_vehicle_id = (
                self.app.doc.vehicles[0].id if self.app.doc.vehicles else None
            )
        self.app.changed()

    def reset_form(self):
        self._editing_id = None
        for box in (self.e_name, self.e_plate, self.e_year, self.e_km, self.e_notes):
            box.delete(0, "end")
        self.cmb_fuel.set("Gasolina")
        self.btn_save.configure(text="Adicionar veículo")
        self.btn_cancel.state(["disabled"])
        self.error_var.set("")

    def _selected_id(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    # -------------------------------------------------------------- refresh
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for vehicle in self.app.doc.vehicles:
            count = len(self.app.doc.vehicle_refuels(vehicle.id))
            active = vehicle.id == self.app.active_vehicle_id
            values = (
                vehicle.name,
                vehicle.plate,
                vehicle.year or "-",
                vehicle.fuel,
                fmt.fmt_number(vehicle.initial_km, 1),
                count,
                "sim" if active else "",
            )
            tags = ("active",) if active else ()
            self.tree.insert("", "end", iid=vehicle.id, values=values, tags=tags)
        self.tree.tag_configure("active", background="#e8f0fe")

        if self._editing_id and self.app.doc.get_vehicle(self._editing_id) is None:
            self.reset_form()
