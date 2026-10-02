"""Janela principal do aplicativo Controle de Veículos."""
from __future__ import annotations

import datetime as dt
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import __version__, caminhos, importers, storage
from ..models import Document
from .maintenance_tab import MaintenanceTab
from .refuels_tab import RefuelsTab
from .reports_tab import ReportsTab
from .vehicles_tab import VehiclesTab

BG = "#eef1f5"
ACCENT = "#2563eb"

FILETYPES = [("Arquivos de dados do Controle de Km", "*.json"), ("Todos os arquivos", "*.*")]
FILETYPES_IMPORT = [
    ("Planilhas e textos (CSV, TSV, XLSX)", "*.csv *.tsv *.txt *.xlsx *.xlsm"),
    ("CSV delimitado", "*.csv"),
    ("Texto separado por TAB", "*.tsv *.txt"),
    ("Planilha do Excel", "*.xlsx *.xlsm"),
    ("Todos os arquivos", "*.*"),
]


class App(tk.Tk):
    def __init__(self, ask_folder: bool = True):
        super().__init__()
        self.doc = Document()
        self.storage_path = storage.default_path()
        self.active_vehicle_id: str | None = None
        self.saved_at: str | None = None
        # Primeira abertura: decidimos perguntar onde gravar ANTES do
        # _initial_load, que já grava a configuração.
        self.ask_folder = ask_folder
        self._first_run = ask_folder and storage.primeira_execucao()

        self.title("Controle de Veículos")
        self.geometry("1180x790")
        self.minsize(1000, 660)
        self.configure(bg=BG)

        self._build_style()
        self._initial_load()
        self._build_menu()
        self._build_toolbar()
        self._build_notebook()
        self._build_statusbar()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.refresh()
        if self._first_run:
            # Depois da janela aparecer, pede a pasta dos dados.
            self.after(250, self._ask_data_folder)

    # --------------------------------------------------------------- estilo
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", font=("Segoe UI", 10), background=BG, foreground="#111827")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG)
        style.configure("TLabelframe", background=BG)
        style.configure("TLabelframe.Label", background=BG, font=("Segoe UI", 10, "bold"))
        style.configure("TCheckbutton", background=BG)
        style.configure("TButton", padding=(10, 5))
        style.configure("Accent.TButton", background=ACCENT, foreground="white",
                        font=("Segoe UI", 10, "bold"), padding=(12, 6))
        style.map("Accent.TButton",
                  background=[("active", "#1d4ed8"), ("disabled", "#a9c2f7")],
                  foreground=[("disabled", "#f2f6ff")])
        style.configure("Danger.TButton", foreground="#dc2626")
        style.map("Danger.TButton", foreground=[("active", "#b91c1c")])
        style.configure("TNotebook", background=BG, padding=4)
        style.configure("TNotebook.Tab", padding=(16, 7), font=("Segoe UI", 10))
        style.map("TNotebook.Tab", background=[("selected", "white")],
                  foreground=[("selected", ACCENT)])
        style.configure("Treeview", background="white", fieldbackground="white",
                        foreground="#111827", rowheight=27, font=("Segoe UI", 10))
        style.map("Treeview", background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"),
                        background="#f3f5f8", foreground="#374151")
        style.configure("Vertical.TScrollbar", background="#dfe4ea", troughcolor=BG)

    # -------------------------------------------------------------- arquivo
    def _initial_load(self):
        path = storage.load_last_path()
        if path is None and self._first_run:
            # Primeira abertura: a pasta ainda vai ser perguntada em seguida,
            # então não registra nada na configuração agora.
            self.storage_path = storage.default_path()
            return
        path = path or storage.default_path()
        if path.exists():
            self.open_path(path, quiet=True)
        else:
            self.storage_path = path
            storage.remember_path(path)

    def _ask_data_folder(self):
        """Primeira abertura: pergunta onde os dados serão gravados."""
        padrao = storage.default_path()
        inicial = padrao.parent
        try:
            inicial.mkdir(parents=True, exist_ok=True)  # pasta padrão é a sugerida
        except OSError:
            inicial = storage.documents_dir()
        escolhida = filedialog.askdirectory(
            parent=self,
            title="Onde guardar os dados do Controle de Veículos?",
            initialdir=str(inicial),
            mustexist=False,
        )
        if not escolhida:
            # Usuário desistiu: usa o padrão e não pergunta de novo.
            storage.remember_path(padrao)
            return

        pasta = Path(escolhida)
        arquivo = pasta / padrao.name
        try:
            pasta.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        storage.remember_path(arquivo, escolhido=True)
        self.storage_path = arquivo

        if arquivo.exists():
            self.open_path(arquivo, quiet=True)
            return
        if not self.save(quiet=True):
            # Sem permissão de gravar ali: volta para o padrão.
            self.storage_path = padrao
            storage.remember_path(padrao)
            self.refresh()
            return
        self.refresh()
        messagebox.showinfo(
            "Onde ficam os dados",
            f"Tudo certo. Os dados serão gravados em:\n\n{arquivo}\n\n"
            "O arquivo já foi criado. Para usar outra pasta depois, "
            "use Arquivo > Salvar como...",
            parent=self,
        )

    def _quarantine(self, path: Path) -> None:
        """Preserva um arquivo problemático com outro nome, sem apagar nada."""
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        target = path.with_name(f"{path.name}.problema-{stamp}.json")
        try:
            os.replace(path, target)
            messagebox.showwarning(
                "Arquivo preservado",
                f"O arquivo com problema foi renomeado e nada foi apagado:\n\n{target}",
                parent=self,
            )
        except OSError:
            pass

    def open_path(self, path: Path, quiet: bool = False) -> bool:
        path = Path(path)
        try:
            doc = storage.load(path)
        except storage.StorageError as exc:
            if quiet:
                if messagebox.askyesno(
                    "Arquivo com problema",
                    f"{exc}\n\nDeseja preservar esse arquivo com outro nome "
                    "e iniciar um novo arquivo?",
                    parent=self,
                ):
                    self._quarantine(path)
                    self.doc = Document()
                    self.storage_path = path
                    self.active_vehicle_id = None
                    self.save()
                else:
                    self.doc = Document()
                    self.storage_path = storage.default_path()
                    self.active_vehicle_id = None
                    storage.remember_path(self.storage_path)
                self.refresh()
                return False
            messagebox.showerror("Não foi possível abrir o arquivo", str(exc), parent=self)
            return False

        self.doc = doc
        self.storage_path = path
        self.active_vehicle_id = doc.vehicles[0].id if doc.vehicles else None
        storage.remember_path(path)
        self.refresh()
        if not quiet:
            messagebox.showinfo(
                "Arquivo aberto",
                f"Dados carregados de:\n{path}\n\n"
                f"{len(doc.vehicles)} veículo(s), {len(doc.refuels)} abastecimento(s) "
                f"e {len(doc.maintenances)} manutenção(ões).",
                parent=self,
            )
        return True

    def new_file(self):
        chosen = filedialog.asksaveasfilename(
            parent=self,
            title="Novo arquivo de dados",
            defaultextension=".json",
            filetypes=FILETYPES,
            initialdir=str(self.storage_path.parent),
            initialfile="dados.json",
        )
        if not chosen:
            return
        if not self.save(quiet=True):
            return
        self.doc = Document()
        self.storage_path = Path(chosen)
        self.active_vehicle_id = None
        storage.remember_path(self.storage_path)
        self.save()
        self.refresh()

    def open_file(self):
        chosen = filedialog.askopenfilename(
            parent=self,
            title="Abrir arquivo de dados",
            filetypes=FILETYPES,
            initialdir=str(self.storage_path.parent),
        )
        if chosen:
            self.open_path(Path(chosen))

    def import_sheet(self):
        """Importa abastecimentos de .csv/.tsv/.xlsx (colunas pelo cabeçalho)."""
        chosen = filedialog.askopenfilename(
            parent=self,
            title="Importar planilha ou CSV",
            filetypes=FILETYPES_IMPORT,
            initialdir=str(self.storage_path.parent),
        )
        if not chosen:
            return
        path = Path(chosen)
        try:
            planilhas = importers.ler_arquivo(path)
            atual = self.current_vehicle()
            nome_padrao = (atual.name if atual else
                           (self.doc.vehicles[0].name if self.doc.vehicles else "Meu veículo"))
            novo, resumo, ignoradas = importers.montar_documento(planilhas, nome_padrao)
        except importers.ImportFileError as exc:
            messagebox.showerror("Não foi possível importar", str(exc), parent=self)
            return
        except Exception as exc:  # noqa: BLE001 - arquivo corrompido/campos inesperados
            messagebox.showerror("Não foi possível importar",
                                 f"{type(exc).__name__}: {exc}", parent=self)
            return

        if not novo.vehicles and not novo.refuels:
            detalhe = "\n".join(resumo["abas"]) or "Nenhuma linha lida."
            messagebox.showerror(
                "Nenhuma linha válida",
                f"Não encontrei dados aproveitáveis em \"{path.name}\".\n\n"
                f"{detalhe}\n\nConfira o formato em Ajuda > Formato das colunas.",
                parent=self)
            return

        linhas = [
            f"Arquivo: {path.name}",
            f"{resumo['linhas']} linha(s) lida(s) em {len(resumo['abas'])} aba(s)",
            f"{len(novo.vehicles)} veículo(s) e {len(novo.refuels)} abastecimento(s)",
        ]
        if ignoradas:
            linhas.append(
                f"{len(ignoradas)} linha(s) ignorada(s): {ignoradas[0]}"
                + (" ..." if len(ignoradas) > 1 else ""))

        if self.doc.vehicles or self.doc.refuels:
            linhas += [
                "",
                f"Este arquivo já tem {len(self.doc.refuels)} abastecimento(s) e "
                f"{len(self.doc.vehicles)} veículo(s).",
                "",
                "Sim = MESCLAR (junta, sem duplicar)",
                "Não = SUBSTITUIR tudo pelo arquivo importado",
                "Cancelar = não importar",
            ]
            escolha = messagebox.askyesnocancel(
                "Importar planilha", "\n".join(linhas), parent=self)
            if escolha is None:
                return
            modo = "mesclar" if escolha else "substituir"
        else:
            if not messagebox.askyesno("Importar planilha",
                                       "\n".join(linhas) + "\n\nImportar?",
                                       parent=self):
                return
            modo = "substituir"

        if modo == "substituir":
            # A planilha não traz manutenções: preserva as existentes, ligando-as
            # ao veículo de mesmo nome quando houver.
            mantidas = list(self.doc.maintenances)
            nomes_antigos = {v.id: v.name for v in self.doc.vehicles}
            self.doc = novo
            self.active_vehicle_id = novo.vehicles[0].id if novo.vehicles else None
            id_por_nome = {v.name: v.id for v in self.doc.vehicles}
            preservadas = []
            for registro in mantidas:
                nome = nomes_antigos.get(registro.vehicle_id, "")
                novo_id = id_por_nome.get(nome)
                if novo_id:
                    registro.vehicle_id = novo_id
                    preservadas.append(registro)
            self.doc.maintenances = preservadas
            contagem = {"veiculos": len(novo.vehicles), "refuels": len(novo.refuels),
                        "duplicados": 0, "manutencoes": len(preservadas),
                        "manutencoes_perdidas": len(mantidas) - len(preservadas)}
        else:
            contagem = importers.mesclar_documento(novo, self.doc)
            contagem["manutencoes"] = len(self.doc.maintenances)

        self.save(quiet=True)
        self.refresh()

        mensagem = (f"Importado: {contagem['refuels']} abastecimento(s), "
                    f"{contagem['veiculos']} veículo(s)")
        if contagem["duplicados"]:
            mensagem += f", {contagem['duplicados']} duplicado(s)"
        if ignoradas:
            mensagem += f", {len(ignoradas)} ignorada(s)"
        if contagem.get("manutencoes"):
            mensagem += f"\n\n{contagem['manutencoes']} manutenção(ões) mantida(s) " \
                        "(a planilha não traz esse tipo de dado)."
        if contagem.get("manutencoes_perdidas"):
            mensagem += (
                f"\n\n{contagem['manutencoes_perdidas']} manutenção(ões) ficaram sem "
                "veículo correspondente na planilha e foram descartadas."
            )
        messagebox.showinfo("Importação concluída",
                            f"{path.name}\n\n{mensagem}", parent=self)

    def save_as(self):
        chosen = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar como",
            defaultextension=".json",
            filetypes=FILETYPES,
            initialdir=str(self.storage_path.parent),
            initialfile=self.storage_path.name,
        )
        if not chosen:
            return
        self.storage_path = Path(chosen)
        storage.remember_path(self.storage_path)
        self.save()
        self.refresh()

    def save(self, quiet: bool = False) -> bool:
        try:
            storage.save(self.doc, self.storage_path)
        except storage.StorageError as exc:
            if not quiet:
                messagebox.showerror("Erro ao salvar", str(exc), parent=self)
            else:
                messagebox.showerror("Erro ao salvar", str(exc), parent=self)
            return False
        self.saved_at = dt.datetime.now().strftime("%H:%M:%S")
        self._update_status()
        return True

    def changed(self):
        """Chamado pelas abas após qualquer alteração: grava e atualiza tudo."""
        self.save(quiet=True)
        self.refresh()

    # --------------------------------------------------------------- layout
    def _build_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Novo arquivo...", accelerator="Ctrl+N",
                              command=self.new_file)
        file_menu.add_command(label="Abrir...", accelerator="Ctrl+O",
                              command=self.open_file)
        file_menu.add_command(label="Importar planilha/CSV...", accelerator="Ctrl+I",
                              command=self.import_sheet)
        file_menu.add_separator()
        file_menu.add_command(label="Salvar agora", accelerator="Ctrl+S",
                              command=lambda: self.save())
        file_menu.add_command(label="Salvar como...", accelerator="Ctrl+Shift+S",
                              command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self._on_close)
        menubar.add_cascade(label="Arquivo", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Manual completo (como instalar e usar)...",
                              command=self.abrir_manual)
        help_menu.add_command(label="Como o consumo é calculado", command=self._help)
        help_menu.add_command(label="Formato das colunas (importação)",
                              command=self._help_formato)
        help_menu.add_separator()
        help_menu.add_command(label="Sobre", command=self._about)
        menubar.add_cascade(label="Ajuda", menu=help_menu)
        self.config(menu=menubar)

        self.bind("<Control-n>", lambda _e: self.new_file())
        self.bind("<Control-o>", lambda _e: self.open_file())
        self.bind("<Control-i>", lambda _e: self.import_sheet())
        self.bind("<Control-s>", lambda _e: self.save())
        self.bind("<Control-Shift-S>", lambda _e: self.save_as())

    def _build_toolbar(self):
        bar = ttk.Frame(self, padding=(14, 10))
        bar.pack(fill="x")

        ttk.Label(bar, text="Veículo:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.cmb_vehicle = ttk.Combobox(bar, state="readonly", width=28)
        self.cmb_vehicle.pack(side="left", padx=(6, 10))
        self.cmb_vehicle.bind("<<ComboboxSelected>>", self._on_vehicle_selected)

        ttk.Button(bar, text="+ Novo veículo", command=self.goto_vehicles).pack(side="left")
        ttk.Button(bar, text="Registrar manutenção",
                   command=self.goto_maintenance).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="Registrar abastecimento", style="Accent.TButton",
                   command=self.goto_refuel).pack(side="left", padx=(8, 0))

        ttk.Label(bar, text="Ctrl+S salva • dados em arquivo .json",
                  foreground="#5b6472").pack(side="right")
        ttk.Button(bar, text="Ajuda", command=self.abrir_manual).pack(
            side="right", padx=(0, 12))

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=(0, 4))

        self.refuels_tab = RefuelsTab(self.notebook, self)
        self.maintenance_tab = MaintenanceTab(self.notebook, self)
        self.reports_tab = ReportsTab(self.notebook, self)
        self.vehicles_tab = VehiclesTab(self.notebook, self)
        self.notebook.add(self.refuels_tab, text="  Abastecimentos  ")
        self.notebook.add(self.maintenance_tab, text="  Manutenções  ")
        self.notebook.add(self.reports_tab, text="  Relatórios  ")
        self.notebook.add(self.vehicles_tab, text="  Veículos  ")

    def _build_statusbar(self):
        bar = ttk.Frame(self, padding=(14, 4))
        bar.pack(fill="x")
        self.status_path = ttk.Label(bar, text="", foreground="#5b6472",
                                     font=("Segoe UI", 9))
        self.status_path.pack(side="left")
        self.status_saved = ttk.Label(bar, text="", foreground="#5b6472",
                                      font=("Segoe UI", 9))
        self.status_saved.pack(side="right")

    # --------------------------------------------------------------- estado
    def current_vehicle(self):
        return self.doc.get_vehicle(self.active_vehicle_id)

    def set_active_vehicle(self, vehicle_id: str | None):
        self.active_vehicle_id = vehicle_id
        self.refresh()

    def _on_vehicle_selected(self, _event=None):
        index = self.cmb_vehicle.current()
        if 0 <= index < len(self.doc.vehicles):
            self.active_vehicle_id = self.doc.vehicles[index].id
            self.refresh()

    def refresh(self):
        if not hasattr(self, "notebook"):
            return
        names = [v.name for v in self.doc.vehicles]
        ids = [v.id for v in self.doc.vehicles]
        if not ids:
            self.active_vehicle_id = None
            self.cmb_vehicle.configure(values=[])
            self.cmb_vehicle.set("")
        else:
            if self.active_vehicle_id not in ids:
                self.active_vehicle_id = ids[0]
            self.cmb_vehicle.configure(values=names)
            self.cmb_vehicle.set(names[ids.index(self.active_vehicle_id)])
        self._update_status()
        self.refuels_tab.refresh()
        self.maintenance_tab.refresh()
        self.reports_tab.refresh()
        self.vehicles_tab.refresh()

    def _update_status(self):
        if not hasattr(self, "status_path"):
            return
        count = len(self.doc.refuels)
        maint = len(self.doc.maintenances)
        self.status_path.configure(
            text=f"Arquivo: {self.storage_path}  •  "
                 f"{len(self.doc.vehicles)} veículo(s), {count} abastecimento(s), "
                 f"{maint} manutenção(ões)"
        )
        self.status_saved.configure(
            text=f"Salvo às {self.saved_at}" if self.saved_at else "Ainda não salvo"
        )

    # --------------------------------------------------------------- ações
    def goto_refuel(self):
        if not self.doc.vehicles:
            messagebox.showinfo(
                "Sem veículo",
                "Cadastre um veículo antes de registrar abastecimentos.",
                parent=self,
            )
            self.goto_vehicles()
            return
        self.notebook.select(self.refuels_tab)
        self.refuels_tab.e_km.focus_set()

    def goto_maintenance(self):
        if not self.doc.vehicles:
            messagebox.showinfo(
                "Sem veículo",
                "Cadastre um veículo antes de registrar manutenções.",
                parent=self,
            )
            self.goto_vehicles()
            return
        self.notebook.select(self.maintenance_tab)
        self.maintenance_tab.e_km.focus_set()

    def goto_vehicles(self):
        self.notebook.select(self.vehicles_tab)
        self.vehicles_tab.e_name.focus_set()

    def abrir_manual(self):
        """Abre o passo a passo completo (INSTALAR-COMO-USAR.txt) na tela."""
        erro = caminhos.abrir_manual()
        if erro:
            messagebox.showinfo("Manual", erro, parent=self)

    def _help(self):
        messagebox.showinfo(
            "Como o consumo é calculado",
            "km/L = distância percorrida ÷ litros abastecidos nesse trecho.\n\n"
            "• A referência é o último abastecimento com 'Tanque cheio' marcado.\n"
            "• Sem marcação, o valor aparece com '~' (aproximado).\n"
            "• R$/km = valor gasto no trecho ÷ distância.\n"
            "• No resumo do período: km rodados ÷ litros abastecidos.\n\n"
            "Marque 'Tanque cheio' toda vez que encher o tanque para ter os "
            "números exatos.",
            parent=self,
        )

    def _help_formato(self):
        messagebox.showinfo("Formato das colunas", importers.TEXTO_FORMATO, parent=self)

    def _about(self):
        messagebox.showinfo(
            "Sobre",
            f"Controle de Veículos v{__version__}\n\n"
            "App desktop em Python/Tkinter (abastecimentos e manutenções).\n"
            "Seus dados ficam somente neste computador, em arquivo JSON:\n"
            f"{self.storage_path}\n\n"
            f"Python {sys.version.split()[0]}",
            parent=self,
        )

    def _on_close(self):
        if not self.save(quiet=True):
            if not messagebox.askyesno(
                "Erro ao salvar",
                "Não foi possível gravar o arquivo de dados.\nDeseja sair mesmo assim?",
                parent=self,
            ):
                return
        self.destroy()
