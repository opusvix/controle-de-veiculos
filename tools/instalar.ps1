# Instala o Controle de Veiculos: pergunta a pasta, copia o programa e
# cria o atalho na area de trabalho. Sem acentos aqui de proposito: o arquivo
# e gravado em UTF-8 com BOM, mas o texto fica simples para facilitar leitura.
param(
    [string]$Destino = ""
)

$raiz = Split-Path -Parent $PSScriptRoot   # pasta de onde o instalador veio

function Normaliza([string]$p) {
    return $p.TrimEnd('\').ToLowerInvariant()
}

Write-Host ""
Write-Host "=========================================================="
Write-Host "  INSTALAR - Controle de Veiculos"
Write-Host "=========================================================="
Write-Host ""
Write-Host "  Programa encontrado em: $raiz"
Write-Host ""

# ------------------------------------------------------------- pasta
if (-not $Destino) {
    # sugestao: a propria pasta de onde o instalador veio (instala ali mesmo)
    $padrao = $raiz
    Write-Host "  Escolha a pasta onde o programa vai ficar."
    Write-Host ""
    $Destino = Read-Host "  Pasta de instalacao [$padrao]"
    if ([string]::IsNullOrWhiteSpace($Destino)) { $Destino = $padrao }
}

$Destino = $Destino.Trim().Trim('"')
try {
    $Destino = [System.IO.Path]::GetFullPath($Destino)
} catch {
    Write-Host "  Caminho invalido: $Destino" -ForegroundColor Red
    exit 1
}

$mesmaPasta = (Normaliza $Destino) -eq (Normaliza $raiz)
Write-Host ""
Write-Host "  Destino: $Destino"
Write-Host ""

# ------------------------------------------------------- copiar arquivos
$exeOrigem = Get-ChildItem -Path (Join-Path $raiz "dist") -Filter *.exe -File -ErrorAction SilentlyContinue |
    Select-Object -First 1

if ($mesmaPasta) {
    Write-Host "  O programa ja esta nesta pasta - nada para copiar." -ForegroundColor Yellow
    if (-not $exeOrigem) {
        Write-Host "  Nao encontrei o executavel em dist\." -ForegroundColor Red
        Write-Host "  Compile primeiro (veja o README.md) e rode de novo." -ForegroundColor Red
        exit 1
    }
} else {
    if (-not $exeOrigem) {
        Write-Host "  Nao encontrei o executavel em dist\." -ForegroundColor Red
        Write-Host "  Compile primeiro (veja o README.md) e rode de novo." -ForegroundColor Red
        exit 1
    }
    try {
        New-Item -ItemType Directory -Force -Path $Destino | Out-Null
        Copy-Item -Path $exeOrigem.FullName -Destination $Destino -Force

        $webOrigem = Join-Path $raiz "web"
        if (Test-Path $webOrigem) {
            $webDestino = Join-Path $Destino "web"
            New-Item -ItemType Directory -Force -Path $webDestino | Out-Null
            Copy-Item -Path (Join-Path $webOrigem "*") -Destination $webDestino -Recurse -Force
            # nao levar o cache do Python (__pycache__)
            Get-ChildItem -Path $webDestino -Filter __pycache__ -Directory -Recurse -ErrorAction SilentlyContinue |
                Remove-Item -Recurse -Force
        }

        # imagens\ alimenta os manuais (README.md e INSTALAR-COMO-USAR.md)
        $imgOrigem = Join-Path $raiz "imagens"
        if (Test-Path $imgOrigem) {
            $imgDestino = Join-Path $Destino "imagens"
            New-Item -ItemType Directory -Force -Path $imgDestino | Out-Null
            Copy-Item -Path (Join-Path $imgOrigem "*") -Destination $imgDestino -Force
        }

        # guias em texto (o botao Ajuda abre o .txt)
        Get-ChildItem -Path $raiz -Filter *.md -File -ErrorAction SilentlyContinue |
            Copy-Item -Destination $Destino -Force
        Get-ChildItem -Path $raiz -Filter *.txt -File -ErrorAction SilentlyContinue |
            Copy-Item -Destination $Destino -Force
    } catch {
        Write-Host "  Nao foi possivel copiar: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  Confira se a pasta existe e se voce tem permissao de escrita." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Programa copiado para a pasta." -ForegroundColor Green
}

# ------------------------------------------------------------- atalho
$exeInstalado = $null
if (-not $mesmaPasta) {
    $exeInstalado = Get-ChildItem -Path $Destino -Filter *.exe -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
}
if (-not $exeInstalado) { $exeInstalado = $exeOrigem }
if (-not $exeInstalado) {
    Write-Host "  Nenhum executavel em $Destino para criar o atalho." -ForegroundColor Red
    exit 1
}

$desktop = [Environment]::GetFolderPath('Desktop')
$atalhoPath = Join-Path $desktop "Controle de Veículos.lnk"
try {
    $wsh = New-Object -ComObject WScript.Shell
    $lnk = $wsh.CreateShortcut($atalhoPath)
    $lnk.TargetPath = $exeInstalado.FullName
    $lnk.WorkingDirectory = $Destino
    $lnk.Description = "Controle de Veículos"
    $lnk.Save()
    Write-Host "  Atalho criado na area de trabalho: Controle de Veículos.lnk" -ForegroundColor Green
} catch {
    Write-Host "  Nao foi possivel criar o atalho: $($_.Exception.Message)" -ForegroundColor Yellow
}

# --------------------------------------------------------------- resumo
Write-Host ""
Write-Host "=========================================================="
Write-Host "  INSTALACAO CONCLUIDA"
Write-Host "=========================================================="
Write-Host ""
Write-Host "  Programa: $Destino"
Write-Host "  Executavel: $($exeInstalado.Name)"
if (Test-Path (Join-Path $Destino "web")) {
    Write-Host "  Versao web: pasta web\ (celular via Servidor Wi-Fi.bat)"
}
if (Test-Path (Join-Path $Destino "imagens")) {
    Write-Host "  Imagens dos guias: pasta imagens\"
}
Write-Host ""
Write-Host "  Na primeira abertura o programa pergunta onde gravar"
Write-Host "  os dados (padrao: pasta do programa + ControleVeiculos)."
Write-Host "  Se essa pasta nao existir mais, ele usa sozinho a pasta"
Write-Host "  Documentos\ControleVeiculos."
Write-Host "  Em seguida ele pede um usuario e uma senha (tranca local)."
Write-Host ""
Write-Host "  Guia completo: INSTALAR-COMO-USAR.md (tem versao .txt tambem,"
Write-Host "  que abre pelo botao Ajuda do programa)."
Write-Host ""
Read-Host "  Tecle ENTER para fechar"
exit 0
