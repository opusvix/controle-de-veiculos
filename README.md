# Controle de Veículos

![Ícone do Controle de Veículos](imagens/icone.png)

Programa de **Windows** para registrar **abastecimentos**, lançar **manutenções**
(com lembrete da próxima revisão) e ver quanto o carro/moto está custando nos
**relatórios**. Existe também a versão para **celular pelo Wi-Fi**.

Tudo fica **só no seu computador**, num arquivo que você escolhe — sem servidor
na nuvem, sem cadastro, sem internet. Cada aparelho tem uma **tranca local**
(usuário e senha guardados só ali) e, se você quiser, o PC e o celular podem
**sincronizar entre si** pela rede Wi-Fi da casa — os dados não passam pela
internet nem por serviço de terceiros.

> **Não é da área de tecnologia?** O passo a passo com fotos está em
> [`INSTALAR-COMO-USAR.md`](INSTALAR-COMO-USAR.md). Este README é a visão geral
> (e a parte técnica, no final). Em qualquer tela há um botão de **Ajuda**
> que abre esses mesmos guias em `.txt`.

## Como abrir

- **Pelo instalador (recomendado):** dois cliques em **`Instalar.bat`** — ele pergunta
  em qual pasta instalar e cria o atalho **Controle de Veículos** na Área de Trabalho.
- **Direto:** dois cliques no atalho da Área de Trabalho ou em
  `dist\Controle de Veículos.exe` (arquivo único de ~12 MB, funciona em qualquer
  Windows 10/11 **sem instalar nada**; também roda de um pendrive).
- **Pelo código-fonte:** `python main.py` ou duplo clique em `Controle de Veículos.bat`
  (precisa de Python 3).

Na **primeira abertura** o programa pergunta **onde gravar os dados** (padrão:
`C:\Programas\Controle de Veiculos\ControleVeiculos`) e em seguida abre a tela de
acesso: crie um **usuário** e uma **senha** (mínimo 4 caracteres) e escolha a
forma de trabalho — **Aplicativo** (a janela), **Computador** (a versão no
navegador) ou **Smartphone** (liga o endereço para o celular). Nas próximas
aberturas bastam usuário e senha; quem esquecer usa **Esqueci a senha** (isso
reinicia só a tranca, os dados ficam). Ele usa só a biblioteca padrão do Python
(Tkinter), sem nada extra.

## O que ele faz

| Aba | Função |
| --- | --- |
| **Abastecimentos** | Formulário rápido (data, odômetro, litros, preço/L, total automático, posto, tanque cheio) + histórico com distância, km/L e R$/km de cada parada. Editar/excluir pelo menu do botão direito. |
| **Manutenções** | Data, quilometragem, tipo de serviço (lista pronta + texto livre), serviços executados, custo, oficina/local, observações e a **próxima manutenção** por km ou por data. Avisos: atrasada, próxima ou em dia. |
| **Relatórios** | Filtro por período e por veículo, **12 indicadores** (km, litros, gasto com combustível, gasto com manutenção, total geral, custo por km...), gráfico com **5 indicadores** e resumo mês a mês. |
| **Veículos** | Cadastro de vários carros/motos (nome, placa, ano, combustível, km inicial). O veículo "ativo" é usado no lançamento e nos relatórios. |

Extras: salvamento automático a cada alteração (Ctrl+S salva na mão),
`Arquivo > Salvar como...` para mover os dados, `Arquivo > Abrir...` para carregar
outra cópia, `Arquivo > Importar planilha/CSV...` (Ctrl+I) e o app lembra o último
arquivo usado.

## Onde ficam os dados

Padrão: `C:\Programas\Controle de Veiculos\ControleVeiculos\dados.json`. É um arquivo de
texto — pode ser copiado ou levado para outro computador (backup = copiar esse arquivo
ou a pasta inteira). Se essa pasta não existe mais, o programa cai sozinho para
`Documentos\ControleVeiculos\dados.json`.

- A pasta escolhida é lembrada numa minúscula configuração em
  `%APPDATA%\ControleVeiculos\config.json`; os dados em si ficam **só** na pasta
  escolhida por você.
