"""Testes de fumaça: cálculos, arquivo e interface.

Executar: python tests/test_smoke.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controle_veiculos import calcs, format as fmt, storage  # noqa: E402
from controle_veiculos.models import Document, Maintenance, Refuel, Vehicle  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"  ok: {message}")


def make_doc() -> Document:
    car = Vehicle(id="carro", name="Gol 2019", plate="ABC1D23", year=2019,
                  fuel="Flex", initial_km=40000.0)
    moto = Vehicle(id="moto", name="Moto", fuel="Gasolina", initial_km=1000.0)
    doc = Document(vehicles=[car, moto])

    # Tanque cheio -> parcial -> tanque cheio -> tanque cheio
    refuels = [
        Refuel(id="r1", vehicle_id="carro", date="2026-06-01", odometer=40000.0,
               liters=40.0, price=5.50, total=220.0, full_tank=True),
        Refuel(id="r2", vehicle_id="carro", date="2026-06-10", odometer=40480.0,
               liters=20.0, price=5.60, total=112.0, full_tank=False),
        Refuel(id="r3", vehicle_id="carro", date="2026-06-20", odometer=40960.0,
               liters=36.0, price=5.70, total=205.2, full_tank=True),
        Refuel(id="r4", vehicle_id="carro", date="2026-07-05", odometer=41500.0,
               liters=38.0, price=5.80, total=220.4, full_tank=True),
        Refuel(id="r5", vehicle_id="moto", date="2026-06-15", odometer=1200.0,
               liters=12.0, price=5.90, total=70.8, full_tank=True),
    ]
    doc.refuels = refuels

    # Manutenções: uma por mês do carro (junho/julho) e uma da moto
    doc.maintenances = [
        Maintenance(id="m1", vehicle_id="carro", date="2026-06-15", odometer=40500.0,
                    type="Troca de óleo", details="Óleo 5W30 + filtro", cost=250.0,
                    shop="Auto Center", next_km=5000.0),
        Maintenance(id="m2", vehicle_id="carro", date="2026-07-10", odometer=41200.0,
                    type="Alinhamento", details="Alinhamento e balanceamento",
                    cost=120.0, next_date="2026-07-20"),
        Maintenance(id="m3", vehicle_id="moto", date="2026-06-20", odometer=1150.0,
                    type="Revisão", cost=90.0, next_km=500.0),
    ]
    return doc


def test_format():
    print("formato pt-BR")
    check(fmt.parse_number("1.234,56") == 1234.56, "1.234,56 -> 1234.56")
    check(fmt.parse_number("1234,56") == 1234.56, "1234,56 -> 1234.56")
    check(fmt.parse_number("5.79") == 5.79, "5.79 -> 5.79 (decimal)")
    check(fmt.parse_number("45.123") == 45123.0, "45.123 -> 45123 (milhar)")
    check(fmt.parse_number(" 45120 ") == 45120.0, "45120 -> 45120")
    check(fmt.parse_number("abc") is None, "texto -> None")
    check(fmt.fmt_number(1234.5, 1) == "1.234,5", "formato 1.234,5")
    check(fmt.fmt_brl(1234.5) == "R$ 1.234,50", "formato R$ 1.234,50")
    check(fmt.parse_date("25/09/2026").isoformat() == "2026-09-25", "data dd/mm/aaaa")
    check(fmt.parse_date("31/02/2026") is None, "data inválida -> None")
    check(fmt.fmt_date("2026-09-25") == "25/09/2026", "ISO -> dd/mm/aaaa")


def test_segments():
    print("cálculo por trecho")
    doc = make_doc()
    ordered = calcs.ordered_refuels(doc, "carro")
    segs = calcs.build_segments(ordered)

    # r2: base = r1 (tanque cheio) -> 480 km / 20 L = 24 km/L (aprox: r2 não cheio)
    check(abs(segs["r2"].distance - 480.0) < 1e-6, "distância r1->r2 = 480 km")
    check(abs(segs["r2"].km_per_l - 24.0) < 1e-6, "r2 = 24,0 km/L")
    check(segs["r2"].approximate is True, "r2 marcado como aproximado")

    # r3: base = r1 -> 960 km / (20 + 36) L = 17,14 km/L, e r3 é tanque cheio -> exato
    check(abs(segs["r3"].distance - 960.0) < 1e-6, "distância r1->r3 = 960 km")
    check(abs(segs["r3"].km_per_l - 960 / 56) < 1e-9, "r3 = 17,14 km/L (56 L)")
    check(segs["r3"].approximate is False, "r3 exato (tanque cheio)")

    # r4: base = r3 -> 540 km / 38 L
    check(abs(segs["r4"].km_per_l - 540 / 38) < 1e-9, "r4 = 14,21 km/L")
    check(segs["r4"].approximate is False, "r4 exato")

    # moto: registro único -> sem trecho
    ordered_moto = calcs.ordered_refuels(doc, "moto")
    check(calcs.build_segments(ordered_moto) == {}, "1º registro não gera trecho")


def test_report():
    print("relatório por período")
    doc = make_doc()
    view = calcs.report(doc, ["carro"])
    s = view.stats
    check(s.count == 4, "4 abastecimentos do carro")
    check(abs(s.km - 1500.0) < 1e-6, "km = 41500 - 40000 = 1500")
    check(abs(s.liters - 134.0) < 1e-6, "litros = 134,0")
    check(abs(s.spent - 757.6) < 1e-6, "gasto = 757,60")
    check(abs(s.km_per_l - 1500 / 134) < 1e-9, "consumo médio = km/litros")
    check(abs(s.avg_price - 757.6 / 134) < 1e-9, "preço médio do litro")
    check(abs(s.cost_per_km - 757.6 / 1500) < 1e-9, "custo por km")

    jul = calcs.report(doc, ["carro"], "2026-07-01", None)
    check(jul.stats.count == 1, "período julho = 1 registro")
    check(abs(jul.stats.km - 540.0) < 1e-6, "julho: 540 km do trecho")

    all_v = calcs.report(doc, ["carro", "moto"])
    check(all_v.stats.count == 5, "todos os veículos = 5 registros")

    months = view.months
    check([m.label for m in months] == ["07/2026", "06/2026"], "resumo mensal ordenado")
    check(abs(months[1].km - 960.0) < 1e-6, "junho = 960 km")
    check(len(view.series) == 4, "série do gráfico com 4 pontos")


def test_maintenance():
    print("manutenções")
    doc = make_doc()

    # modelo ida e volta
    raw = doc.to_dict()
    check(raw["version"] == 2, "documento na versão 2")
    check(len(raw["maintenances"]) == 3, "3 manutenções serializadas")
    back = Document.from_dict(raw)
    check(len(back.maintenances) == 3, "manutenções recarregadas do JSON")
    check(back.maintenances[0].type == "Troca de óleo", "tipo do serviço preservado")
    check(back.maintenances[0].cost == 250.0 and back.maintenances[0].shop == "Auto Center",
          "custo e oficina preservados")
    check(back.maintenances[1].next_date == "2026-07-20", "data-alvo preservada")
    check(back.maintenances[0].due_km == 45500.0, "vencimento por km = 40.500 + 5.000")

    # arquivo antigo (sem a chave "maintenances") continua abrindo
    antigo = doc.to_dict()
    del antigo["maintenances"]
    check(Document.from_dict(antigo).maintenances == [], "arquivo antigo abre sem manutenções")

    # relatório: manutenção em linha separada + total geral
    view = calcs.report(doc, ["carro"])
    s = view.stats
    check(s.maint_count == 2, "2 manutenções do carro no período")
    check(abs(s.maint_spent - 370.0) < 1e-6, "gasto com manutenção = 370,00")
    check(abs(s.spent - 757.6) < 1e-6, "combustível continua 757,60")
    check(abs(s.total_spent - 1127.6) < 1e-6, "total geral = 757,60 + 370,00")
    check(abs(s.cost_per_km_total - 1127.6 / 1500) < 1e-9, "custo por km total")

    julho = view.months[0]
    check(julho.label == "07/2026", "primeiro mês = 07/2026")
    check(abs(julho.maint_spent - 120.0) < 1e-6, "julho: 120,00 de manutenção")
    check(abs(julho.total - julho.spent - 120.0) < 1e-6, "total do mês = combustível + manutenção")

    # mês só com manutenção aparece no resumo (mesmo sem abastecimento)
    so_manut = calcs.report(doc, ["moto"], "2026-06-18", "2026-06-30")
    check(len(so_manut.months) == 1, "mês só com manutenção entra no resumo")
    check(so_manut.months[0].count == 0, "sem abastecimento nesse mês")
    check(abs(so_manut.months[0].maint_spent - 90.0) < 1e-6, "90,00 de manutenção")
    check(abs(so_manut.months[0].total - 90.0) < 1e-6, "total do mês = 90,00")

    # avisos da próxima manutenção
    hoje = dt.date(2026, 9, 29)
    lembretes = calcs.reminders(doc, "carro", hoje)
    check(len(lembretes) == 2, "um aviso por tipo de serviço")
    niveis = {r.maintenance.type: r.level for r in lembretes}
    check(niveis["Troca de óleo"] == "ok", "troca de óleo ainda em dia")
    check(niveis["Alinhamento"] == "atrasada", "alinhamento atrasado (data passou)")

    moto = {r.maintenance.type: r for r in calcs.reminders(doc, "moto", hoje)}
    check(moto["Revisão"].level == "proxima", "revisão próxima por quilometragem")
    check(abs(moto["Revisão"].remaining_km - 450.0) < 1e-6, "faltam 450 km")
    check(moto["Revisão"].label == "Em 450 km", f"rótulo: {moto['Revisão'].label}")

    # um serviço novo do mesmo tipo fecha o aviso do anterior
    doc.maintenances.append(Maintenance(id="m4", vehicle_id="carro", date="2026-09-01",
                                        odometer=41400.0, type="Alinhamento"))
    depois = calcs.reminders(doc, "carro", hoje)
    check(all(r.maintenance.type != "Alinhamento" for r in depois),
          "registro mais recente do tipo fecha o aviso anterior")

    # aviso atrasado por quilometragem
    atras_doc = Document(
        vehicles=[Vehicle(id="carro", name="Gol 2019", initial_km=45000.0)],
        maintenances=[Maintenance(id="m5", vehicle_id="carro", date="2026-01-10",
                                  odometer=36000.0, type="Pastilhas de freio",
                                  next_km=5000.0)],
    )
    atrasado = calcs.reminders(atras_doc, "carro", hoje)
    check(atrasado[0].level == "atrasada", "serviço vencido por km é atrasado")
    check(atrasado[0].remaining_km < 0, "quilometragem restante negativa")


def test_storage():
    print("arquivo JSON")
    doc = make_doc()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sub" / "dados.json"
        storage.save(doc, path)
        check(path.exists(), "arquivo criado (inclusive a pasta)")
        raw = json.loads(path.read_text(encoding="utf-8"))
        check(raw["version"] == 2 and len(raw["vehicles"]) == 2, "conteúdo JSON válido")
        check(len(raw["maintenances"]) == 3, "manutenções gravadas")
        check(not path.with_name(path.name + ".tmp").exists(), "gravação atômica sem resíduo")

        loaded = storage.load(path)
        check(len(loaded.vehicles) == 2 and len(loaded.refuels) == 5, "recarrega tudo")
        check(len(loaded.maintenances) == 3, "manutenções recarregadas")
        check(loaded.maintenances[0].next_km == 5000.0, "intervalo de revisão preservado")
        check(loaded.vehicles[0].name == "Gol 2019", "dados preservados")
        check(loaded.refuels[0].total == 220.0, "valores numéricos preservados")

        empty = storage.load(Path(tmp) / "novo.json")
        check(isinstance(empty, Document) and not empty.vehicles, "arquivo ausente = novo")

        bad = Path(tmp) / "quebrado.json"
        bad.write_text("{ nao é json", encoding="utf-8")
        try:
            storage.load(bad)
            raise AssertionError("deveria falhar")
        except storage.StorageError:
            check(True, "JSON inválido gera StorageError")


def test_locais():
    print("pastas de dados (raiz escolhida, Documentos e migração)")
    raiz_original = storage.PREFERRED_ROOT
    user_original = os.environ.get("USERPROFILE")
    appdata_original = os.environ.get("APPDATA")

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        docs = base / "Documents"
        docs.mkdir()
        raiz = base / "Programas" / "Controle de Veiculos"
        raiz.mkdir(parents=True)
        os.environ["USERPROFILE"] = str(base)
        os.environ["APPDATA"] = str(base / "AppData")
        try:
            # 1) sem a raiz escolhida, o padrão é Documentos
            storage.PREFERRED_ROOT = base / "outra-raiz-que-nao-existe"
            check(storage.preferred_data_dir() is None, "raiz inexistente é ignorada")
            check(storage.default_path() == docs / storage.APP_DIR_NAME / "dados.json",
                  "sem a raiz, o padrão cai em Documentos")
            check(storage.primeira_execucao(), "primeira abertura detectada")

            # 2) com a raiz, o padrão passa a ser dentro dela
            storage.PREFERRED_ROOT = raiz
            check(storage.default_path() == raiz / storage.APP_DIR_NAME / "dados.json",
                  "padrão usa a raiz escolhida")

            # 3) dado existente no Documentos migra por cópia
            automatica = docs / storage.APP_DIR_NAME
            automatica.mkdir()
            original = automatica / "dados.json"
            original.write_text('{"version": 2, "vehicles": []}', encoding="utf-8")
            destino = raiz / storage.APP_DIR_NAME / "dados.json"
            check(storage.load_last_path() is None, "sem configuração não há arquivo a abrir")
            check(destino.exists(), "dado do Documentos copiado para a raiz")
            check(original.exists(), "cópia: o arquivo do Documentos continua lá")

            # 4) a cadeia inclui a pasta legada ControleKm
            destino.unlink()
            original.unlink()
            legada = docs / storage.LEGACY_APP_DIR_NAME
            legada.mkdir()
            (legada / "dados.json").write_text('{"version": 2, "vehicles": []}',
                                               encoding="utf-8")
            check(storage.load_last_path() is None, "ainda sem configuração")
            check(destino.exists() and (legada / "dados.json").exists(),
                  "dado legado copiado até a raiz, sem apagar o original")

            # 5) depois que o usuário escolhe a pasta, nada migra sozinho
            meu_arquivo = automatica / "dados.json"
            meu_arquivo.write_text('{"version": 2, "vehicles": []}', encoding="utf-8")
            storage.remember_path(meu_arquivo, escolhido=True)
            cfg = json.loads(storage.config_file().read_text(encoding="utf-8"))
            check(cfg["escolhido"] is True, "escolha do usuário registrada")
            check(not storage.primeira_execucao(), "não é mais primeira execução")
            destino.unlink()
            check(storage.load_last_path() == meu_arquivo, "caminho escolhido respeitado")
            check(not destino.exists(), "migração automática não acontece mais")

            # 6) raiz que existe mas não aceita gravação (ex.: Program Files)
            original_gravavel = storage._pasta_gravavel
            storage._pasta_gravavel = lambda p: False
            try:
                storage.PREFERRED_ROOT = raiz
                check(storage.preferred_data_dir() is None,
                      "raiz sem permissão de escrita é ignorada")
                check(storage.data_dir() == docs / storage.APP_DIR_NAME,
                      "sem gravar na raiz, o padrão cai em Documentos")
            finally:
                storage._pasta_gravavel = original_gravavel

            # 7) o teste de gravação é de verdade (cria, grava e apaga)
            arquivo = base / "arquivo.txt"
            arquivo.write_text("x", encoding="utf-8")
            nova = raiz / "nova-subpasta"
            check(storage._pasta_gravavel(nova), "pasta gravável detectada")
            check(not (nova / ".permissao-teste.tmp").exists(),
                  "arquivo de teste apagado depois do teste")
            check(not storage._pasta_gravavel(arquivo / "sub"),
                  "arquivo no meio do caminho não vira pasta")
        finally:
            storage.PREFERRED_ROOT = raiz_original
            if user_original is None:
                os.environ.pop("USERPROFILE", None)
            else:
                os.environ["USERPROFILE"] = user_original
            if appdata_original is None:
                os.environ.pop("APPDATA", None)
            else:
                os.environ["APPDATA"] = appdata_original
    print("  ok: raiz escolhida, Documentos e migração de dados")


def test_ui():
    print("interface")
    from controle_veiculos.ui.app import App

    app = App(ask_folder=False)
    try:
        app.storage_path = Path(tempfile.mkdtemp()) / "dados.json"
        doc = make_doc()
        app.doc = doc
        app.active_vehicle_id = "carro"
        app.refresh()
        app.update_idletasks()
        app.update()

        check(app.current_vehicle().name == "Gol 2019", "veículo ativo carregado")
        check(app.refuels_tab.tree.get_children(), "histórico renderizado")
        check(len(app.vehicles_tab.tree.get_children()) == 2, "lista de veículos renderizada")

        # Aba de manutenções
        check(app.notebook.index(app.maintenance_tab) == 1, "aba Manutenções logo após Abastecimentos")
        linhas = app.maintenance_tab.tree.get_children()
        check(len(linhas) == 2, "histórico de manutenções do veículo renderizado")
        valores = [app.maintenance_tab.tree.item(r)["values"] for r in linhas]
        oleo = [v for v in valores if str(v[2]) == "Troca de óleo"]
        check(oleo and str(oleo[0][6]).startswith("Em 4.000 km"),
              f"coluna Próxima = {oleo[0][6] if oleo else '-'}")

        # Relatórios
        app.reports_tab.refresh()
        app.update()
        check(app.reports_tab.tree.get_children(), "resumo mensal renderizado")
        values = app.reports_tab.tree.item(app.reports_tab.tree.get_children()[0])["values"]
        check(str(values[0]) == "07/2026", f"primeira linha mensal = {values[0]}")
        check(app.reports_tab.cards["maint_count"][0].cget("text") == "2",
              "cartão de manutenções no relatório")
        check(app.reports_tab.cards["total_spent"][0].cget("text").startswith("R$"),
              "cartão de total geral")

        # Mudança de veículo ativo
        app.set_active_vehicle("moto")
        app.update()
        check(app.cmb_vehicle.get() == "Moto", "combo acompanha o veículo ativo")
        check(len(app.refuels_tab.tree.get_children()) == 1, "histórico da moto")

        # Salvamento automático via changed()
        app.doc.vehicles.append(Vehicle(id="novo", name="Teste"))
        app.changed()
        app.update()
        saved = json.loads(app.storage_path.read_text(encoding="utf-8"))
        check(len(saved["vehicles"]) == 3, "changed() grava no arquivo")
        check(app.status_saved.cget("text").startswith("Salvo às"),
              "status mostra o horário da gravação")

        # Janelas de diálogo construídas sem erro
        from controle_veiculos.ui.dialogs import maintenance_dialog, refuel_dialog, vehicle_dialog
        dlg_toplevel_check = (hasattr(refuel_dialog, "__call__")
                              and hasattr(vehicle_dialog, "__call__")
                              and hasattr(maintenance_dialog, "__call__"))
        check(dlg_toplevel_check, "diálogos importáveis")

        app.notebook.select(app.reports_tab)
        app.update()
        check(app.notebook.select() == str(app.reports_tab), "abas selecionáveis")
    finally:
        app.destroy()
    print("  ok: interface criada e destruída sem erros")


def _walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk(child)


def _fill_dialog(app, entry_values, combo_values=None):
    """Abre um diálogo, preenche os campos e clica em Salvar."""
    import tkinter as tk
    from tkinter import ttk as _ttk

    # cancela agendamentos de diálogos anteriores (evita corrida entre testes)
    for timer in getattr(app, "_dialog_timers", []):
        try:
            app.after_cancel(timer)
        except tk.TclError:
            pass
    app._dialog_timers = []
    errors: list[Exception] = app.__dict__.setdefault("_dialog_errors", [])

    def action():
        try:
            tops = [w for w in app.winfo_children() if isinstance(w, tk.Toplevel)]
            if not tops:
                return
            dlg = tops[0]
            found = list(_walk(dlg))
            entries = [
                w for w in found
                if isinstance(w, (tk.Entry, _ttk.Entry))
                and not isinstance(w, _ttk.Combobox)
            ]
            combos = [w for w in found if isinstance(w, _ttk.Combobox)]
            for entry, value in zip(entries, entry_values):
                entry.delete(0, "end")
                entry.insert(0, value)
            for combo, value in zip(combos, combo_values or []):
                combo.set(value)
            buttons = [w for w in found
                       if isinstance(w, _ttk.Button) and w.cget("text") == "Salvar"]
            if buttons:
                buttons[0].invoke()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    def safety_close():
        for w in app.winfo_children():
            if isinstance(w, tk.Toplevel):
                w.destroy()

    app._dialog_timers = [app.after(400, action), app.after(6000, safety_close)]


def test_dialogs():
    print("diálogos")
    import tkinter as tk
    from controle_veiculos.ui.app import App
    from controle_veiculos.ui.dialogs import maintenance_dialog, refuel_dialog, vehicle_dialog

    app = App(ask_folder=False)
    try:
        app.storage_path = Path(tempfile.mkdtemp()) / "dados.json"
        app.doc = make_doc()
        app.active_vehicle_id = "carro"
        app.refresh()

        # 1) abastecimento válido, com total calculado automaticamente
        _fill_dialog(app, ["25/09/2026", "42000", "30", "5,50", "", "Posto Ipiranga", "ok"])
        record = refuel_dialog(app, app.doc, "carro")
        check(not app._dialog_errors, f"sem exceções no diálogo de abastecimento {app._dialog_errors}")
        check(record is not None, "diálogo salva um abastecimento válido")
        if record:
            check(record.date == "2026-09-25" and record.odometer == 42000.0,
                  "data e odômetro interpretados")
            check(abs(record.total - 165.0) < 1e-9, "total calculado (30 x 5,50)")
            check(record.full_tank is True, "tanque cheio marcado por padrão")
            check(record.station == "Posto Ipiranga", "posto preenchido")

        # 2) odômetro menor que o anterior deve ser recusado
        _fill_dialog(app, ["25/09/2026", "100", "30", "5,50", "165", "", ""])
        rejected = refuel_dialog(app, app.doc, "carro")
        check(rejected is None, "odômetro menor que o anterior é recusado")

        # 3) veículo válido
        _fill_dialog(app, ["Uno 2015", "DEF4G56", "2015", "78000"],
                     combo_values=["Flex"])
        vehicle = vehicle_dialog(app)
        check(not app._dialog_errors, f"sem exceções no diálogo de veículo {app._dialog_errors}")
        check(vehicle is not None, "diálogo salva um veículo válido")
        if vehicle:
            check(vehicle.name == "Uno 2015" and vehicle.year == 2015, "nome e ano preenchidos")
            check(vehicle.initial_km == 78000.0, "km inicial interpretado")
            check(vehicle.fuel == "Flex", "combustível selecionado")

        # 4) veículo sem nome deve ser recusado
        _fill_dialog(app, ["", "", "", ""], combo_values=["Gasolina"])
        rejected_vehicle = vehicle_dialog(app)
        check(rejected_vehicle is None, "veículo sem nome é recusado")

        # 5) manutenção válida (data, km, tipo, custo, oficina, próxima)
        _fill_dialog(app, ["25/09/2026", "42000", "250", "Oficina do Zé", "5000",
                           "15/12/2026", "Óleo 5W30 + filtro"],
                     combo_values=["Troca de óleo"])
        manut = maintenance_dialog(app, app.doc, "carro")
        check(not app._dialog_errors, f"sem exceções no diálogo de manutenção {app._dialog_errors}")
        check(manut is not None, "diálogo salva uma manutenção válida")
        if manut:
            check(manut.date == "2026-09-25" and manut.odometer == 42000.0,
                  "data e odômetro da manutenção interpretados")
            check(manut.type == "Troca de óleo" and manut.cost == 250.0,
                  "tipo e custo preenchidos")
            check(manut.shop == "Oficina do Zé", "oficina preenchida")
            check(manut.next_km == 5000.0 and manut.next_date == "2026-12-15",
                  "próxima manutenção (km e data) preenchida")

        # 6) manutenção sem tipo deve ser recusada
        _fill_dialog(app, ["25/09/2026", "42000", "", "", "", "", ""], combo_values=[""])
        rejected_maint = maintenance_dialog(app, app.doc, "carro")
        check(rejected_maint is None, "manutenção sem tipo é recusada")
    finally:
        app.destroy()
    print("  ok: diálogos abrem, validam e fecham")


def test_primeira_abertura():
    print("primeira abertura: pergunta onde gravar os dados")
    from controle_veiculos.ui import app as app_mod
    from controle_veiculos.ui.app import App

    raiz_original = storage.PREFERRED_ROOT
    user_original = os.environ.get("USERPROFILE")
    appdata_original = os.environ.get("APPDATA")
    ask_original = app_mod.filedialog.askdirectory
    info_original = app_mod.messagebox.showinfo

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "Documents").mkdir()
        raiz = base / "Programas" / "Controle de Veiculos"
        raiz.mkdir(parents=True)
        os.environ["USERPROFILE"] = str(base)
        os.environ["APPDATA"] = str(base / "AppData")
        storage.PREFERRED_ROOT = raiz
        pedidos: list[dict] = []
        app = None
        try:
            # ---------------------------------- usuário escolhe uma pasta
            destino = base / "MeusDados"

            def escolher(**kwargs):
                pedidos.append(kwargs)
                return str(destino)

            app_mod.filedialog.askdirectory = escolher
            app_mod.messagebox.showinfo = lambda *_a, **_kw: None

            app = App(ask_folder=True)
            check(app._first_run, "primeira execução é detectada")
            app._ask_data_folder()  # o timer é de 250 ms; disparamos na hora
            check(len(pedidos) == 1, "pasta perguntada ao usuário")
            check(pedidos[0].get("initialdir") == str(raiz / storage.APP_DIR_NAME),
                  f"sugestão inicial = {pedidos[0].get('initialdir')}")
            esperado = destino / "dados.json"
            check(app.storage_path == esperado, "arquivo passa a ser o escolhido")
            check(esperado.exists(), "dados.json criado na pasta escolhida")
            cfg = json.loads(storage.config_file().read_text(encoding="utf-8"))
            check(cfg.get("escolhido") is True, "escolha guardada na configuração")
            check(not storage.primeira_execucao(), "não é mais primeira execução")

            # ------------------------------- segunda abertura: sem pergunta
            app.destroy()
            app = App(ask_folder=True)
            check(not app._first_run, "segunda abertura não agenda a pergunta")
            check(app.storage_path == esperado, "reabre o arquivo escolhido")

            # ------------------------------------------ usuário cancela
            app.destroy()
            app = None
            storage.config_file().unlink()
            pedidos.clear()

            def cancelar(**kwargs):
                pedidos.append(kwargs)
                return ""

            app_mod.filedialog.askdirectory = cancelar
            app = App(ask_folder=True)
            check(app._first_run, "sem configuração volta a ser primeira execução")
            app._ask_data_folder()
            check(len(pedidos) == 1, "pergunta feita (e cancelada)")
            padrao = raiz / storage.APP_DIR_NAME / "dados.json"
            check(app.storage_path == padrao, "cancelar usa a pasta padrão")
            cfg2 = json.loads(storage.config_file().read_text(encoding="utf-8"))
            check("escolhido" not in cfg2 and cfg2.get("last_file"),
                  "padrão lembrado sem marcar escolha")
            check(not storage.primeira_execucao(), "não pergunta de novo")

            app.destroy()
            app = App(ask_folder=True)
            check(not app._first_run, "após cancelar, nenhuma pergunta é agendada")
        finally:
            if app is not None:
                app.destroy()
            app_mod.filedialog.askdirectory = ask_original
            app_mod.messagebox.showinfo = info_original
            storage.PREFERRED_ROOT = raiz_original
            if user_original is None:
                os.environ.pop("USERPROFILE", None)
            else:
                os.environ["USERPROFILE"] = user_original
            if appdata_original is None:
                os.environ.pop("APPDATA", None)
            else:
                os.environ["APPDATA"] = appdata_original
    print("  ok: pasta perguntada na 1ª abertura, escolhida ou cancelada")


def _xlsx_bytes(abas: dict[str, list[list]]) -> bytes:
    """Monta um .xlsx mínimo (zip deflado, strings compartilhadas) para teste."""
    import io
    import zipfile

    shared: list[str] = []
    index: dict[str, int] = {}

    def sid(texto):
        chave = str(texto)
        if chave not in index:
            index[chave] = len(shared)
            shared.append(chave)
        return index[chave]

    folhas, rels = [], []
    for i, (nome, linhas) in enumerate(abas.items(), start=1):
        rows = []
        for n, linha in enumerate(linhas, start=1):
            cells = []
            for j, valor in enumerate(linha):
                col = chr(65 + j)
                if isinstance(valor, (int, float)) and not isinstance(valor, bool):
                    cells.append(f'<c r="{col}{n}"><v>{valor}</v></c>')
                else:
                    cells.append(f'<c r="{col}{n}" t="s"><v>{sid(valor)}</v></c>')
            rows.append(f'<row r="{n}">{"".join(cells)}</row>')
        folhas.append((i, nome,
                       '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                       '<worksheet xmlns="http://schemas.openxmlformats.org/'
                       'spreadsheetml/2006/main"><sheetData>'
                       + "".join(rows) + "</sheetData></worksheet>"))
        rels.append((i, nome))

    tipos = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
             'package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
             '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.'
             'openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
             + "".join(
                 '<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/'
                 'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % i
                 for i, _n, _x in folhas)
             + '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.'
               'openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>')
    raiz = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
            'relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                "<sheets>"
                + "".join(f'<sheet name="{nome}" sheetId="{i}" r:id="rId{i}"/>'
                          for i, nome, _x in folhas)
                + "</sheets></workbook>")
    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
               'relationships">'
               + "".join(
                   '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/'
                   'officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>'
                   % (i, i) for i, _n, _x in folhas)
               + '<Relationship Id="rId99" Type="http://schemas.openxmlformats.org/'
                 'officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
                 "</Relationships>")
    sst = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
           f'count="{len(shared)}" uniqueCount="{len(shared)}">'
           + "".join(f"<si><t>{s}</t></si>" for s in shared) + "</sst>")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", tipos)
        z.writestr("_rels/.rels", raiz)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/sharedStrings.xml", sst)
        for i, _nome, xml in folhas:
            z.writestr(f"xl/worksheets/sheet{i}.xml", xml)
    return buf.getvalue()


CSV_BRASIL = (
    "Posto;Data;Odômetro (km);Litros;Preço por litro;Total;Tanque cheio;Veículo;Observações\r\n"
    'Ipiranga;05/07/2026;41.500;38,00;5,80;220,40;sim;Gol 2019;"Posto Ipiranga; Centro"\r\n'
    "Shell;19/07/2026;41.980;35,50;6,00;213,00;não;;abastecimento parcial\r\n"
    ";;;;0;;;;\r\n"
    "Ipiranga;xx/07/2026;42400;30;5,90;;sim;;data inválida\r\n"
    "Posto Brasil;02/08/2026;42400;32,00;5,70;182,40;1;Fusca 1984;restauração\r\n"
)

CSV_EUA = (
    "Date,Odometer,Liters,Price,Liter,Total,Full tank,Vehicle,Notes,Station\n"
    "2026-07-05,41500,38.00,5.80,5.80,220.40,yes,Gol 2019,first,Shell\n"
    "2026-07-19,41980,35.50,6.00,6.00,213.00,no,Gol 2019,,Shell\n"
)

TSV_SEM_CABECALHO = (
    "05/07/2026\t41500\t38,00\t5,80\t220,40\tsim\t\tprimeiro\r\n"
    "19/07/2026\t41980\t35,50\t6,00\t213,00\tnão\t\t"
)


def test_import():
    print("importação de planilha/CSV")
    from controle_veiculos import importers

    # ---------------------------------------------------------- cabeçalhos
    check(importers.campo_do_cabecalho("Odômetro (km)") == "odometro",
          "cabeçalho 'Odômetro (km)'")
    check(importers.campo_do_cabecalho("Preço por litro") == "preco",
          "cabeçalho 'Preço por litro'")
    check(importers.campo_do_cabecalho("Price per Liter") == "preco",
          "cabeçalho em inglês")
    check(importers.campo_do_cabecalho("Full Tank") == "tanque", "cabeçalho 'Full Tank'")
    check(importers.campo_do_cabecalho("Km inicial") == "kminicial",
          "'Km inicial' não vira odômetro")
    check(importers.campo_do_cabecalho("Qualquer coisa") is None,
          "cabeçalho desconhecido -> None")

    # ------------------------------------------------------------- números
    check(importers.parse_num_any("1.234,56") == 1234.56, "número pt-BR")
    check(importers.parse_num_any("1,234.56") == 1234.56, "número americano")
    check(importers.parse_num_any("41.500") == 41500.0, "milhar brasileiro")
    check(importers.parse_num_any("5.79") == 5.79, "decimal curto")
    check(importers.parse_num_any("abc") is None, "texto -> None")

    # --------------------------------------------------------------- datas
    check(importers.parse_data_any("05/07/2026") == "2026-07-05", "data dd/mm/aaaa")
    check(importers.parse_data_any("2026-07-05") == "2026-07-05", "data ISO")
    check(importers.parse_data_any("31/02/2026") is None, "data impossível -> None")
    serial = (dt.date(2026, 7, 5) - dt.date(1899, 12, 30)).days
    check(importers.parse_data_any(serial) == "2026-07-05", "série do Excel")
    check(importers.parse_bool_any("sim") and importers.parse_bool_any(1)
          and not importers.parse_bool_any("não")
          and not importers.parse_bool_any(""), "sim/não interpretados")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # ------------------------------------------------------- CSV pt-BR
        csv_path = tmp_path / "abastecimentos.csv"
        csv_path.write_bytes(CSV_BRASIL.encode("utf-8-sig"))
        doc, resumo, ign = importers.montar_documento(
            importers.ler_arquivo(csv_path), "Meu veículo")
        nomes = [v.name for v in doc.vehicles]
        check(nomes == ["Gol 2019", "Fusca 1984"], f"veículos do CSV: {nomes}")
        check(len(doc.refuels) == 3, "3 linhas válidas (2 inválidas ignoradas)")
        check(len(ign) == 2, f"2 linhas ignoradas: {ign}")
        gol = next(v for v in doc.vehicles if v.name == "Gol 2019")
        check(gol.initial_km == 41500.0, "km inicial = 1º odômetro")
        primeiro = doc.refuels[0]
        check(primeiro.date == "2026-07-05" and primeiro.odometer == 41500.0,
              "data e odômetro interpretados")
        check(abs(primeiro.total - 220.40) < 1e-9 and primeiro.full_tank,
              "total e 'tanque cheio' lidos")
        check(doc.refuels[1].station == "Shell" and doc.refuels[1].notes
              == "abastecimento parcial", "posto e observações")
        check(doc.refuels[2].vehicle_id != doc.refuels[0].vehicle_id,
              "linha vazia herdou o veículo anterior e a última criou outro")

        # ------------------------------------------------------- CSV em inglês
        us_path = tmp_path / "dados_us.csv"
        us_path.write_text(CSV_EUA, encoding="utf-8")
        doc_us, _resumo, ign_us = importers.montar_documento(
            importers.ler_arquivo(us_path), "Meu veículo")
        check(len(doc_us.refuels) == 2 and not ign_us, "CSV americano lido sem perdas")
        check(doc_us.refuels[0].date == "2026-07-05" and doc_us.refuels[0].price == 5.80,
              "datas ISO e números com ponto")
        check(doc_us.refuels[0].full_tank and not doc_us.refuels[1].full_tank,
              "'yes'/'no' de tanque cheio")

        # ------------------------------------------------------- TSV sem cabeçalho
        tsv_path = tmp_path / "sem_cabecalho.tsv"
        tsv_path.write_bytes(TSV_SEM_CABECALHO.encode("utf-8"))
        doc_tsv, _r, _i = importers.montar_documento(
            importers.ler_arquivo(tsv_path), "Gol 2019")
        check(len(doc_tsv.refuels) == 2, "arquivo sem cabeçalho na ordem padrão")
        check([v.name for v in doc_tsv.vehicles] == ["Gol 2019"],
              "sem coluna de veículo usa o veículo ativo")

        # ------------------------------------------------------------ XLSX
        serial_jun = (dt.date(2026, 6, 10) - dt.date(1899, 12, 30)).days
        xlsx = _xlsx_bytes({
            "Abastecimentos": [
                ["Veículo", "Data", "Odômetro", "Litros", "Preço por litro", "Total",
                 "Tanque cheio", "Posto", "Observações"],
                ["Onix 2021", serial_jun, 50120, 42.5, 5.65, 240.13, "sim", "BR", ""],
                ["Onix 2021", serial_jun + 14, 50590, 39.0, 5.99, 233.61, "no", "Shell", ""],
            ],
            "Veículos": [
                ["Nome", "Placa", "Ano", "Combustível", "Km inicial", "Observações"],
                ["Onix 2021", "ABC1D23", 2021, "Flex", 49800, "carro da família"],
            ],
            "Lembretes": [["Lembrete"], ["trocar o óleo"]],
        })
        xlsx_path = tmp_path / "abastecimentos.xlsx"
        xlsx_path.write_bytes(xlsx)
        planilhas = importers.ler_arquivo(xlsx_path)
        check([nome for nome, _l in planilhas] == ["Abastecimentos", "Veículos", "Lembretes"],
              "3 abas lidas do .xlsx")
        doc_x, resumo_x, ign_x = importers.montar_documento(planilhas, "Meu veículo")
        check(len(doc_x.refuels) == 2 and not ign_x, "linhas do .xlsx importadas")
        onix = doc_x.vehicles[0]
        check(onix.plate == "ABC1D23" and onix.year == 2021 and onix.fuel == "Flex",
              "dados do veículo vindos da aba Veículos")
        check(onix.initial_km == 49800.0, "km inicial da planilha")
        check(doc_x.refuels[0].date == "2026-06-10", "datas seriais convertidas")
        check(any("cabeçalhos não reconhecidos" in a for a in resumo_x["abas"]),
              "aba desconhecida reportada")

        # ------------------------------------------------------------- erros
        vazio = tmp_path / "vazio.csv"
        vazio.write_text("", encoding="utf-8")
        try:
            importers.ler_arquivo(vazio)
            raise AssertionError("arquivo vazio deveria falhar")
        except importers.ImportFileError:
            check(True, "arquivo vazio gera ImportFileError")

        antigo = tmp_path / "antigo.xls"
        antigo.write_bytes(b"\xd0\xcf\x11\xe0")
        try:
            importers.ler_arquivo(antigo)
            raise AssertionError(".xls antigo deveria falhar")
        except importers.ImportFileError as exc:
            check(".xlsx" in str(exc), "orienta a salvar como .xlsx")

        # ------------------------------------------------------------ mesclar
        atual = make_doc()
        alvo = next(v for v in atual.vehicles if v.name == "Gol 2019")
        antes_v, antes_r = len(atual.vehicles), len(atual.refuels)
        contagem = importers.mesclar_documento(doc, atual)
        check(contagem["veiculos"] == 1, "Fusca 1984 criado, Gol 2019 reaproveitado")
        check(len(atual.vehicles) == antes_v + 1, "nenhum veículo duplicado")
        check(contagem["refuels"] == 2 and contagem["duplicados"] == 1,
              "2 abastecimentos novos, o já existente não duplicou")
        check(len(atual.refuels) == antes_r + 2, "histórico somado")
        fusca = next(v for v in atual.vehicles if v.name == "Fusca 1984")
        check(atual.refuels[-1].vehicle_id == fusca.id,
              "linha com veículo novo criou o Fusca")
        check(atual.refuels[-2].vehicle_id == alvo.id,
              "linha sem nome herdou o veículo existente")
        outra = importers.mesclar_documento(doc, atual)
        check(outra["refuels"] == 0 and outra["duplicados"] == 3,
              "segunda importação não duplica")


def _importar(caminho: Path, nome: str):
    """Importa um arquivo .py que não é módulo do pacote (web/, tools/)."""
    import importlib.util

    bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # não deixar __pycache__ em web\ e tools\
    try:
        spec = importlib.util.spec_from_file_location(nome, caminho)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return modulo
    finally:
        sys.dont_write_bytecode = bytecode


def test_conta():
    print("conta local (usuário e senha do login)")
    from controle_veiculos import conta

    appdata_original = os.environ.get("APPDATA")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["APPDATA"] = str(Path(tmp) / "AppData")
        try:
            check(not conta.existe(), "sem conta na primeira vez")
            check(conta.usuario_salvo() == "", "sem usuário salvo")
            check(conta.validar("Maria", "1234") is False, "validar sem conta = False")

            try:
                conta.criar("", "1234")
                raise AssertionError("usuário vazio deveria falhar")
            except conta.ContaError:
                check(True, "usuário vazio gera ContaError")
            try:
                conta.criar("Maria", "12")
                raise AssertionError("senha curta deveria falhar")
            except conta.ContaError:
                check(True, "senha curta gera ContaError")

            conta.criar("Maria", " 1234 ")
            check(conta.existe(), "conta criada")
            check(conta.usuario_salvo() == "Maria", "usuário guardado")
            check(conta.conta_file().exists(), f"arquivo em {conta.conta_file()}")
            bruto = conta.conta_file().read_text(encoding="utf-8")
            check("1234" not in bruto and "hash" in bruto,
                  "a senha não fica no arquivo (só o resumo)")
            check(conta.validar("Maria", "1234"), "senha certa entra (espaços ignorados)")
            check(not conta.validar("maria", "1234"), "usuário diferente é recusado")
            check(not conta.validar("Maria", "9999"), "senha errada é recusada")

            conta.apagar()
            check(not conta.existe(), "apagar() tira só a conta")
            check(not conta.conta_file().exists(), "arquivo da conta removido")
        finally:
            if appdata_original is None:
                os.environ.pop("APPDATA", None)
            else:
                os.environ["APPDATA"] = appdata_original
    print("  ok: conta local criada, validada e reiniciada sem texto puro")


def test_login():
    print("tela de acesso (usuário, senha e 3 modos)")
    from controle_veiculos import conta
    from controle_veiculos.ui.login import MODOS, LoginWindow

    appdata_original = os.environ.get("APPDATA")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["APPDATA"] = str(Path(tmp) / "AppData")
        janela = None
        try:
            check([m[1] for m in MODOS] == ["Aplicativo", "Computador", "Smartphone"],
                  "3 modos: Aplicativo, Computador, Smartphone")

            # primeiro acesso: criação da conta
            janela = LoginWindow()
            janela.update_idletasks()
            janela.update()
            check(janela.modo is None, "nenhum modo escolhido ainda")
            rotulos = [b.cget("text") for b in janela.botoes]
            check(rotulos == ["Aplicativo", "Computador", "Smartphone"],
                  f"botões na tela: {rotulos}")
            janela.e_usuario.insert(0, "Maria")
            janela.e_senha.insert(0, "12")
            check(janela._validar() is False, "senha curta recusada")
            janela.e_senha.delete(0, "end")
            janela.e_senha.insert(0, "abcd")
            janela.e_confirma.insert(0, "abce")
            check(janela._validar() is False, "senhas diferentes recusadas")
            check(not conta.existe(), "com erro, nada é criado")
            janela.e_confirma.delete(0, "end")
            janela.e_confirma.insert(0, "abcd")
            check(janela._validar() is True, "conta criada com usuário e senha")
            check(conta.existe() and conta.usuario_salvo() == "Maria",
                  "conta guardada no APPDATA")
            janela.destroy()
            janela = None

            # reabertura: já existe conta
            janela = LoginWindow()
            janela.update()
            check(not janela._criando, "reabertura detecta a conta existente")
            janela.e_usuario.insert(0, "Maria")
            janela.e_senha.insert(0, "errada")
            check(janela._validar() is False, "senha errada recusada")
            janela.e_senha.delete(0, "end")
            janela.e_senha.insert(0, "abcd")
            check(janela._validar() is True, "senha certa entra")
            janela.e_usuario.delete(0, "end")
            janela.e_usuario.insert(0, "Outra")
            check(janela._validar() is False, "usuário de outra conta recusado")

            # reinício ("esqueci a senha") apaga só a conta
            conta.apagar()
            check(not conta.existe(), "reinício apaga a conta, não os dados")
        finally:
            if janela is not None:
                janela.destroy()
            if appdata_original is None:
                os.environ.pop("APPDATA", None)
            else:
                os.environ["APPDATA"] = appdata_original
    print("  ok: login valida, cria conta e mostra os 3 modos")


def test_ajuda():
    print("ajuda: manual em texto e botões")
    from tkinter import ttk

    from controle_veiculos import caminhos

    raiz = Path(__file__).resolve().parents[1]
    manual = caminhos.caminho_manual()
    check(manual is not None and manual.exists(),
          f"manual encontrado: {manual.name if manual else None}")
    check(manual.suffix in (".txt", ".md"), "é um arquivo de manual")
    check(caminhos.pasta_web().exists(), "pasta web\\ localizada")
    check(caminhos.URL_LOCAL.startswith("http://127.0.0.1:8000/"),
          f"endereço da versão web = {caminhos.URL_LOCAL}")
    check(caminhos.servidor_disponivel(), "Servidor Wi-Fi.bat encontrado")

    for nome in ("INSTALAR-COMO-USAR.txt", "README.txt"):
        for pasta, rotulo in ((raiz, "raiz"), (raiz / "web", "web")):
            arquivo = pasta / nome
            check(arquivo.exists(), f"{rotulo}\\{nome} existe")
            texto = arquivo.read_text(encoding="utf-8")
            check(len(texto) > 800, f"{rotulo}\\{nome} tem conteúdo")
            dados = arquivo.read_bytes()
            check(b"\r\n" in dados and b"\n" not in dados.replace(b"\r\n", b""),
                  f"{rotulo}\\{nome} com final de linha CRLF")

    # o App: botão Ajuda na barra + item no menu
    from controle_veiculos.ui.app import App

    app = App(ask_folder=False)
    try:
        app.storage_path = Path(tempfile.mkdtemp()) / "dados.json"
        app.update()
        botoes = [w.cget("text") for w in _walk(app)
                  if isinstance(w, ttk.Button) and w.cget("text") == "Ajuda"]
        check(len(botoes) == 1, "botão Ajuda na barra de ferramentas")
        check(callable(app.abrir_manual), "método abrir_manual existe")
        barra = app.nametowidget(app.cget("menu"))
        idx = barra.index("Ajuda")
        menu = barra.nametowidget(barra.entrycget(idx, "menu"))
        # entrycget no Tkinter quer a opção sem hífen; só "command" tem rótulo
        rotulos = [menu.entrycget(k, "label")
                   for k in range((menu.index("end") or 0) + 1)
                   if menu.type(k) == "command"]
        check(any("Manual completo" in r for r in rotulos),
              "item 'Manual completo' no menu Ajuda")
    finally:
        app.destroy()
    print("  ok: manual em texto encontrado e botões de ajuda no lugar")


def test_manuais_txt():
    print("manuais convertidos de .md para .txt")
    raiz = Path(__file__).resolve().parents[1]
    md_para_txt = _importar(raiz / "tools" / "md_para_txt.py", "md_para_txt")

    md = ("# Título\n\nTexto **forte**, `codigo` e [link](#ancora).\n\n"
          "![foto do carro](imagens/x.png)\n\n"
          "> citação\n\n1. passo um\n\n- item\n\n```\ncodigo cru\n```\n\n"
          "| Coluna | Obs |\n| --- | --- |\n| um | dois com uma coluna bem longa "
          "para ver se quebra em varias linhas |\n")
    txt = md_para_txt.md_para_txt(md)
    linhas = txt.splitlines()
    check(linhas[0] == "Título", "título vira texto simples")
    check("====" in txt, "sublinhado do título")
    check("forte" in txt and "**" not in txt, "negrito sem asteriscos")
    check('"codigo"' in txt, "código entre aspas")
    check("[foto: foto do carro]" in txt, "foto marcada como [foto: ...]")
    check("link" in txt and "#ancora" not in txt, "âncora vira só o texto")
    linha_cit = [l for l in linhas if "citação" in l]
    check(bool(linha_cit) and linha_cit[0].startswith("    "),
          "citação indentada com 4 espaços")
    check("codigo cru" in txt, "bloco de código preservado")
    check("1. passo um" in txt and "- item" in txt, "listas preservadas")
    check(any(l.startswith("--") for l in linhas), "linha de traços da tabela")
    check(any(l.startswith("Coluna") and "Obs" in l for l in linhas),
          "cabeçalho da tabela")
    check("uma coluna bem longa" in txt, "tabela com célula longa")
    larguras = [len(l) for l in linhas if l.strip()]
    check(max(larguras) <= md_para_txt.LARGURA_MAX + 4,
          f"linhas da tabela até {md_para_txt.LARGURA_MAX} colunas")

    # os arquivos gerados estão atualizados em relação aos .md
    for nome_md, nome_txt in [("INSTALAR-COMO-USAR.md", "INSTALAR-COMO-USAR.txt"),
                              ("README.md", "README.txt")]:
        mtime_md = (raiz / nome_md).stat().st_mtime
        for pasta, rotulo in ((raiz, "raiz"), (raiz / "web", "web")):
            arquivo = pasta / nome_txt
            check(arquivo.exists(), f"{rotulo}\\{nome_txt} gerado")
            check(arquivo.stat().st_mtime >= mtime_md - 1,
                  f"{rotulo}\\{nome_txt} mais novo que o {nome_md}")
            texto = arquivo.read_text(encoding="utf-8")
            check("**" not in texto,
                  f"{rotulo}\\{nome_txt} sem marcação de negrito sobrando")
            longas = [l for l in texto.splitlines() if len(l) > 110]
            check(not longas, f"{rotulo}\\{nome_txt} sem linhas gigantes")

    # todas as fotos citadas nos guias existem mesmo
    import re

    for nome_md in ("INSTALAR-COMO-USAR.md", "README.md"):
        alvo = (raiz / nome_md).read_text(encoding="utf-8")
        for foto in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", alvo):
            if foto.startswith(("http://", "https://")):
                continue
            check((raiz / foto).exists(), f"{nome_md} cita {foto} e ela existe")

    # nenhum arquivo de texto do projeto guarda o caminho da máquina de quem fez
    proibidos = ["2026" + "-09-Veiculos", "D" + ":\\" + "Projetos",
                 "D" + ":/" + "Projetos"]
    pula_dirs = {".git", "build", "dist", "ControleVeiculos", "ControleKm",
                 "__pycache__", ".venv", "venv"}
    pula_ext = {".png", ".jpg", ".jpeg", ".ico", ".exe", ".pyc", ".lnk"}
    achados = []
    for arquivo in raiz.rglob("*"):
        if not arquivo.is_file() or arquivo.suffix.lower() in pula_ext:
            continue
        if pula_dirs & set(arquivo.relative_to(raiz).parts):
            continue
        corpo = arquivo.read_text(encoding="utf-8", errors="ignore")
        if any(p in corpo for p in proibidos):
            achados.append(str(arquivo.relative_to(raiz)))
    check(not achados, f"nenhum arquivo de texto com caminho pessoal ({achados})")


def test_servidor():
    print("servidor da versão web e sincronização")
    import threading
    import urllib.error
    import urllib.request

    raiz = Path(__file__).resolve().parents[1]
    servidor = _importar(raiz / "web" / "servidor.py", "servidor_web")

    def lancamento(ident, data, litros=10.0, **extra):
        reg = {"id": ident, "vehicle_id": "v1", "date": data, "odometer": 40000,
               "liters": litros, "price": 5.5, "total": 55, "full_tank": True,
               "station": "", "notes": ""}
        reg.update(extra)
        return reg

    r1 = lancamento("r1", "2026-09-01")
    vazio = {"version": 2, "vehicles": [], "refuels": [], "maintenances": []}

    # a) lançamento novo do celular entra no PC
    res, est = servidor.mesclar({}, dict(vazio, refuels=[r1]),
                                dict(vazio, refuels=[r1, lancamento("r2", "2026-09-20")]))
    check(len(res["refuels"]) == 2 and est["novos_celular"] == 1,
          "novo lançamento do celular soma no PC")

    # b) apagado no celular (com cópia da última sync) sai do PC
    res, est = servidor.mesclar(dict(vazio, refuels=[r1]),
                                dict(vazio, refuels=[r1]), vazio)
    check(res["refuels"] == [] and est["removidos"] == 1,
          "exclusão do celular propaga para o PC")

    # c) celular novo (sem cópia anterior) não apaga nada do PC
    res, est = servidor.mesclar(None, dict(vazio, refuels=[r1]), vazio)
    check(len(res["refuels"]) == 1 and est["removidos"] == 0,
          "celular sem histórico não apaga dados do PC")

    # d) edição só de um lado vale; dos dois lados, vence a data mais recente
    res, _e = servidor.mesclar(dict(vazio, refuels=[r1]), dict(vazio, refuels=[r1]),
                               dict(vazio, refuels=[dict(r1, liters=12.0)]))
    check(res["refuels"][0]["liters"] == 12.0, "edição só do celular vale")
    res, est = servidor.mesclar(dict(vazio, refuels=[r1]),
                                dict(vazio, refuels=[dict(r1, date="2026-09-30")]),
                                dict(vazio, refuels=[dict(r1, date="2026-09-15")]))
    check(res["refuels"][0]["date"] == "2026-09-30" and est["conflitos"] == 1,
          "conflito: data mais recente vence (empate fica o PC)")

    # e) veículo: o PC vale; o celular só completa o que faltar
    res, _e = servidor.mesclar(
        {}, {"version": 2, "vehicles": [{"id": "v1", "name": "Gol", "plate": "",
                                         "notes": ""}], "refuels": [], "maintenances": []},
        {"version": 2, "vehicles": [{"id": "v1", "name": "Gol", "plate": "ABC1D23",
                                     "notes": "x"}], "refuels": [], "maintenances": []})
    check(res["vehicles"][0]["plate"] == "ABC1D23" and res["vehicles"][0]["name"] == "Gol",
          "veículo: vale o do PC e o celular completa o vazio")

    # f) registros sem id são ignorados
    res, _e = servidor.mesclar(
        {}, {"version": 2, "vehicles": [{"name": "sem id"}], "refuels": [],
             "maintenances": []}, vazio)
    check(res["vehicles"] == [], "registro sem id é descartado")

    # g) arquivo: gravação atômica e leitura de JSON quebrado
    with tempfile.TemporaryDirectory() as tmp:
        arquivo = Path(tmp) / "dados.json"
        servidor.salvar_documento(arquivo, vazio)
        check(arquivo.exists() and not arquivo.with_name("dados.json.tmp").exists(),
              "gravação atômica sem resíduo")
        arquivo.write_text("{ quebrado", encoding="utf-8")
        try:
            servidor.ler_documento(arquivo)
            raise AssertionError("deveria falhar")
        except ValueError:
            check(True, "JSON quebrado gera ValueError (não é sobrescrito)")

        # --------------------------------------------- ponta a ponta (HTTP)
        # Coleta primeiro, na thread principal: as janelas anteriores deixaram
        # objetos do Tk no lixo e o Tk só pode ser finalizado aqui (se o GC
        # rodar dentro do thread HTTP, o Tk encerra o processo).
        import gc

        gc.collect()
        os.environ["CONTROLE_VEICULOS_DADOS"] = str(arquivo)
        arquivo.unlink()
        httpd = servidor.ThreadingHTTPServer(("127.0.0.1", 0), servidor.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{httpd.server_address[1]}"
        try:
            r = json.load(urllib.request.urlopen(url + "/__sync", timeout=15))
            check(r["ok"] and r["dados"] is None, "GET /__sync sem arquivo = null")

            with urllib.request.urlopen(url + "/", timeout=15) as pagina:
                conteudo = pagina.read().decode("utf-8")
            check("login-root" in conteudo, "GET / serve a página com a tela de acesso")
            with urllib.request.urlopen(url + "/INSTALAR-COMO-USAR.txt", timeout=15) as man:
                check(man.status == 200, "manual em texto servido pelo servidor")

            payload = json.dumps({"base": None, "dados": dict(
                vazio, refuels=[lancamento("novo", "2026-09-25")])}).encode("utf-8")
            req = urllib.request.Request(url + "/__sync", data=payload,
                                         headers={"Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=15))
            check(r["ok"] and r["estat"]["novos_celular"] == 1,
                  "POST /__sync registra o lançamento novo")
            gravado = json.loads(arquivo.read_text(encoding="utf-8"))
            check(len(gravado["refuels"]) == 1, "resultado gravado no dados.json")

            # arquivo corrompido: recusa e preserva
            arquivo.write_text("{ quebrado", encoding="utf-8")
            req = urllib.request.Request(url + "/__sync", data=payload,
                                         headers={"Content-Type": "application/json"})
            try:
                urllib.request.urlopen(req, timeout=15)
                raise AssertionError("deveria recusar")
            except urllib.error.HTTPError as exc:
                check(exc.code == 500, "arquivo quebrado recusa a sincronização")
            check(arquivo.read_text(encoding="utf-8") == "{ quebrado",
                  "arquivo quebrado não é sobrescrito")
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=15)
            os.environ.pop("CONTROLE_VEICULOS_DADOS", None)
    print("  ok: servidor serve a página, sincroniza e protege o arquivo")


def test_web_e_bat():
    print("página web, bats e instalador")
    raiz = Path(__file__).resolve().parents[1]
    html = (raiz / "web" / "controle-veiculos.html").read_text(encoding="utf-8")
    for marca in ('id="login-root"', 'id="login-form"', 'id="btn-sync"',
                  'id="btn-ajuda"', 'id="btn-sair"', 'id="btn-manual"',
                  'LS_SYNC', 'pbkdf2', 'INSTALAR-COMO-USAR.txt', 'Repita a senha',
                  'Esqueci a senha', 'Sincronizar com o PC'):
        check(marca in html, f"página tem {marca}")
    check(html.count("<script") == html.count("</script>"), "<script> balanceado")
    check(html.count("<div") == html.count("</div>"), "<div> balanceado")

    bat = (raiz / "web" / "Servidor Wi-Fi.bat").read_bytes()
    check(max(bat) < 128, "Servidor Wi-Fi.bat só com caracteres ASCII")
    check(b"\r\n" in bat and b"\n" not in bat.replace(b"\r\n", b""),
          "Servidor Wi-Fi.bat com final de linha CRLF")
    texto = bat.decode("ascii")
    check("servidor.py" in texto, "bat chama o servidor com sincronização")
    check("http.server" in texto, "bat tem o servidor simples como reserva")
    check("servidor-wifi.ps1" in texto, "bat cai para o PowerShell sem Python")
    check("chcp 65001" in texto, "bat prepara o console para acentos")

    codigo = (raiz / "web" / "servidor.py").read_text(encoding="utf-8")
    check("from http.server import" in codigo and "ThreadingHTTPServer" in codigo,
          "servidor.py usa só a biblioteca padrão do Python")
    check('"/__sync"' in codigo, "servidor.py expõe /__sync")
    check("_pasta_gravavel" in codigo,
          "servidor escolhe pasta onde dá para gravar (Program Files)")

    # Instalar.bat da raiz (o instalador oficial do pacote)
    instalar = (raiz / "Instalar.bat").read_bytes()
    check(max(instalar) < 128, "Instalar.bat só com caracteres ASCII")
    check(b"\r\n" in instalar and b"\n" not in instalar.replace(b"\r\n", b""),
          "Instalar.bat com final de linha CRLF")
    tbat = instalar.decode("ascii")
    check("instalar.ps1" in tbat, "Instalar.bat chama o instalador do PowerShell")
    check("title Instalar" in tbat, "Instalar.bat dá título à janela (a foto usa ele)")

    # instalar.ps1: pasta padrão do Windows, atualização e sintaxe
    ps1 = (raiz / "tools" / "instalar.ps1").read_text(encoding="utf-8-sig")
    for marca in ("PastaBaseWindows", "ENTER ja instala na pasta padrao do Windows",
                  "HKCU:\\Software\\Controle de Veiculos", "InstallDir",
                  "Remover-VersaoAntiga", "RunAs",
                  "Documentos\\ControleVeiculos"):
        check(marca in ps1, f"instalador tem {marca}")
    comando = ("$t = Get-Content -LiteralPath $env:INSTALAR_PS1 -Raw; "
               "[void][scriptblock]::Create($t)")
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", comando],
        capture_output=True, text=True, errors="replace", timeout=90,
        env={**os.environ, "INSTALAR_PS1": str(raiz / "tools" / "instalar.ps1")},
    )
    check(proc.returncode == 0,
          f"instalar.ps1 sem erro de sintaxe ({proc.stderr.strip()[:160]})")


def main():
    tests = [test_format, test_segments, test_report, test_maintenance, test_storage,
             test_locais, test_import, test_ui, test_dialogs, test_primeira_abertura,
             test_conta, test_login, test_ajuda, test_manuais_txt, test_servidor,
             test_web_e_bat]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  FALHOU: {exc}")
    print("-" * 60)
    print(f"{len(tests) - failures}/{len(tests)} grupos passaram")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
