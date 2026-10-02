"""Tela de login: usuário, senha e a escolha de como trabalhar.

A conta é local (controle_veiculos.conta): criada na primeira vez e guardada
neste computador. Os três botões dizem onde a pessoa vai trabalhar:
  Aplicativo  - a janela normal do programa
  Computador  - a versão web no navegador padrão desta máquina
  Smartphone  - liga o Servidor Wi-Fi para o celular acessar
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .. import caminhos, conta

BG = "#eef1f5"
ACCENT = "#2563eb"
ERRO = "#dc2626"
OK = "#15803d"

MODOS = [
    ("aplicativo", "Aplicativo", "abre a janela\ndo programa"),
    ("computador", "Computador", "abre no navegador\ndeste computador"),
    ("smartphone", "Smartphone", "faz o celular\nacessar pelo Wi-Fi"),
]


class LoginWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.modo: str | None = None
        self._ocupado = False
        self._criando = not conta.existe()

        self.title("Controle de Veículos - acesso")
        self.configure(bg=BG)
        self.resizable(False, False)

        estilo = ttk.Style(self)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure(".", font=("Segoe UI", 10), background=BG, foreground="#111827")
        estilo.configure("TFrame", background=BG)
        estilo.configure("TLabel", background=BG)
        estilo.configure("TButton", padding=(10, 6))
        estilo.configure("Accent.TButton", background=ACCENT, foreground="white",
                         font=("Segoe UI", 10, "bold"), padding=(12, 8))
        estilo.map("Accent.TButton", background=[("active", "#1d4ed8")])

        self._montar()
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        self.after(50, self._centralizar)

    def _fechar(self) -> None:
        self.modo = None
        self.quit()

    # ------------------------------------------------------------------ UI
    def _montar(self) -> None:
        raiz = ttk.Frame(self, padding=(28, 22, 28, 18))
        raiz.pack(fill="both", expand=True)

        ttk.Label(raiz, text="Controle de Veículos",
                  font=("Segoe UI", 16, "bold")).pack(anchor="w")
        self.subtitulo = ttk.Label(
            raiz,
            text=("Primeiro acesso: crie um usuário e uma senha para este computador."
                  if self._criando else "Digite seu usuário e sua senha para continuar."),
            foreground="#4b5563", wraplength=400)
        self.subtitulo.pack(anchor="w", pady=(2, 14))

        ttk.Label(raiz, text="Usuário").pack(anchor="w")
        self.e_usuario = ttk.Entry(raiz, width=34)
        self.e_usuario.pack(anchor="w", fill="x", pady=(2, 10))

        ttk.Label(raiz, text="Senha").pack(anchor="w")
        self.e_senha = ttk.Entry(raiz, width=34, show="•")
        self.e_senha.pack(anchor="w", fill="x", pady=(2, 10))

        self.lbl_confirma = ttk.Label(raiz, text="Repita a senha")
        self.e_confirma = ttk.Entry(raiz, width=34, show="•")
        if self._criando:
            self.lbl_confirma.pack(anchor="w")
            self.e_confirma.pack(anchor="w", fill="x", pady=(2, 10))

        self.status = tk.Label(raiz, text="", bg=BG, fg=ERRO, justify="left",
                               anchor="w", font=("Segoe UI", 9), wraplength=400)
        self.status.pack(fill="x", pady=(2, 12))

        ttk.Label(raiz, text="Como você vai trabalhar?",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))

        linha = ttk.Frame(raiz)
        linha.pack(fill="x")
        self.botoes: list[ttk.Button] = []
        for i, (chave, rotulo, dica) in enumerate(MODOS):
            col = ttk.Frame(linha)
            col.grid(row=0, column=i, sticky="n", padx=(0 if i == 0 else 8))
            estilo = "Accent.TButton" if (chave == "aplicativo") else "TButton"
            botao = ttk.Button(col, text=rotulo, style=estilo, width=15,
                               command=lambda m=chave: self._entrar(m))
            botao.pack(fill="x")
            tk.Label(col, text=dica, bg=BG, fg="#4b5563", justify="left",
                     font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))
            self.botoes.append(botao)
            if chave == "aplicativo":
                botao.bind("<Return>", lambda _e: self._entrar("aplicativo"))

        rodape = ttk.Frame(raiz)
        rodape.pack(fill="x", pady=(16, 0))
        self.btn_esqueci = tk.Button(
            rodape, text="Esqueci a senha", bd=0, bg=BG, fg=ACCENT, cursor="hand2",
            activebackground=BG, activeforeground="#1d4ed8",
            font=("Segoe UI", 9), command=self._esqueci_senha)
        if not self._criando:
            self.btn_esqueci.pack(side="left")
        tk.Button(
            rodape, text="Abrir o manual (passo a passo)", bd=0, bg=BG, fg=ACCENT,
            cursor="hand2", activebackground=BG, activeforeground="#1d4ed8",
            font=("Segoe UI", 9), command=self._abrir_manual).pack(side="right")

        self.e_usuario.focus_set()

    def _centralizar(self) -> None:
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = max(0, (self.winfo_screenwidth() - w) // 2)
        y = max(0, (self.winfo_screenheight() - h) // 3)
        self.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------ mensagens
    def _erro(self, texto: str) -> None:
        self.status.configure(text=texto, fg=ERRO)

    def _info(self, texto: str) -> None:
        self.status.configure(text=texto, fg=OK)

    def _modo_criando(self) -> None:
        self._criando = True
        self.subtitulo.configure(
            text="Primeiro acesso: crie um usuário e uma senha para este computador.")
        if not self.lbl_confirma.winfo_ismapped():
            self.lbl_confirma.pack(after=self.e_senha, anchor="w")
            self.e_confirma.pack(after=self.lbl_confirma, anchor="w", fill="x",
                                 pady=(2, 10))
        if self.btn_esqueci.winfo_ismapped():
            self.btn_esqueci.pack_forget()
        self.e_senha.delete(0, "end")
        self.e_confirma.delete(0, "end")
        self.e_usuario.focus_set()

    def _esqueci_senha(self) -> None:
        if messagebox.askyesno(
            "Esqueci a senha",
            "Isso reinicia a senha de ACESSO deste computador.\n\n"
            "Seus dados (abastecimentos, manutenções...) continuam intactos.\n\n"
            "Continuar?",
            parent=self,
        ):
            conta.apagar()
            self._modo_criando()
            self._info("Conta reiniciada. Crie um usuário e uma senha novos.")

    def _abrir_manual(self) -> None:
        erro = caminhos.abrir_manual()
        if erro:
            messagebox.showinfo("Manual", erro, parent=self)

    # --------------------------------------------------------------- entrar
    def _ocupar(self, ocupado: bool) -> None:
        self._ocupado = ocupado
        estado = "disabled" if ocupado else "normal"
        for botao in self.botoes:
            botao.configure(state=estado)

    def _validar(self) -> bool:
        usuario = self.e_usuario.get().strip()
        senha = self.e_senha.get().strip()
        if not usuario:
            self._erro("Digite o seu usuário.")
            self.e_usuario.focus_set()
            return False
        if self._criando:
            if len(senha) < conta.MINIMO_SENHA:
                self._erro(f"A senha precisa ter pelo menos "
                           f"{conta.MINIMO_SENHA} caracteres.")
                self.e_senha.focus_set()
                return False
            if senha != self.e_confirma.get().strip():
                self._erro("As duas senhas não batem. Digite a mesma de novo.")
                self.e_senha.focus_set()
                return False
            try:
                conta.criar(usuario, senha)
            except conta.ContaError as exc:
                self._erro(str(exc))
                return False
            self._criando = False
            self.subtitulo.configure(
                text=f"Pronto, {usuario}. Escolha como você vai trabalhar.")
            self.lbl_confirma.pack_forget()
            self.e_confirma.pack_forget()
            self.btn_esqueci.pack(side="left")
            self._info(f"Conta criada para {usuario} ✓")
            return True  # conta criada: segue direto para o modo escolhido
        if not conta.validar(usuario, senha):
            self._erro("Usuário ou senha incorretos.")
            self.e_senha.select_range(0, "end")
            self.e_senha.focus_set()
            return False
        return True

    def _entrar(self, modo: str) -> None:
        if self._ocupado:
            return
        if not self._validar():
            return

        if modo == "aplicativo":
            self.modo = modo
            self.quit()
            return

        # Computador / Smartphone: liga o Servidor Wi-Fi (janela própria).
        self._ocupar(True)
        self._info("Ligando o Servidor Wi-Fi...")
        self.update_idletasks()
        if not caminhos.iniciar_servidor():
            self._ocupar(False)
            self._erro("Não encontrei o \"Servidor Wi-Fi.bat\" na pasta web\\.")
            return
        if modo == "computador":
            erro = caminhos.abrir_versao_web()
            if erro:
                self._ocupar(False)
                self._erro(erro.replace("\n", " "))
                return
        self.modo = modo
        self.quit()