- Quem já usou as versões anteriores não perde nada: os dados são **copiados**
  automaticamente (nunca movidos) e as pastas antigas ficam intactas como cópia
  de segurança. Os detalhes estão em [Armazenamento](#armazenamento).

## No celular

`web\controle-veiculos.html` é a **mesma ferramenta em um único arquivo** HTML/JS —
sem instalação e sem internet, com barra de botões no rodapé e os mesmos cálculos
(inclusive manutenções e lembretes). Os dados ficam no próprio aparelho.

1. **No PC:** dois cliques em `web\Servidor Wi-Fi.bat`. Ele mostra um endereço tipo
   `http://192.168.1.5:8000/controle-veiculos.html`.
2. **No celular:** na mesma rede Wi-Fi, digite esse endereço no navegador e use
   *Adicionar à tela de início*. Na primeira vez, crie o **usuário e a senha**
   daquele aparelho (a tela de acesso é local, uma por aparelho).
3. **Sincronizar:** na aba **Dados**, o botão **Sincronizar com o PC** junta os
   dados dos dois lados (só funciona com o PC ligado, o `.bat` aberto e na mesma
   rede). Ver [Sincronizar](#sincronizar-pc--celular-pela-rede).
4. Funciona **com ou sem Python**: se não houver Python, o servidor cai para
   `web\servidor-wifi.ps1` (PowerShell que já vem com o Windows). Nada é instalado —
   mas nesse modo (e no modo `file://`, com duplo clique no HTML) o **Sincronizar**
   fica de fora, porque ele precisa do `web\servidor.py`.

Passo a passo com fotos: [`INSTALAR-COMO-USAR.md`](INSTALAR-COMO-USAR.md) (Parte 7).

---

# Parte técnica

## Manutenções e o lembrete da próxima revisão

- Cada serviço guarda: data, odômetro, tipo, serviços executados, custo, oficina,
  observações e, se você quiser, o intervalo da próxima revisão:
  **"Repetir a cada X km"** e/ou **"Próxima em data"**.
- O aviso considera só o **registro mais recente de cada tipo** (lançar um serviço
  novo fecha o lembrete do anterior) e aparece na aba Manutenções, na dica do
  formulário e num selo no botão da navegação (versão web).
- Status: **atrasada** quando falta 0 km/0 dias, **próxima** quando restam
  até 500 km (ou 10% do intervalo) ou até 30 dias, senão **em dia**.
- Os custos de manutenção entram **em linha própria** nos relatórios (cartões,
  coluna "Manutenção" do resumo mensal, "Total geral" e no gráfico).

## Como o consumo é calculado

- **km/L por abastecimento** = distância desde o **último tanque cheio** ÷ litros
  abastecidos nesse trecho (litros somados entre as duas paradas com tanque cheio).
- Valores sem referência de tanque cheio saem com **`~`** (aproximados). Marque
  "Tanque cheio" sempre que encher o tanque para ter números exatos.
- **R$/km** = valor gasto no trecho ÷ distância.
- **No resumo do período**: km rodados ÷ litros abastecidos (as distâncias são
  atribuídas ao mês/parada em que foram registradas).

## Armazenamento

- Gravação atômica (arquivo temporário + troca), então um desligamento repentino não
  corrompe os dados. Se um arquivo chegar corrompido, o app oferece renomeá-lo (nada é
  apagado) e seguir.
- A pasta preferida vem de `storage.PREFERRED_ROOT`, que aponta para a **pasta do programa**
  (raiz do repositório no código-fonte, pasta do `.exe` no exe); se ela não existir,
  o programa usa `Documentos\ControleVeiculos`.
- Migração em cadeia **sempre por cópia**, na ordem
  `Documentos\ControleKm` → `Documentos\ControleVeiculos` →
  `<pasta do programa>\ControleVeiculos`, com uma guarda (`escolhido`) que
  faz o programa parar de migrar assim que você escolhe a pasta na mão.
- `App(ask_folder=True)` ativa a pergunta da pasta na primeira abertura
  (`storage.primeira_execucao()`).

## Tela de acesso (conta local)

- `controle_veiculos/conta.py` cria, valida e apaga a conta local em
  `%APPDATA%\ControleVeiculos\conta.json`, no formato
  `{"usuario", "sal", "hash", "iteracoes"}` (compatível com o lado web).
- A senha nunca é guardada em texto: **PBKDF2-HMAC-SHA256** com sal aleatório —
  **200 000 iterações** no desktop; no navegador **150 000** via `crypto.subtle`
  (só existe em `localhost`/HTTPS) com queda para um PBKDF2 em JS puro a
  **40 000** iterações quando a página está em `http://192.168.x.x` (contexto não
  seguro: `crypto.subtle` não existe lá).
- `controle_veiculos/ui/login.py` (`LoginWindow`) é a tela: **Usuário**, **Senha**,
  **Repita a senha** (só no 1º acesso) e os três modos Aplicativo, Computador e
  Smartphone (Enter ou F1 = Aplicativo). **Esqueci a senha** reinicia só a conta
  (`conta.apagar()`), nunca os dados.
- Na versão web a tela é um overlay que cobre a página (`#login-root`); o estado fica
  em `controlekm.conta` no `localStorage` e a página só aparece depois de entrar
  (`logado = true`), com o usuário já preenchido quando a conta existe.
- Cada aparelho/navegador tem a **sua própria** conta — é tranca local, não sincroniza.

## Sincronizar (PC ↔ celular pela rede)

- O botão **Sincronizar com o PC** (aba Dados) chama `POST /__sync` do
  `web\servidor.py` com `{base, dados}`; `base` é o snapshot salvo em
  `controlekm.sincronizacao` — é ele que permite a **junção em 3 vias**.
- Regras da junção: registro **novo** soma dos dois lados; **exclusão** só propaga
  se existir na base (quem nunca sincronizou nunca perde nada); **conflito**
  (editado dos dois lados) fica com a **data mais recente**, no empate o **PC**
  vence; **veículo** vale o do PC e o celular só completa campos vazios.
- `web\servidor.py` é standalone (não importa o pacote) e usa só a biblioteca
  padrão: serve os arquivos estáticos e `/__sync`, com trava (`TRAVA`) contra
  syncs simultâneos, gravação atômica e **recusa** de gravar quando o
  `dados.json` está corrompido (HTTP 500, arquivo intocado). Porta 8000, sem
  headers CORS (mesma origem). `CONTROLE_VEICULOS_DADOS` sobrescreve o caminho do
  arquivo — é o que os testes usam.
- `web\Servidor Wi-Fi.bat` chama `python servidor.py` e, se falhar, cai para
  `python -m http.server 8000` (aí **sem** `/__sync`) e, sem Python, para o
  `servidor-wifi.ps1`. A página só mostra o botão quando `/__sync` responde; se não
  responder, esconde o botão e mostra a dica do que fazer.
- No navegador, **toda** substituição total do `store` limpa o snapshot de sync
  (`limparBaseSync()`), para um sync futuro nunca apagar o que o PC acabou de gravar.

## Ajuda (botões e manuais em `.txt`)

- Desktop: botão **Ajuda** na barra de ferramentas e **Ajuda → Manual completo**
  (mais *Como o consumo é calculado* e *Formato das colunas*), abrindo o `.txt` com
  o programa padrão (`caminhos.abrir_manual()`).
- Web: botão **?** no topo, **Abrir o manual (texto)** na aba Dados e o link da tela
  de acesso — abrem um modal com o texto do `INSTALAR-COMO-USAR.txt`, com queda
  para `window.open` se o `fetch` falhar (ex.: página aberta em `file://`).
- Os `.txt` são **gerados** a partir dos `.md`: `python tools\md_para_txt.py`
  (UTF-8 + CRLF), escritos na raiz **e** copiados para `web\` (o celular abre pelo
  servidor). Sempre que mexer nos `.md`, rode o script de novo — os testes cobram
  que o `.txt` não fique velho.

## Importar de uma planilha (CSV, TSV ou XLSX)

Já tem os abastecimentos numa planilha? Traga tudo de uma vez:

- **App desktop:** `Arquivo > Importar planilha/CSV...` (ou **Ctrl+I**).
- **Versão web:** aba *Dados > Importar planilha/CSV* (com *Baixar modelo .csv*).

As duas versões leem `.csv`, `.tsv`, `.txt` e `.xlsx` (até 2 abas) e reconhecem o
**nome do cabeçalho** — em português ou inglês —, então a ordem das colunas não
importa. O separador (`;`, `,`, aba do Excel ou `|`) é detectado sozinho e as aspas
do Excel são respeitadas. O `.xlsx` é lido sem biblioteca nenhuma (zip + XML).

**Colunas da tabela de abastecimentos**

| Coluna | Obrigatória | Exemplo | Observação |
| --- | --- | --- | --- |
| Veículo | não | Gol 2019 | Nome inexistente cria o veículo; vazio repete a linha anterior |
| Data | **sim** | 05/07/2026 | `dd/mm/aaaa`, `aaaa-mm-dd` ou data do Excel |
| Odômetro (km) | **sim** | 41.500 | quilômetros totais do veículo na parada |
| Litros | **sim** | 38,00 | quantidade abastecida |
| Preço por litro | **sim** | 5,80 | dá para preencher só o Total |
| Total | não | 220,40 | vazio = litros × preço |
| Tanque cheio | não | sim | `sim/não`, `1/0`, `x`; vazio = não |
| Posto | não | Shell | livre |
| Observações | não | troca de óleo | livre |

**Colunas da aba "Veículos" (só no `.xlsx`):** Nome, Placa, Ano, Combustível,
Km inicial e Observações — completam placa/ano/combustível dos abastecimentos que
tiverem o mesmo nome de veículo.

Observações:

- A planilha não traz manutenções: na opção **substituir**, as manutenções já
  lançadas são **mantidas** e religadas ao veículo de mesmo nome (e a mensagem
  diz quantas ficaram).
- Sem cabeçalho a ordem padrão é: Data; Odômetro; Litros; Preço por litro; Total;
  Tanque cheio; Posto; Observações (usa o veículo ativo como nome).
- Números aceitam formato brasileiro (`1.234,56`) e americano (`1,234.56`).
- Se já houver dados você escolhe **mesclar** (junta, sem duplicar) ou
  **substituir**; as linhas inválidas são listadas na mensagem, nada é apagado às cegas.
- O formato antigo `.xls` não é lido: no Excel use *Salvar como → .xlsx* ou *.csv*.
- Arquivos `.json` continuam sendo abertos por `Arquivo > Abrir...`.
- A relação completa também está dentro do app:
  `Ajuda > Formato das colunas (importação)`.

## Detalhes da versão web

- `web\controle-veiculos.html` é um arquivo único (HTML + JS), sem dependências
  externas, responsivo (360 px a 1440 px), com modo claro/escuro.
- **Chrome/Edge no PC:** em *Dados > Conectar ao dados.json*, dá para apontar para o
  mesmo arquivo do app desktop — depois da primeira permissão, cada alteração é gravada
  nele automaticamente. O navegador não deixa uma página gravar sozinha em pastas
  quaisquer (regra de segurança), por isso no celular o caminho é
  *Baixar dados.json* / *Importar dados.json*.
- Chaves internas do navegador (`controlekm.*` no `localStorage`) são mantidas de
  propósito, para não quebrar instalações antigas.
- Tela de acesso, ajuda e sincronização têm seções próprias:
  [conta local](#tela-de-acesso-conta-local),
  [sincronizar](#sincronizar-pc--celular-pela-rede) e
  [ajuda](#ajuda-botões-e-manuais-em-txt).

## Estrutura do projeto

```
controle-de-veiculos/        # raiz do projeto (github.com/opusvix/controle-de-veiculos)
├── main.py                  # ponto de entrada
├── Instalar.bat             # instalação: pergunta a pasta e cria o atalho
├── Controle de Veículos.bat # lançador pelo código-fonte
├── README.md                # este arquivo
├── README.txt               # o mesmo texto gerado em .txt (Bloco de Notas)
├── INSTALAR-COMO-USAR.md    # manual do usuário (com fotos)
├── INSTALAR-COMO-USAR.txt   # manual em texto puro (é o que o botão Ajuda abre)
├── imagens/                 # fotos usadas nos manuais
│   ├── icone.png            # ícone
│   ├── 01-instalar.png      # janela do instalador
│   ├── 02-pasta-dados.png   # pergunta da pasta na 1ª abertura
│   ├── 03..06 *.png         # as 4 abas do programa
│   ├── 07-servidor-wifi.png # janela preta do servidor
│   ├── 08-celular.png       # versão web no celular
│   └── 09-tela-acesso.png   # tela de acesso (usuário, senha e 3 modos)
├── dist/
│   └── Controle de Veículos.exe   # executável standalone (gerado)
├── assets/
│   ├── controle_veiculos.ico # ícone (mostrador) gerado por tools/make_icon.py
│   └── preview.png          # prévia do ícone
├── tools/
│   ├── instalar.ps1         # cópia (exe, web\, imagens\, *.md, *.txt) + atalho
│   ├── md_para_txt.py       # gera os .txt a partir dos .md (raiz e web\)
│   ├── capturas.py          # gera as fotos de imagens/ (usa Pillow só aqui)
│   ├── make_icon.py         # gera o .ico (sem dependências)
│   └── file_version_info.txt # versão/descrição nas propriedades do .exe
├── web/
│   ├── controle-veiculos.html # versão web (arquivo único, offline, responsiva)
│   ├── Servidor Wi-Fi.bat   # servidor local que mostra o endereço para o celular
│   ├── servidor.py          # servidor estático + /__sync (a sincronização)
│   └── servidor-wifi.ps1    # servidor em PowerShell (quando não há Python)
├── controle_veiculos/
│   ├── format.py            # números/datas no padrão pt-BR
│   ├── models.py            # Vehicle, Refuel, Maintenance, Document (v2)
│   ├── storage.py           # gravação do JSON, pasta escolhida e migrações
│   ├── conta.py             # conta local: usuário/senha do login (PBKDF2)
│   ├── caminhos.py          # manual, Servidor Wi-Fi e endereço da versão web
│   ├── calcs.py             # consumo, custo, lembretes e relatórios
│   ├── importers.py         # importa CSV/TSV/XLSX (só biblioteca padrão)
│   └── ui/
│       ├── app.py           # janela principal (+ pergunta da pasta na 1ª abertura)
│       ├── login.py         # tela de acesso (usuário/senha + 3 modos)
│       ├── refuels_tab.py   # aba Abastecimentos
│       ├── maintenance_tab.py # aba Manutenções
│       ├── reports_tab.py   # aba Relatórios
│       ├── vehicles_tab.py  # aba Veículos
│       ├── dialogs.py       # formulários modais
│       └── chart.py         # gráfico de barras (Canvas)
└── tests/test_smoke.py      # testes de lógica, pastas, interface, sync e web
```

## Gerar/atualizar o executável

Requisito único: `python -m pip install pyinstaller`.

```powershell
git clone https://github.com/opusvix/controle-de-veiculos  # só na 1ª vez
cd controle-de-veiculos

# 1) (opcional) regenera o ícone
python tools\make_icon.py

# 2) compila — use caminhos ABSOLUTOS (o PyInstaller resolve caminhos relativos
#    contra a pasta do .spec, não contra o diretório atual)
python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name "Controle de Veículos" `
  --icon "$PWD\assets\controle_veiculos.ico" `
  --version-file "$PWD\tools\file_version_info.txt" `
  --distpath "$PWD\dist" --workpath "$PWD\build" --specpath "$PWD\build" `
  "$PWD\main.py"
```

Saída: `dist\Controle de Veículos.exe`. `--windowed` remove o console;
`--onefile` gera um arquivo único. O `.spec` fica em `build\` para recompilar.
(No PowerShell o aviso pode sair com código de saída 1 mesmo com
`Build complete!` — é normal.)

Instalação de teste sem travar o prompt:

```powershell
'' | powershell -NoProfile -ExecutionPolicy Bypass -File tools\instalar.ps1 -Destino C:\temp\teste
```

## Testes

```powershell
python tests\test_smoke.py
```

Cobre formatação pt-BR, cálculo por trecho, relatórios por período,
**manutenções e os lembretes da próxima revisão**, gravação do arquivo,
**pastas de dados (raiz escolhida, Documentos e migração)**,
**importação de planilha/CSV/XLSX**, interface e os diálogos
(abrir, validar e salvar) — mais os grupos novos: **conta local** (criar,
validar, reiniciar), **tela de acesso** (os 3 modos e as validações),
**ajuda e manuais `.txt`** (existência, CRLF e frescor em relação aos `.md`),
**conversor `md_para_txt`**, **servidor + sincronização** (junção em 3 vias,
gravação atômica, recusa de arquivo corrompido e teste HTTP de ponta a ponta)
e **página web + `Servidor Wi-Fi.bat`** (marcas da tela de acesso/ajuda/sync,
ASCII e CRLF do `.bat`). São **16 grupos**.

## Atualizar as fotos dos manuais

As fotos de `imagens\` são geradas de verdade (não são montadas à mão):

```powershell
cd controle-de-veiculos   # pasta clonada do projeto
python tools\capturas.py
```

O script abre o programa com dados de exemplo, fotografa cada aba, o diálogo da
pasta, o instalador e o servidor, e gera `icone.png` a partir do `.ico`.
As imagens que ele não faz são `08-celular.png` (tirada do navegador) e
`09-tela-acesso.png` (tela de acesso). **Pillow** é usado **só** aqui — o programa
em si continua sem nenhuma biblioteca externa. Depois de regenerar, confira se
todos os arquivos referenciados em `*.md` existem.
