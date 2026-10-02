# Divulgação — posts, stories e Reels

Material pronto para divulgar o Controle de Veículos nas redes. As imagens
ficam nesta pasta; os textos abaixo são para copiar e colar.

O link e o QR de todas as artes apontam para a página da release mais nova:

<https://github.com/opusvix/controle-de-veiculos/releases/latest>

Quando sair uma versão nova do programa, **nada precisa ser mudado** nas artes.

## As imagens

| arquivo | tamanho | serve para |
|---|---|---|
| `qr-release.png` | 904×904 | QR puro — servem para imprimir ou colar em qualquer arte |
| `post-feed-1080x1080.png` | 1080×1080 | feed do Instagram/Facebook e post do LinkedIn |
| `story-1080x1920.png` | 1080×1920 | stories (Instagram, Facebook e status do WhatsApp) |
| `capa-reels-1080x1920.png` | 1080×1920 | Reels/TikTok — o texto fica no centro, então sobrevive ao corte quadrado do feed |

Para regenerar (depois de mudar as telas ou as cores do programa):

```powershell
python -m pip install pillow qrcode   # uma vez só
python tools\divulgacao.py
```

Os requisitos extras valem só para as artas — o programa em si continua sem
nenhuma biblioteca fora da biblioteca padrão.

## Textos prontos (copie e colar)

### LinkedIn

> Você sabe quanto gastou para manter seu carro no mês passado?
>
> Eu não sabia. Foi essa dor que me fez criar o **Controle de Veículos**: um
> programa de Windows que transforma a pilha de notinhas de posto em
> informação útil.
>
> O que ele faz:
>
> - Registra abastecimentos e já calcula o consumo (km/l) e o custo por km;
> - Guarda as manutenções com lembrete da próxima revisão (óleo, pneus, freios...);
> - Mostra relatórios: quanto você gastou no mês, no período e por veículo;
> - Tem versão para o celular na rede local, que sincroniza com o PC.
>
> E o que ele **não** faz: mandar seus dados para a nuvem. Funciona offline,
> sem cadastro e sem internet — cada aparelho tem sua própria tranca de
> usuário e senha. Seus dados são seus.
>
> É gratuito e de código aberto. Dá para instalar em 2 minutos:
> <https://github.com/opusvix/controle-de-veiculos/releases/latest>
>
> Se você também perde a noção de quanto o carro "come", testa e me conta o
> que achou — feedback é bem-vindo. 🚗
>
> #FinançasPessoais #Mobilidade #CódigoAberto #ProjetosPessoais #Windows

### Facebook

> Sabe aquela sensação de chegar no fim do mês e não lembrar quanto foi
> gasolina? 😅
>
> Fiz um programinha que resolve isso: o **Controle de Veículos**. 🚗
>
> Nele você anota cada abastecimento e ele já te mostra:
>
> - ⛽ quanto gastou no mês;
> - 📊 o consumo do carro (km/l) e o custo por quilômetro;
> - 🔧 as manutenções com lembrete da próxima revisão.
>
> E o melhor: tudo fica no **SEU computador**. Sem nuvem, sem cadastro e sem
> internet — com senha para ninguém abrir no seu lugar.
>
> Baixar é de graça (Windows 10/11):
> <https://github.com/opusvix/controle-de-veiculos/releases/latest>
>
> É só baixar o zip, extrair tudo e dar dois cliques em `Instalar.bat` — o
> passo a passo com fotos vem junto. Manda para aquele amigo que diz que
> "carro é um buraco negro" 😄

### Instagram (feed)

> Quanto você gastou no carro mês passado? 🚗💨
>
> O Controle de Veículos é um app gratuito de PC que transforma a pilha de
> notinhas de posto em informação de verdade:
>
> 📊 consumo e custo por km
> 🔧 manutenção com lembrete da revisão
> 🔒 tudo offline — seus dados ficam com você
>
> Baixar: aponte a câmera para o QR code 👆 ou pegue o link na bio.
> Windows 10/11 • grátis • sem cadastro
>
> #controledeveiculos #carro #moto #gastosdocarro #consumo #manutencao
> #financaspessoais #dicasdicarro #appgratuito #offline

Publique junto com `post-feed-1080x1080.png`.

### Status/mensagem no WhatsApp

> Programa novo aqui em casa: **Controle de Veículos** — anota abastecimento,
> mostra o consumo do carro, avisa quando chega a hora da manutenção e ainda
> funciona offline (dados ficam no PC, sem nuvem). Gratuito:
> <https://github.com/opusvix/controle-de-veiculos/releases/latest>
> (baixa o zip, extrai e dá dois cliques em Instalar.bat)

## Stories (Instagram, Facebook e WhatsApp status)

1. Publique a arte `story-1080x1920.png`.
2. Adicione o **sticker de link** com o endereço da release (o card branco da
   arte já tem o QR — o sticker ajuda quem prefere clicar).
3. Sticker de **enquete**: "Você sabe quanto gastou no carro mês passado?"
   — *Nem ideia* / *Sei sim*.
4. Sticker de **caixinha de perguntas**: "O que mais quer ver no programa?"
   — as respostas viram ideia (e conteúdo) para os próximos posts.

## Reels / TikTok — roteiro de 25 segundos

Grave a tela com o programa aberto (Win+G do Windows, OBS ou celular
filmando). O texto já serve de legenda:

1. **0–3 s (gancho)** — abre o programa, câmera perto da tela:
   **"Quanto você gastou no carro mês passado?"**
2. **3–8 s** — preenche um abastecimento (data, odômetro, litros, valor):
   **"Anote em 10 segundos"**
3. **8–13 s** — destaque na coluna km/l e no total:
   **"Ele já calcula o consumo e o custo por km"**
4. **13–17 s** — aba Manutenções com o aviso de revisão:
   **"E nunca mais esquece a troca do óleo"**
5. **17–21 s** — aba Relatórios:
   **"Quanto o carro comeu no mês"**
6. **21–25 s** — encerra na arte `capa-reels-1080x1920.png` ou com o QR na
   tela: **"Grátis, offline, sem cadastro — link na bio"**

Áudio: use um som em alta do momento (ou sua voz); deixe a legenda automática
ligada. Capa do Reels: `capa-reels-1080x1920.png`.

## Dicas por rede

- **Instagram:** o link do post não clica — deixe o endereço na **bio** e
  escreva "link na bio"; o QR resolve quem já está no celular.
- **LinkedIn/Facebook:** anexe `post-feed-1080x1080.png` ao texto e deixe o
  link no fim (funciona em qualquer ordem, mas no fim fica mais legível).
- **Windows SmartScreen:** se alguém reclamar do aviso "Windows protegeu seu
  computador", é o padrão de arquivos baixados da internet — é só clicar em
  **Mais informações → Executar assim mesmo** (manual, Passo 7).

## Quando sair uma versão nova

1. Publique a release nova (o endereço "latest" passa a apontar para ela);
2. as artes e os textos continuam valendo como estão;
3. só gere artes novas se as **telas** do programa mudaram:
   `python tools\capturas.py` (fotos) e depois `python tools\divulgacao.py`.
