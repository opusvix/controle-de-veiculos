"""Aba 'Manutenções': serviços feitos no veículo + avisos da próxima revisão."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .. import calcs, format as fmt
from ..models import MAINT_TYPES, Maintenance, new_id
from .dialogs import maintenance_dialog

COLUMNS = (
    ("date", "Data", 90, "center"),
    ("odometer", "Odômetro (km)", 105, "e"),
    ("type", "Tipo", 135, "w"),
    ("details", "Serviços", 200, "w"),
    ("cost", "Custo", 95, "e"),
    ("shop", "Oficina", 140, "w"),
    ("next", "Próxima", 150, "w"),
)


class MaintenanceTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=14)
        self.app = app
        self._build_form()
        self._build_history()
        self.refresh()

    # ------------------------------------------------------------------ form
    def _build_form(self):
        form = ttk.LabelFrame(self, text=" Registrar manutenção ", padding=12)
        form.pack(fill="x")

        for col in range(8):
            form.columnconfigure(col, weight=1, uniform="f")

        def entry(row, col, label, width=12, span=1):
            ttk.Label(form, text=label).grid(row=row, column=col, columnspan=span,
                                             sticky="w", padx=(0, 14), pady=(0, 2))
            box = ttk.Entry(form, width=width)
            box.grid(row=row + 1, column=col, columnspan=span, sticky="we",
                     padx=(0, 14), pady=(0, 4))
            return box

        self.e_date = entry(0, 0, "Data (dd/mm/aaaa)", 14)
        self.e_km = entry(0, 1, "Odômetro (km)", 13)

        ttk.Label(form, text="Tipo de serviço").grid(row=0, column=2, sticky="w",
                                                     padx=(0, 14), pady=(0, 2))
        self.cmb_type = ttk.Combobox(form, values=MAINT_TYPES, width=20)
        self.cmb_type.grid(row=1, column=2, sticky="we", padx=(0, 14), pady=(0, 4))

        self.e_cost = entry(0, 3, "Custo (R$)", 11)
        self.e_shop = entry(0, 4, "Oficina / local", 16)
        self.e_next_km = entry(0, 5, "Repetir a cada (km)", 13)
        self.e_next_date = entry(0, 6, "Próxima em (data)", 14)

        btn_box = ttk.Frame(form)
        btn_box.grid(row=0, column=7, rowspan=2, sticky="nse", padx=(6, 0))
        self.btn_add = ttk.Button(btn_box, text="Adicionar", style="Accent.TButton",
                                  command=self.add_maintenance)
        self.btn_add.pack(fill="x", pady=(0, 4))
        ttk.Button(btn_box, text="Limpar", command=self.clear_form).pack(fill="x")

        ttk.Label(form, text="Serviços executados").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(8, 2))
        self.e_details = ttk.Entry(form)
        self.e_details.grid(row=3, column=0, columnspan=3, sticky="we",
                            padx=(0, 14), pady=(0, 2))

        ttk.Label(form, text="Observações").grid(
            row=2, column=4, columnspan=3, sticky="w", pady=(8, 2))
        self.e_notes = ttk.Entry(form)
        self.e_notes.grid(row=3, column=4, columnspan=3, sticky="we", pady=(0, 2))

        self.hint = ttk.Label(form, text="", foreground="#5b6472")
        self.hint.grid(row=4, column=0, columnspan=8, sticky="w", pady=(6, 0))

        for box in (self.e_date, self.e_km, self.cmb_type, self.e_cost, self.e_shop,
                    self.e_next_km, self.e_next_date, self.e_details, self.e_notes):
            box.bind("<Return>", lambda _e: self.add_maintenance())

    # -------------------------------------------------------------- histórico
    def _build_history(self):
        box = ttk.LabelFrame(self, text=" Histórico de manutenções ", padding=10)
        box.pack(fill="both", expand=True, pady=(12, 0))

        self.tree = ttk.Treeview(box, columns=[c[0] for c in COLUMNS], show="headings",
                                 selectmode="browse")
        for key, title, width, anchor in COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor=anchor,
                             stretch=(key in ("details", "shop", "next")))
        vsb = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(box, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)

        self.tree.tag_configure("odd", background="#f7f9fc")
        self.tree.tag_configure("late", foreground="#b91c1c")
        self.tree.tag_configure("soon", foreground="#8a6d1f")

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
        self.alert = ttk.Label(foot, text="", foreground="#b91c1c")
        self.alert.pack(side="right")

    def _open_menu(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.menu.tk_popup(event.x_root, event.y_root)

    def _selected_id(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    # --------------------------------------------------------------- ações
    def add_maintenance(self):
        vehicle = self.app.current_vehicle()
        if vehicle is None:
            messagebox.showinfo(
                "Sem veículo",
                "Cadastre um veículo na aba 'Veículos' antes de registrar manutenções.",
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
                                 "Informe os quilômetros do veículo (ex.: 45120).",
                                 parent=self.app)
            self.e_km.focus_set()
            return
        service_type = self.cmb_type.get().strip()
        if not service_type:
            messagebox.showerror("Tipo obrigatório",
                                 "Escolha ou digite o tipo de serviço (ex.: Troca de óleo).",
                                 parent=self.app)
            self.cmb_type.focus_set()
            return
        cost = 0.0
        if self.e_cost.get().strip():
            cost = fmt.parse_number(self.e_cost.get())
            if cost is None or cost < 0:
                messagebox.showerror("Custo inválido",
                                     "Use um valor em reais (ex.: 250,00) ou deixe em branco.",
                                     parent=self.app)
                self.e_cost.focus_set()
                return
        next_km = None
        if self.e_next_km.get().strip():
            value = fmt.parse_number(self.e_next_km.get())
            if value is None or value <= 0:
                messagebox.showerror("Intervalo inválido",
                                     "Informe a quilometragem entre revisões (ex.: 5000).",
                                     parent=self.app)
                self.e_next_km.focus_set()
                return
            next_km = value
        next_date = None
        if self.e_next_date.get().strip():
            parsed = fmt.parse_date(self.e_next_date.get())
            if parsed is None:
                messagebox.showerror("Data inválida",
                                     "A próxima manutenção usa o formato dd/mm/aaaa.",
                                     parent=self.app)
                self.e_next_date.focus_set()
                return
            next_date = parsed.isoformat()

        record = Maintenance(
            id=new_id(),
            vehicle_id=vehicle.id,
            date=date.isoformat(),
            odometer=km,
            type=service_type,
            details=self.e_details.get().strip(),
            cost=round(cost, 2),
            shop=self.e_shop.get().strip(),
            notes=self.e_notes.get().strip(),
            next_km=round(next_km, 1) if next_km else None,
            next_date=next_date,
        )
        self.app.doc.maintenances.append(record)
        self.clear_form(next_km=km)
        self.app.changed()
        self.e_km.focus_set()

    def edit_selected(self):
        rec_id = self._selected_id()
        if not rec_id:
            return
        record = self.app.doc.get_maintenance(rec_id)
        if not record:
            return
        updated = maintenance_dialog(self.app, self.app.doc, record.vehicle_id, record)
        if updated is None:
            return
        index = self.app.doc.maintenances.index(record)
        self.app.doc.maintenances[index] = updated
        self.app.changed()

    def delete_selected(self):
        rec_id = self._selected_id()
        if not rec_id:
            return
        record = self.app.doc.get_maintenance(rec_id)
        if not record:
            return
        ok = messagebox.askyesno(
            "Excluir registro",
            f"Excluir a manutenção '{record.type}' de {fmt.fmt_date(record.date)}?",
            parent=self.app,
        )
        if not ok:
            return
        self.app.doc.maintenances.remove(record)
        self.app.changed()

    def copy_selected(self):
        rec_id = self._selected_id()
        record = self.app.doc.get_maintenance(rec_id) if rec_id else None
        if not record:
            return
        line = (
            f"{fmt.fmt_date(record.date)} | {fmt.fmt_number(record.odometer, 1)} km | "
            f"{record.type} | {fmt.fmt_brl(record.cost)}"
        )
        self.app.clipboard_clear()
        self.app.clipboard_append(line)

    def clear_form(self, next_km=None):
        self.e_date.delete(0, "end")
        self.e_date.insert(0, fmt.today_input())
        self.e_km.delete(0, "end")
        if next_km is not None:
            self.e_km.insert(0, fmt.fmt_number(next_km, 1))
        self.cmb_type.set("")
        self.e_cost.delete(0, "end")
        self.e_shop.delete(0, "end")
        self.e_next_km.delete(0, "end")
        self.e_next_date.delete(0, "end")
        self.e_details.delete(0, "end")
        self.e_notes.delete(0, "end")

    # -------------------------------------------------------------- refresh
    def refresh(self):
        vehicle = self.app.current_vehicle()
        state = "normal" if vehicle else "disabled"
        for box in (self.e_date, self.e_km, self.cmb_type, self.e_cost, self.e_shop,
                    self.e_next_km, self.e_next_date, self.e_details, self.e_notes):
            box.configure(state=state)
        self.btn_add.configure(state=state)

        reminders = calcs.reminders(self.app.doc, vehicle.id) if vehicle else []
        late = [r for r in reminders if r.level == "atrasada"]
        soon = [r for r in reminders if r.level == "proxima"]

        if vehicle is None:
            self.hint.configure(
                text="Nenhum veículo cadastrado: use a aba 'Veículos' para criar o primeiro."
            )
        else:
            items = calcs.ordered_maintenances(self.app.doc, vehicle.id)
            parts = []
            if items:
                last = items[-1]
                parts.append(
                    f"Último serviço: {last.type} em {fmt.fmt_date(last.date)} "
                    f"({fmt.fmt_number(last.odometer, 1)} km)"
                )
            else:
                parts.append(
                    f"Nenhuma manutenção registrada para {vehicle.name} "
                    f"(km atual: {fmt.fmt_number(calcs.current_km(self.app.doc, vehicle.id), 1)})"
                )
            if late:
                parts.append(f"ATRASADA: {late[0].maintenance.type} — {late[0].label}")
            elif soon:
                parts.append(f"Próxima: {soon[0].maintenance.type} — {soon[0].label}")
            self.hint.configure(text=" | ".join(parts))

        if late:
            self.alert.configure(
                text=f"⚠ {len(late)} serviço(s) atrasado(s) e {len(soon)} próximo(s)",
                foreground="#b91c1c",
            )
        elif soon:
            self.alert.configure(
                text=f"⚠ {len(soon)} serviço(s) próximos", foreground="#8a6d1f"
            )
        else:
            self.alert.configure(text="", foreground="#5b6472")

        self._reload_tree(reminders)

    def _reload_tree(self, reminders):
        self.tree.delete(*self.tree.get_children())
        vehicle = self.app.current_vehicle()
        if vehicle is None:
            return
        by_id = {r.maintenance.id: r for r in reminders}
        items = calcs.ordered_maintenances(self.app.doc, vehicle.id)
        for index, record in enumerate(reversed(items)):
            reminder = by_id.get(record.id)
            if reminder:
                proxima = reminder.label
                if reminder.detail:
                    proxima += f" ({reminder.detail})"
            else:
                proxima = "—"
            values = (
                fmt.fmt_date(record.date),
                fmt.fmt_number(record.odometer, 1),
                record.type,
                record.details or record.notes,
                fmt.fmt_brl(record.cost) if record.cost else "-",
                record.shop,
                proxima,
            )
            tags = []
            if index % 2:
                tags.append("odd")
            if reminder and reminder.level == "atrasada":
                tags.append("late")
            elif reminder and reminder.level == "proxima":
                tags.append("soon")
            self.tree.insert("", "end", iid=record.id, values=values, tags=tags)
