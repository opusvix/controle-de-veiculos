"""Gráfico de barras desenhado com o próprio Canvas do Tkinter (sem dependências)."""
from __future__ import annotations

import math

import tkinter as tk
from tkinter import ttk

from ..format import fmt_number

ACCENT = "#2563eb"
GRID = "#eaeef3"
AXIS_TEXT = "#5b6472"
EMPTY_TEXT = "#96a0b0"


def _axis_label(value: float) -> str:
    if abs(value) >= 1000:
        return fmt_number(value, 0)
    if abs(value) >= 100:
        return fmt_number(value, 0)
    if abs(value) >= 10:
        return fmt_number(value, 1)
    return fmt_number(value, 2)


class BarChart(ttk.Frame):
    """Gráfico de barras vertical com eixo, grade e rótulos no padrão pt-BR."""

    def __init__(self, parent, height: int = 230, color: str = ACCENT):
        super().__init__(parent)
        self.color = color
        self.canvas = tk.Canvas(
            self,
            height=height,
            bg="white",
            highlightthickness=1,
            highlightbackground="#d7dce2",
        )
        self.canvas.pack(fill="both", expand=True)
        self._labels: list[str] = []
        self._values: list[float | None] = []
        self._unit = ""
        self._decimals_label = False
        self.canvas.bind("<Configure>", lambda _e: self.redraw())

    def set_data(self, labels: list[str], values: list[float | None], unit: str = "") -> None:
        self._labels = list(labels)
        self._values = list(values)
        self._unit = unit
        self.redraw()

    def redraw(self) -> None:
        c = self.canvas
        c.delete("all")
        width = c.winfo_width()
        height = c.winfo_height()
        if width < 60 or height < 60:
            return

        plotted = [v for v in self._values if v is not None and v > 0]
        if not self._labels or not plotted:
            c.create_text(
                width / 2,
                height / 2,
                text="Sem dados no período selecionado",
                fill=EMPTY_TEXT,
                font=("Segoe UI", 11),
            )
            return

        left, top, right, bottom = 66, 22, 18, 44
        plot_w = width - left - right
        plot_h = height - top - bottom
        if plot_w < 40 or plot_h < 40:
            return

        vmax = max(plotted) * 1.15
        steps = 4
        for i in range(steps + 1):
            value = vmax * i / steps
            y = top + plot_h - (value / vmax) * plot_h
            c.create_line(left, y, width - right, y, fill=GRID)
            c.create_text(
                left - 8,
                y,
                text=_axis_label(value),
                anchor="e",
                fill=AXIS_TEXT,
                font=("Segoe UI", 9),
            )

        if self._unit:
            c.create_text(left, 6, anchor="nw", text=self._unit, fill=AXIS_TEXT,
                          font=("Segoe UI", 9, "italic"))

        n = len(self._labels)
        slot = plot_w / n
        bar_w = max(2.0, min(46.0, slot * 0.62))
        max_label_chars = max(6, int(plot_w / (n * 9)))
        skip = max(1, math.ceil(n / max(1, int(plot_w / 52))))

        for i, (label, value) in enumerate(zip(self._labels, self._values)):
            x = left + slot * (i + 0.5)
            if value is None or value <= 0:
                continue
            bar_h = max(2.0, (value / vmax) * plot_h)
            y0 = top + plot_h - bar_h
            c.create_rectangle(x - bar_w / 2, y0, x + bar_w / 2, top + plot_h,
                               fill=self.color, width=0)
            if n <= 20:
                c.create_text(x, y0 - 4, anchor="s", text=fmt_number(value, 1),
                              fill=AXIS_TEXT, font=("Segoe UI", 8))
            if i % skip == 0:
                text = label if len(label) <= max_label_chars else label[: max_label_chars - 1] + "…"
                c.create_text(x, top + plot_h + 8, anchor="n", text=text,
                              fill=AXIS_TEXT, font=("Segoe UI", 8))
