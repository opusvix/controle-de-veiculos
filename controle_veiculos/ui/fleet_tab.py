"""Aba 'Frota': painel geral, documentos/vencimentos e motoristas."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .. import calcs, format as fmt
from . import dialogs

LEVEL_COLORS = {
    "atrasada": "#dc2626",
    "proxima": "#b45309",
    "ok": "#15803d",
}


class FleetTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=14)
        self.app = app
        self._build_cards()
        self._build_fleet()
        self._build_bottom()
        self.refresh()

    # ---------------------------------------------------------------- cards
    def _build_cards(self):
        wrap = ttk.Frame(self)
        wrap.pack(fill="x")
        for col in range(3):
            wrap.columnconfigure(col, weight=1, uniform="c")
        self.cards: dict[str, tk.Label] = {}
        specs = (
            ("vehicles", "Veículos na frota"),
            ("spent", "Gasto no mês (frota)"),
            ("alerts", "Alertas"),
        )
        for index, (key, caption) in enumerate(specs):
            card = tk.Frame(wrap, bg="white", highlightbackground="#dfe4ea",
                            highlightthickness=1)
            card.grid(row=0, column=index, sticky="nsew", padx=5, pady=5)
            tk.Label(card, text=caption, bg="white", fg="#6b7280",
                     font=("Segoe UI", 9)).pack(padx=12, pady=(9, 0))
            value = tk.Label(card, text="-", bg="white", fg="#111827",
                             font=("Segoe UI", 18, "bold"))
            value.pack(padx=12, pady=(2, 0))
            sub = tk.Label(card, text="", bg="white", fg="#6b7280",
                           font=("Segoe UI", 9))
            sub.pack(padx=12, pady=(0, 9))
            self.cards[key] = value
            self.cards[key + "_sub"] = sub

    # ---------------------------------------------------------------- frota
    def _build_fleet(self):
        box = ttk.LabelFrame(self, text=" Painel da frota (mês atual) ", padding=10)
        box.pack(fill="both", expand=True, pady=(12, 0))
        cols = (
            ("name", "Veículo", 180, "w"),
            ("km", "Km atual", 100, "e"),
            ("kmpl", "Consumo", 100, "e"),
            ("spent", "Gasto mês", 110, "e"),
            ("co2", "CO₂ mês (kg)", 110, "e"),
            ("alert", "Revisão mais urgente", 260, "w"),
        )
        self.fleet_tree = ttk.Treeview(box, columns=[c[0] for c in cols],
                                       show="headings", height=6)
        for key, title, width, anchor in cols:
            self.fleet_tree.heading(key, text=title)
            self.fleet_tree.column(key, width=width, anchor=anchor)
        self.fleet_tree.tag_configure("atrasada", foreground=LEVEL_COLORS["atrasada"])
        self.fleet_tree.tag_configure("proxima", foreground=LEVEL_COLORS["proxima"])
        vsb = ttk.Scrollbar(box, orient="vertical", command=self.fleet_tree.yview)
        self.fleet_tree.configure(yscrollcommand=vsb.set)
        self.fleet_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)

    # ------------------------------------------------ documentos + motoristas
    def _build_bottom(self):
        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True, pady=(12, 0))
        wrap.columnconfigure(0, weight=3, uniform="b")
        wrap.columnconfigure(1, weight=2, uniform="b")

        # -------- Documentos / vencimentos
        docbox = ttk.LabelFrame(wrap, text=" Documentos e vencimentos ", padding=10)
        docbox.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        cols = (
            ("type", "Documento", 150, "w"),
            ("vehicle", "Veículo", 150, "w"),
            ("due", "Vence em", 100, "center"),
            ("left", "Faltam", 90, "e"),
            ("cost", "Valor", 90, "e"),
        )
        self.doc_tree = ttk.Treeview(docbox, columns=[c[0] for c in cols],
                                     show="headings", height=6)
        for key, title, width, anchor in cols:
            self.doc_tree.heading(key, text=title)
            self.doc_tree.column(key, width=width, anchor=anchor)
        self.doc_tree.tag_configure("atrasada", foreground=LEVEL_COLORS["atrasada"])
        self.doc_tree.tag_configure("proxima", foreground=LEVEL_COLORS["proxima"])
        self.doc_tree.grid(row=0, column=0, columnspan=4, sticky="nsew")
        docbox.rowconfigure(0, weight=1)
        docbox.columnconfigure(0, weight=1)
        self._doc_ids: list[str] = []
        btns = ttk.Frame(docbox)
        btns.grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 0))
        ttk.Button(btns, text="+ Documento", style="Accent.TButton",
                   command=self.add_document).pack(side="left")
        ttk.Button(btns, text="Editar", command=self.edit_document).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Dar baixa", command=self.resolve_document).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Excluir", style="Danger.TButton",
                   command=self.delete_document).pack(side="left", padx=(8, 0))

        # -------- Motoristas
        drvbox = ttk.LabelFrame(wrap, text=" Motoristas ", padding=10)
        drvbox.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        cols = (
            ("name", "Nome", 160, "w"),
            ("license", "CNH", 110, "w"),
        )
        self.drv_tree = ttk.Treeview(drvbox, columns=[c[0] for c in cols],
                                     show="headings", height=6)
        for key, title, width, anchor in cols:
            self.drv_tree.heading(key, text=title)
            self.drv_tree.column(key, width=width, anchor=anchor)
        self.drv_tree.grid(row=0, column=0, columnspan=3, sticky="nsew")
        drvbox.rowconfigure(0, weight=1)
        drvbox.columnconfigure(0, weight=1)
        self._drv_ids: list[str] = []
        btns = ttk.Frame(drvbox)
        btns.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Button(btns, text="+ Motorista", style="Accent.TButton",
                   command=self.add_driver).pack(side="left")
        ttk.Button(btns, text="Editar", command=self.edit_driver).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Excluir", style="Danger.TButton",
                   command=self.delete_driver).pack(side="left", padx=(8, 0))

    # -------------------------------------------------------------- refresh
    def refresh(self):
        doc = self.app.doc
        summary = calcs.fleet_summary(doc)
        self.cards["vehicles"].configure(text=str(len(doc.vehicles)))
        self.cards["vehicles_sub"].configure(
            text=f"{len(doc.drivers)} motorista(s)")
        self.cards["spent"].configure(text=fmt.fmt_brl(summary.total_spent))
        self.cards["spent_sub"].configure(
            text=f"{fmt.fmt_number(summary.total_co2, 0)} kg CO₂ no mês")
        alerts = summary.alert_vehicles + calcs.doc_alert_count(doc)
        self.cards["alerts"].configure(text=str(alerts))
        self.cards["alerts_sub"].configure(
            text="revisões + documentos" if alerts else "tudo em dia")

        # painel da frota
        self.fleet_tree.delete(*self.fleet_tree.get_children())
        for c in summary.cards:
            if c.worst is not None:
                alerta = f"{c.worst.maintenance.type}: {c.worst.label}"
                tags = (c.worst.level,)
            else:
                alerta = "—"
                tags = ()
            self.fleet_tree.insert("", "end", tags=tags, values=(
                c.vehicle.name or c.vehicle.plate or "(sem nome)",
                fmt.fmt_number(c.km, 0) + " km",
                fmt.fmt_number(c.km_per_l, 2) + " km/L" if c.km_per_l else "-",
                fmt.fmt_brl(c.month_spent),
                fmt.fmt_number(c.month_co2, 0),
                alerta,
            ))

        # documentos
        self.doc_tree.delete(*self.doc_tree.get_children())
        self._doc_ids = []
        for rem in calcs.doc_reminders(doc):
            dc = rem.document
            if rem.remaining_days is None:
                faltam = "—"
            elif rem.remaining_days < 0:
                faltam = f"{abs(rem.remaining_days)}d atrás"
            else:
                faltam = f"{rem.remaining_days} dia(s)"
            tags = (rem.level,) if rem.level != "ok" else ()
            self.doc_tree.insert("", "end", tags=tags, values=(
                dc.get("type", ""),
                rem.vehicle_name,
                fmt.fmt_date(dc.get("due_date")) if dc.get("due_date") else "—",
                faltam,
                fmt.fmt_brl(dc.get("cost")) if dc.get("cost") else "-",
            ))
            self._doc_ids.append(dc.get("id", ""))

        # motoristas
        self.drv_tree.delete(*self.drv_tree.get_children())
        self._drv_ids = []
        for dr in doc.drivers:
            if not isinstance(dr, dict):
                continue
            self.drv_tree.insert("", "end", values=(
                dr.get("name", ""),
                dr.get("license", "") or "-",
            ))
            self._drv_ids.append(dr.get("id", ""))

    # ------------------------------------------------------------ documentos
    def _selected_doc(self) -> dict | None:
        sel = self.doc_tree.selection()
        if not sel:
            return None
        idx = self.doc_tree.index(sel[0])
        if not (0 <= idx < len(self._doc_ids)):
            return None
        did = self._doc_ids[idx]
        return next((d for d in self.app.doc.documents if d.get("id") == did), None)

    def add_document(self):
        if not self.app.doc.vehicles:
            messagebox.showinfo("Sem veículo",
                                "Cadastre um veículo antes de adicionar documentos.",
                                parent=self.app)
            return
        record = dialogs.document_dialog(self.app, self.app.doc)
        if record:
            self.app.doc.documents.append(record)
            self.app.changed()

    def edit_document(self):
        dc = self._selected_doc()
        if dc is None:
            messagebox.showinfo("Selecione", "Escolha um documento na lista.",
                                parent=self.app)
            return
        record = dialogs.document_dialog(self.app, self.app.doc, dc)
        if record:
            for i, x in enumerate(self.app.doc.documents):
                if x.get("id") == record["id"]:
                    self.app.doc.documents[i] = record
                    break
            self.app.changed()

    def resolve_document(self):
        dc = self._selected_doc()
        if dc is None:
            messagebox.showinfo("Selecione", "Escolha um documento na lista.",
                                parent=self.app)
            return
        dc["done"] = True
        self.app.changed()

    def delete_document(self):
        dc = self._selected_doc()
        if dc is None:
            messagebox.showinfo("Selecione", "Escolha um documento na lista.",
                                parent=self.app)
            return
        if messagebox.askyesno("Excluir documento",
                               f"Excluir o documento \"{dc.get('type', '')}\"?",
                               parent=self.app):
            self.app.doc.documents = [x for x in self.app.doc.documents
                                      if x.get("id") != dc.get("id")]
            self.app.changed()

    # ------------------------------------------------------------ motoristas
    def _selected_driver(self) -> dict | None:
        sel = self.drv_tree.selection()
        if not sel:
            return None
        idx = self.drv_tree.index(sel[0])
        if not (0 <= idx < len(self._drv_ids)):
            return None
        did = self._drv_ids[idx]
        return next((d for d in self.app.doc.drivers if d.get("id") == did), None)

    def add_driver(self):
        record = dialogs.driver_dialog(self.app)
        if record:
            self.app.doc.drivers.append(record)
            self.app.changed()

    def edit_driver(self):
        dr = self._selected_driver()
        if dr is None:
            messagebox.showinfo("Selecione", "Escolha um motorista na lista.",
                                parent=self.app)
            return
        record = dialogs.driver_dialog(self.app, dr)
        if record:
            for i, x in enumerate(self.app.doc.drivers):
                if x.get("id") == record["id"]:
                    self.app.doc.drivers[i] = record
                    break
            self.app.changed()

    def delete_driver(self):
        dr = self._selected_driver()
        if dr is None:
            messagebox.showinfo("Selecione", "Escolha um motorista na lista.",
                                parent=self.app)
            return
        if messagebox.askyesno("Excluir motorista",
                               f"Excluir o motorista \"{dr.get('name', '')}\"?\n\n"
                               "Os abastecimentos ligados a ele ficam sem motorista.",
                               parent=self.app):
            self.app.doc.drivers = [x for x in self.app.doc.drivers
                                    if x.get("id") != dr.get("id")]
            self.app.changed()
