"""Aba 'Abastecimentos': formulário de lançamento + histórico navegável."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .. import calcs, format as fmt
from ..models import Refuel, new_id
from .dialogs import refuel_dialog

COLUMNS = (
    ("date", "Data", 90, "center"),
    ("odometer", "Odômetro (km)", 105, "e"),
    ("distance", "Dist. (km)", 90, "e"),
    ("liters", "Litros", 75, "e"),
    ("price", "R$/L", 75, "e"),
    ("total", "Total", 95, "e"),
    ("kmpl", "km/L", 85, "e"),
    ("cpk", "R$/km", 85, "e"),
    ("station", "Posto", 140, "w"),
    ("full", "Tanque", 65, "center"),
)


class RefuelsTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=14)
        self.app = app
        self._auto_total = True
        self._build_form()
        self._build_history()
        self.refresh()

    # ------------------------------------------------------------------ form
    def _build_form(self):
        form = ttk.LabelFrame(self, text=" Registrar abastecimento ", padding=12)
        form.pack(fill="x")

        for col in range(8):
            form.columnconfigure(col, weight=1, uniform="f")

        def entry(row, col, label, width=12):
            ttk.Label(form, text=label).grid(row=row, column=col, sticky="w",
                                             padx=(0, 14), pady=(0, 2))
            box = ttk.Entry(form, width=width)
            box.grid(row=row + 1, column=col, sticky="we", padx=(0, 14), pady=(0, 4))
            return box

        self.e_date = entry(0, 0, "Data (dd/mm/aaaa)", 14)
        self.e_km = entry(0, 1, "Odômetro (km)", 13)
        self.e_liters = entry(0, 2, "Litros", 10)
        self.e_price = entry(0, 3, "Preço/L (R$)", 11)
        self.e_total = entry(0, 4, "Total (R$)", 12)
        self.e_station = entry(0, 5, "Posto", 16)

        ttk.Label(form, text="Tanque cheio").grid(row=0, column=6, sticky="w",
                                                  padx=(0, 14), pady=(0, 2))
        self.v_full = tk.BooleanVar(value=True)
        ttk.Checkbutton(form, variable=self.v_full).grid(row=1, column=6, sticky="w",
                                                         pady=(0, 4))

        btn_box = ttk.Frame(form)
        btn_box.grid(row=0, column=7, rowspan=2, sticky="nse", padx=(6, 0))
        self.btn_add = ttk.Button(btn_box, text="Adicionar", style="Accent.TButton",
                                  command=self.add_refuel)
        self.btn_add.pack(fill="x", pady=(0, 4))
        ttk.Button(btn_box, text="Limpar", command=self.clear_form).pack(fill="x")

        ttk.Label(form, text="Observações").grid(row=2, column=0, columnspan=2, sticky="w",
                                                 pady=(8, 2))
        self.e_notes = ttk.Entry(form)
        self.e_notes.grid(row=3, column=0, columnspan=6, sticky="we", pady=(0, 2))

        self.hint = ttk.Label(form, text="", foreground="#5b6472")
        self.hint.grid(row=4, column=0, columnspan=8, sticky="w", pady=(6, 0))

        for box in (self.e_date, self.e_km, self.e_liters, self.e_price,
                    self.e_total, self.e_station, self.e_notes):
            box.bind("<Return>", lambda _e: self.add_refuel())
        self.e_liters.bind("<KeyRelease>", self._recalc_total)
        self.e_price.bind("<KeyRelease>", self._recalc_total)
        self.e_total.bind("<KeyRelease>", lambda _e: setattr(self, "_auto_total", False))

    def _recalc_total(self, _event=None):
        if not self._auto_total:
            return
        liters = fmt.parse_number(self.e_liters.get())
        price = fmt.parse_number(self.e_price.get())
        if liters and price and liters > 0 and price > 0:
            self.e_total.delete(0, "end")
            self.e_total.insert(0, fmt.fmt_number(round(liters * price, 2), 2))

    # -------------------------------------------------------------- history
    def _build_history(self):
        box = ttk.LabelFrame(self, text=" Histórico ", padding=10)
        box.pack(fill="both", expand=True, pady=(12, 0))

        self.tree = ttk.Treeview(box, columns=[c[0] for c in COLUMNS], show="headings",
                                 selectmode="browse")
        for key, title, width, anchor in COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor=anchor, stretch=(key in ("station",)))
        vsb = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(box, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)

        self.tree.tag_configure("odd", background="#f7f9fc")
        self.tree.tag_configure("approx", foreground="#8a6d1f")

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Editar registro", command=self.edit_selected)
        menu.add_command(label="Excluir registro", command=self.delete_selected)
        menu.add_separator()
        menu.add_command(label="Copiar valores", command=self.copy_selected)
        self.menu = menu
        self.tree.bind("<Button-3>", self._open_menu)
        self.tree.bind("<Double-1>", lambda _e: self.edit_selected())
        self.tree.bind("<Delete>", lambda _e: self.delete_selected())

        foot = ttk.Frame(box)
        foot.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(foot, text="Editar", command=self.edit_selected).pack(side="left")
        ttk.Button(foot, text="Excluir", style="Danger.TButton",
                   command=self.delete_selected).pack(side="left", padx=(8, 0))
        ttk.Button(foot, text="Recalcular consumo", command=self.recalculate_hint).pack(
            side="left", padx=(8, 0)
        )
        ttk.Label(
            foot,
            text="km/L com '~' = cálculo aproximado (marque 'Tanque cheio' para precisão). "
                 "Botão direito no registro para mais opções.",
            foreground="#5b6472",
        ).pack(side="right")

    def _open_menu(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.menu.tk_popup(event.x_root, event.y_root)

    def _selected_id(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    # -------------------------------------------------------------- actions
    def add_refuel(self):
        vehicle = self.app.current_vehicle()
        if vehicle is None:
            messagebox.showinfo(
                "Sem veículo",
                "Cadastre um veículo na aba 'Veículos' antes de registrar abastecimentos.",
                parent=self.app,
            )
            return

        date = fmt.parse_date(self.e_date.get())
        if date is None:
            messagebox.showerror("Data inválida", "Use o formato dd/mm/aaaa.",
                                 parent=self.app)
            self.e_date.focus_set()
            return
        km = fmt.parse_number(self.e_km.get())
        if km is None or km <= 0:
            messagebox.showerror("Odômetro inválido",
                                 "Informe os quilômetros totais do veículo (ex.: 45120).",
                                 parent=self.app)
            self.e_km.focus_set()
            return
        liters = fmt.parse_number(self.e_liters.get())
        if liters is None or liters <= 0:
            messagebox.showerror("Litros inválidos",
                                 "Informe a quantidade de litros abastecidos.",
                                 parent=self.app)
            self.e_liters.focus_set()
            return
        price = fmt.parse_number(self.e_price.get())
        if price is None or price <= 0:
            messagebox.showerror("Preço inválido",
                                 "Informe o preço por litro (ex.: 5,79).",
                                 parent=self.app)
            self.e_price.focus_set()
            return
        total = fmt.parse_number(self.e_total.get())
        if total is None or total <= 0:
            total = round(liters * price, 2)

        existing = self.app.doc.vehicle_refuels(vehicle.id)
        if existing:
            max_km = max(r.odometer for r in existing)
            if km <= max_km:
                messagebox.showerror(
                    "Odômetro menor que o anterior",
                    f"O último registro é de {fmt.fmt_number(max_km, 1)} km.\n"
                    "A quilometragem só pode crescer.",
                    parent=self.app,
                )
                self.e_km.focus_set()
                return

        record = Refuel(
            id=new_id(),
            vehicle_id=vehicle.id,
            date=date.isoformat(),
            odometer=km,
            liters=liters,
            price=price,
            total=round(total, 2),
            full_tank=bool(self.v_full.get()),
            station=self.e_station.get().strip(),
            notes=self.e_notes.get().strip(),
        )
        self.app.doc.refuels.append(record)
        last_km = km
        self.clear_form(keep_station=True, keep_price=True, next_km=last_km)
        self.app.changed()
        self.e_km.focus_set()

    def edit_selected(self):
        ref_id = self._selected_id()
        if not ref_id:
            return
        record = self.app.doc.get_refuel(ref_id)
        if not record:
            return
        updated = refuel_dialog(self.app, self.app.doc, record.vehicle_id, record)
        if updated is None:
            return
        index = self.app.doc.refuels.index(record)
        self.app.doc.refuels[index] = updated
        self.app.changed()

    def delete_selected(self):
        ref_id = self._selected_id()
        if not ref_id:
            return
        record = self.app.doc.get_refuel(ref_id)
        if not record:
            return
        ok = messagebox.askyesno(
            "Excluir registro",
            f"Excluir o abastecimento de {fmt.fmt_date(record.date)} "
            f"({fmt.fmt_number(record.liters, 2)} L / {fmt.fmt_brl(record.total)})?",
            parent=self.app,
        )
        if not ok:
            return
        self.app.doc.refuels.remove(record)
        self.app.changed()

    def copy_selected(self):
        ref_id = self._selected_id()
        record = self.app.doc.get_refuel(ref_id) if ref_id else None
        if not record:
            return
        line = (
            f"{fmt.fmt_date(record.date)} | {fmt.fmt_number(record.odometer, 1)} km | "
            f"{fmt.fmt_number(record.liters, 2)} L | {fmt.fmt_brl(record.price, 3)}/L | "
            f"{fmt.fmt_brl(record.total)}"
        )
        self.app.clipboard_clear()
        self.app.clipboard_append(line)

    def recalculate_hint(self):
        messagebox.showinfo(
            "Como o consumo é calculado",
            "km/L = distância desde o último tanque cheio ÷ litros abastecidos nesse trecho.\n\n"
            "Para valores exatos, marque 'Tanque cheio' em cada abastecimento que "
            "encher o tanque. Sem isso, o cálculo sai aproximado ('~').",
            parent=self.app,
        )

    def clear_form(self, keep_station=False, keep_price=False, next_km=None):
        station = self.e_station.get() if keep_station else ""
        price = self.e_price.get() if keep_price else ""
        self.e_date.delete(0, "end")
        self.e_date.insert(0, fmt.today_input())
        self.e_km.delete(0, "end")
        if next_km is not None:
            self.e_km.insert(0, fmt.fmt_number(next_km, 1))
        self.e_liters.delete(0, "end")
        self.e_price.delete(0, "end")
        if price:
            self.e_price.insert(0, price)
        self.e_total.delete(0, "end")
        self.e_station.delete(0, "end")
        if station:
            self.e_station.insert(0, station)
        self.e_notes.delete(0, "end")
        self.v_full.set(True)
        self._auto_total = True

    # -------------------------------------------------------------- refresh
    def refresh(self):
        vehicle = self.app.current_vehicle()
        state = "normal" if vehicle else "disabled"
        for box in (self.e_date, self.e_km, self.e_liters, self.e_price, self.e_total,
                    self.e_station, self.e_notes):
            box.configure(state=state)
        self.btn_add.configure(state=state)

        if vehicle is None:
            self.hint.configure(
                text="Nenhum veículo cadastrado: use a aba 'Veículos' para criar o primeiro."
            )
        else:
            refs = calcs.ordered_refuels(self.app.doc, vehicle.id)
            if refs:
                segments = calcs.build_segments(refs)
                last = refs[-1]
                seg = segments.get(last.id)
                consumption = (
                    f"{fmt.fmt_number(seg.km_per_l, 1)} km/L"
                    if seg and seg.km_per_l
                    else "sem base de cálculo"
                )
                self.hint.configure(
                    text=(
                        f"Último registro: {fmt.fmt_number(last.odometer, 1)} km em "
                        f"{fmt.fmt_date(last.date)} | consumo do último trecho: {consumption} | "
                        f"total: {len(refs)} abastecimentos"
                    )
                )
            else:
                self.hint.configure(
                    text=(
                        f"Primeiro registro de {vehicle.name}. "
                        f"Km inicial informado: {fmt.fmt_number(vehicle.initial_km, 1)} km."
                    )
                )
        self._reload_tree()

    def _reload_tree(self):
        self.tree.delete(*self.tree.get_children())
        vehicle = self.app.current_vehicle()
        if vehicle is None:
            return
        refs = calcs.ordered_refuels(self.app.doc, vehicle.id)
        segments = calcs.build_segments(refs)
        for index, record in enumerate(reversed(refs)):
            seg = segments.get(record.id)
            distance = f"{fmt.fmt_number(seg.distance, 1)}" if seg and seg.distance else "-"
            if seg and seg.km_per_l:
                kmpl = ("~" if seg.approximate else "") + fmt.fmt_number(seg.km_per_l, 2)
            else:
                kmpl = "-"
            cpk = fmt.fmt_brl(seg.cost_per_km) if seg and seg.cost_per_km else "-"
            values = (
                fmt.fmt_date(record.date),
                fmt.fmt_number(record.odometer, 1),
                distance,
                fmt.fmt_number(record.liters, 2),
                fmt.fmt_number(record.price, 3),
                fmt.fmt_brl(record.total),
                kmpl,
                cpk,
                record.station,
                "sim" if record.full_tank else "",
            )
            tags = []
            if index % 2:
                tags.append("odd")
            if kmpl.startswith("~"):
                tags.append("approx")
            self.tree.insert("", "end", iid=record.id, values=values, tags=tags)
