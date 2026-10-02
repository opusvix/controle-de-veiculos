"""Aba 'Relatórios': filtros por período, resumo, gráfico e resumo mensal."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .. import calcs, format as fmt
from .chart import BarChart

MODES = (
    "Consumo (km/L)",
    "Custo por km (R$/km)",
    "Gasto mensal (R$)",
    "Manutenção por mês (R$)",
    "Km por mês",
)

MONTH_COLUMNS = (
    ("month", "Mês", 85, "center"),
    ("count", "Abast.", 70, "e"),
    ("km", "Km rodados", 105, "e"),
    ("liters", "Litros", 90, "e"),
    ("spent", "Combustível", 110, "e"),
    ("maint", "Manutenção", 110, "e"),
    ("total", "Total", 110, "e"),
    ("kmpl", "km/L", 80, "e"),
    ("cpk", "R$/km", 80, "e"),
)

CARD_SPECS = (
    ("count", "Abastecimentos"),
    ("maint_count", "Manutenções"),
    ("km", "Km rodados"),
    ("liters", "Litros abastecidos"),
    ("spent", "Gasto com combustível"),
    ("maint_spent", "Gasto com manutenção"),
    ("total_spent", "Total geral"),
    ("avg_price", "Preço médio do litro"),
    ("km_per_l", "Consumo médio"),
    ("cost_per_km", "Custo por km (combustível)"),
    ("cost_per_km_total", "Custo por km total"),
    ("avg_spent", "Média por abastecimento"),
)


class ReportsTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=14)
        self.app = app
        self.start_iso: str | None = None
        self.end_iso: str | None = None
        self.all_vehicles = tk.BooleanVar(value=False)
        self._build_filters()
        self._build_cards()
        self._build_chart()
        self._build_months()
        self.refresh()

    # -------------------------------------------------------------- filtros
    def _build_filters(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x")

        ttk.Label(bar, text="Período:").pack(side="left")
        ttk.Label(bar, text="de").pack(side="left", padx=(8, 4))
        self.e_start = ttk.Entry(bar, width=12)
        self.e_start.pack(side="left")
        ttk.Label(bar, text="até").pack(side="left", padx=(6, 4))
        self.e_end = ttk.Entry(bar, width=12)
        self.e_end.pack(side="left")

        ttk.Button(bar, text="Aplicar", command=self.apply_filters).pack(
            side="left", padx=(10, 6)
        )
        ttk.Button(bar, text="Limpar", command=self.clear_filters).pack(side="left")

        ttk.Checkbutton(
            bar, text="Todos os veículos", variable=self.all_vehicles,
            command=self.refresh,
        ).pack(side="left", padx=(16, 0))

        self.period_label = ttk.Label(bar, text="", foreground="#5b6472")
        self.period_label.pack(side="right")

    def apply_filters(self):
        start_text = self.e_start.get().strip()
        end_text = self.e_end.get().strip()
        start = end = None
        if start_text:
            start = fmt.parse_date(start_text)
            if start is None:
                messagebox.showerror("Data inválida",
                                     "Data inicial inválida. Use dd/mm/aaaa.",
                                     parent=self.app)
                return
        if end_text:
            end = fmt.parse_date(end_text)
            if end is None:
                messagebox.showerror("Data inválida",
                                     "Data final inválida. Use dd/mm/aaaa.",
                                     parent=self.app)
                return
        if start and end and start > end:
            messagebox.showerror("Período inválido",
                                 "A data inicial não pode ser posterior à final.",
                                 parent=self.app)
            return
        self.start_iso = start.isoformat() if start else None
        self.end_iso = end.isoformat() if end else None
        self.refresh()

    def clear_filters(self):
        self.e_start.delete(0, "end")
        self.e_end.delete(0, "end")
        self.start_iso = self.end_iso = None
        self.refresh()

    # ---------------------------------------------------------------- cards
    def _build_cards(self):
        wrap = ttk.Frame(self)
        wrap.pack(fill="x", pady=(12, 0))
        for col in range(4):
            wrap.columnconfigure(col, weight=1, uniform="c")
        self.cards: dict[str, tuple[tk.Label, tk.Label]] = {}
        for index, (key, caption) in enumerate(CARD_SPECS):
            row, col = divmod(index, 4)
            card = tk.Frame(wrap, bg="white", highlightbackground="#dfe4ea",
                            highlightthickness=1)
            card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            tk.Label(card, text=caption, bg="white", fg="#6b7280",
                     font=("Segoe UI", 9)).pack(padx=12, pady=(9, 0))
            value = tk.Label(card, text="-", bg="white", fg="#111827",
                             font=("Segoe UI", 18, "bold"))
            value.pack(padx=12, pady=(2, 0))
            sub = tk.Label(card, text="", bg="white", fg="#6b7280",
                           font=("Segoe UI", 9))
            sub.pack(padx=12, pady=(0, 9))
            self.cards[key] = (value, sub)

    # ---------------------------------------------------------------- chart
    def _build_chart(self):
        box = ttk.LabelFrame(self, text=" Gráfico ", padding=10)
        box.pack(fill="x", pady=(12, 0))
        head = ttk.Frame(box)
        head.pack(fill="x", pady=(0, 6))
        ttk.Label(head, text="Indicador:").pack(side="left")
        self.cmb_mode = ttk.Combobox(head, values=list(MODES), state="readonly", width=24)
        self.cmb_mode.set(MODES[0])
        self.cmb_mode.pack(side="left", padx=(8, 0))
        self.cmb_mode.bind("<<ComboboxSelected>>", lambda _e: self._draw_chart())
        self.chart_note = ttk.Label(head, text="", foreground="#5b6472")
        self.chart_note.pack(side="right")
        self.chart = BarChart(box, height=240)
        self.chart.pack(fill="x")

    # --------------------------------------------------------------- months
    def _build_months(self):
        box = ttk.LabelFrame(self, text=" Resumo mensal ", padding=10)
        box.pack(fill="both", expand=True, pady=(12, 0))
        self.tree = ttk.Treeview(box, columns=[c[0] for c in MONTH_COLUMNS],
                                 show="headings", height=7)
        for key, title, width, anchor in MONTH_COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor=anchor)
        vsb = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)

    # -------------------------------------------------------------- refresh
    def _vehicle_ids(self) -> list[str]:
        if self.all_vehicles.get():
            return [v.id for v in self.app.doc.vehicles]
        vehicle = self.app.current_vehicle()
        return [vehicle.id] if vehicle else []

    def refresh(self):
        view = calcs.report(self.app.doc, self._vehicle_ids(), self.start_iso, self.end_iso)
        stats = view.stats

        if self.start_iso or self.end_iso:
            left = fmt.fmt_date(self.start_iso) if self.start_iso else "início"
            right = fmt.fmt_date(self.end_iso) if self.end_iso else "hoje"
            self.period_label.configure(text=f"Período: {left} a {right}")
        else:
            self.period_label.configure(text="Período: todos os registros")

        if not self._vehicle_ids():
            for key, (value, sub) in self.cards.items():
                value.configure(text="-")
                sub.configure(text="sem veículo" if key == "count" else "")
            self.tree.delete(*self.tree.get_children())
            self.chart.set_data([], [], "")
            self.chart_note.configure(text="Cadastre um veículo para ver relatórios.")
            return

        data = {
            "count": (fmt.fmt_number(stats.count, 0), "", "no período"),
            "maint_count": (fmt.fmt_number(stats.maint_count, 0), "", "no período"),
            "km": (fmt.fmt_number(stats.km, 1), " km", "no período"),
            "liters": (fmt.fmt_number(stats.liters, 1), " L", "no período"),
            "spent": (fmt.fmt_brl(stats.spent), "", "combustível no período"),
            "maint_spent": (fmt.fmt_brl(stats.maint_spent), "", "serviços no período"),
            "total_spent": (fmt.fmt_brl(stats.total_spent), "", "combustível + manutenção"),
            "avg_price": (fmt.fmt_brl(stats.avg_price), "", "média do período"),
            "km_per_l": (
                fmt.fmt_number(stats.km_per_l, 2),
                " km/L",
                (
                    f"{fmt.fmt_number(stats.l_per_100km, 1)} L/100 km"
                    if stats.l_per_100km
                    else "sem dados suficientes"
                ),
            ),
            "cost_per_km": (fmt.fmt_brl(stats.cost_per_km), "/km", "combustível ÷ km rodados"),
            "cost_per_km_total": (fmt.fmt_brl(stats.cost_per_km_total), "/km",
                                  "tudo ÷ km rodados"),
            "avg_spent": (fmt.fmt_brl(stats.avg_spent), "", "valor por parada"),
        }
        for key, (value_text, unit, subtitle) in data.items():
            value_label, sub_label = self.cards[key]
            value_label.configure(text=value_text + unit)
            sub_label.configure(text=subtitle)

        self.tree.delete(*self.tree.get_children())
        for row in view.months:
            values = (
                row.label,
                row.count,
                fmt.fmt_number(row.km, 1),
                fmt.fmt_number(row.liters, 1),
                fmt.fmt_brl(row.spent),
                fmt.fmt_brl(row.maint_spent) if row.maint_spent else "-",
                fmt.fmt_brl(row.total),
                fmt.fmt_number(row.km_per_l, 2) if row.km_per_l else "-",
                fmt.fmt_brl(row.cost_per_km) if row.cost_per_km else "-",
            )
            self.tree.insert("", "end", values=values)

        self._current_view = view
        self._draw_chart()

    def _draw_chart(self):
        view = getattr(self, "_current_view", None)
        if view is None:
            return
        mode = self.cmb_mode.get() or MODES[0]

        if mode in ("Gasto mensal (R$)", "Km por mês", "Manutenção por mês (R$)"):
            labels = [row.label for row in view.months]
            if mode.startswith("Manutenção"):
                values = [row.maint_spent for row in view.months]
                unit = "R$ em manutenção por mês"
                tem_manut = any(row.maint_spent for row in view.months)
                self.chart_note.configure(
                    text="apenas serviços registrados em Manutenções" if tem_manut else ""
                )
            elif mode.startswith("Gasto"):
                values = [row.total for row in view.months]
                unit = "R$ por mês (combustível + manutenção)"
                tem_manut = any(row.maint_spent for row in view.months)
                self.chart_note.configure(
                    text="barras por mês calendário · combustível + manutenção"
                    if tem_manut else "barras por mês calendário"
                )
            else:
                values = [row.km for row in view.months]
                unit = "km por mês"
                self.chart_note.configure(
                    text="barras por mês calendário" if labels else ""
                )
        else:
            labels = [fmt.fmt_date(record.date) for record, _ in view.series]
            if mode.startswith("Consumo"):
                values = [seg.km_per_l if seg else None for _, seg in view.series]
                unit = "km/L por abastecimento"
            else:
                values = [seg.cost_per_km if seg else None for _, seg in view.series]
                unit = "R$ por km, por abastecimento"
            approx = sum(
                1 for _, seg in view.series if seg and seg.approximate and seg.km_per_l
            )
            if approx and mode.startswith("Consumo"):
                self.chart_note.configure(
                    text=f"{approx} valor(es) aproximado(s): marque 'Tanque cheio'"
                )
            else:
                self.chart_note.configure(text="")

        self.chart.set_data(labels, values, unit)
