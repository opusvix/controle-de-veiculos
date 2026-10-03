# Instala o Controle de Veiculos: sugere a pasta padrao do Windows (Program
# Files) e pede so o ENTER do usuario, remove uma versao anterior (os dados
# ficam intactos), copia o programa e cria o atalho na area de trabalho.
# Sem acentos nas mensagens de proposito: o arquivo e gravado em UTF-8 com
# BOM, mas o texto fica simples para facilitar leitura (o nome do atalho
# mantem o acento porque e o nome exato que o Windows usa).
param(
    [string]$Destino = ""
)

# --------------------------------------------------------------- utilidades
$elevado = ([Security.Principal.WindowsPrincipal]::new(
    [Security.Principal.WindowsIdentity]::GetCurrent()
)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

$raiz = Split-Path -Parent $PSScriptRoot   # pasta de onde o instalador veio
$chave = "HKCU:\Software\Controle de Veiculos"   # memoria da instalacao
$atalhoPath = Join-Path ([Environment]::GetFolderPath('Desktop')) "Controle de Veículos.lnk"
$interativo = [string]::IsNullOrEmpty($Destino)  # sem -Destino, ele pergunta

function Sair([int]$codigo) {
    # A janela elevada e aberta direto pelo Windows (sem o .bat do lado de
    # fora): nela o erro precisa da pausa aqui. Chamado pelo .bat, quem pausa
    # e o proprio .bat.
    if ($codigo -ne 0 -and $elevado) {
        Write-Host ""
        Read-Host "  Tecle ENTER para fechar"
    }
    exit $codigo
}

function Normaliza([string]$p) {
    return $p.TrimEnd('\').ToLowerInvariant()
}

function PastaBaseWindows() {
    $base = $env:ProgramFiles
    if ([string]::IsNullOrEmpty($base)) { $base = "C:\Program Files" }
    return $base
}

function PrecisaAdmin([string]$pasta) {
    # Program Files (e Program Files (x86)) so aceitam copia com permissao
    # de administrador - la o instalador precisa pedir a permissao do Windows.
    if ([string]::IsNullOrWhiteSpace($pasta)) { return $false }
    $alvos = @((PastaBaseWindows), ${env:ProgramFiles(x86)}) |
        Where-Object { -not [string]::IsNullOrEmpty($_) }
    $caminho = $pasta.TrimEnd('\')
    foreach ($alvo in $alvos) {
        $raizAlvo = $alvo.TrimEnd('\')
        if ($caminho.Equals($raizAlvo, [StringComparison]::OrdinalIgnoreCase) -or
            $caminho.StartsWith($raizAlvo + '\', [StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Remover-VersaoAntiga([string]$pasta, [string]$exeAntigo) {
    Write-Host ""
    Write-Host "  Versao anterior em: $pasta" -ForegroundColor Yellow

    # o programa (ou a janela do Servidor Wi-Fi) ainda esta aberto daqui?
    $alvoDir = $pasta.TrimEnd('\') + '\'
    $ocupado = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $c = $null
        try { $c = $_.Path } catch { $c = $null }
        if (-not $c) { $false }
        else {
            $caminho = $c.TrimEnd('\') + '\'
            $caminho.StartsWith($alvoDir, [StringComparison]::OrdinalIgnoreCase)
        }
    }
    if ($ocupado) {
        Write-Host "  O programa esta aberto. Feche o Controle de Veiculos (e a" -ForegroundColor Red
        Write-Host "  janela preta do Servidor Wi-Fi, se estiver) e rode o" -ForegroundColor Red
        Write-Host "  Instalar.bat de novo." -ForegroundColor Red
        Sair 1
    }

    try {
        # so apaga o executavel se ele estiver dentro da pasta antiga
        if ($exeAntigo -and (Test-Path -LiteralPath $exeAntigo)) {
            if ($exeAntigo.TrimEnd('\').StartsWith($alvoDir, [StringComparison]::OrdinalIgnoreCase)) {
                Remove-Item -LiteralPath $exeAntigo -Force
            }
        }
        foreach ($nome in @("web", "imagens")) {
            $dir = Join-Path $pasta $nome
            if (Test-Path -LiteralPath $dir) {
                Remove-Item -LiteralPath $dir -Recurse -Force -ErrorAction Stop
            }
        }
        Get-ChildItem -LiteralPath $pasta -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Extension -eq ".md" -or $_.Extension -eq ".txt" } |
            Remove-Item -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Host "  Aviso: nao deu para apagar tudo ($($_.Exception.Message))." -ForegroundColor Yellow
        Write-Host "  Os arquivos novos vao por cima dos antigos." -ForegroundColor Yellow
    }

    # atalho antigo (o novo e criado no fim)
    if (Test-Path -LiteralPath $atalhoPath) {
        Remove-Item -LiteralPath $atalhoPath -Force -ErrorAction SilentlyContinue
    }

    # a pasta do programa so sai se ficar vazia: a pasta de DADOS
    # (ControleVeiculos) dentro dela e sua e nunca e tocada.
    $restos = @(Get-ChildItem -LiteralPath $pasta -Force -ErrorAction SilentlyContinue)
    if ($restos.Count -eq 0) {
        Remove-Item -LiteralPath $pasta -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -Path $chave -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  Versao anterior removida (seus dados ficaram onde estao)." -ForegroundColor Green
}

function MarcaAtual() {
    return Get-ItemProperty -Path $chave -ErrorAction SilentlyContinue
}

# --------------------------------------------------------------- cabecalho
$Host.UI.RawUI.WindowTitle = "Instalar Controle de Veiculos"
$marca = MarcaAtual

Write-Host ""
Write-Host "=========================================================="
Write-Host "  INSTALAR - Controle de Veiculos"
Write-Host "=========================================================="
Write-Host ""
Write-Host "  Programa encontrado em: $raiz"
Write-Host ""

if ($marca -and $marca.InstallDir) {
    Write-Host "  Versao instalada encontrada:" -ForegroundColor Yellow
    Write-Host "    $($marca.InstallDir)"
    $detalhe = @()
    if ($marca.Versao) { $detalhe += "versao $($marca.Versao)" }
    if ($marca.InstaladoEm) { $detalhe += "instalada em $($marca.InstaladoEm)" }
    if ($detalhe.Count -gt 0) {
        Write-Host "    ($($detalhe -join ', '))"
    }
    Write-Host ""
}

# ------------------------------------------------------------------ pasta
$pastaPadrao = Join-Path (PastaBaseWindows) "Controle de Veiculos"
if ($interativo) {
    Write-Host "  Escolha a pasta do programa."
    Write-Host "  ENTER ja instala na pasta padrao do Windows."
    Write-Host ""
    $Destino = Read-Host "  Pasta de instalacao [$pastaPadrao]"
    if ([string]::IsNullOrWhiteSpace($Destino)) { $Destino = $pastaPadrao }
}

$Destino = $Destino.Trim().Trim('"')
try {
    $Destino = [System.IO.Path]::GetFullPath($Destino)
} catch {
    Write-Host "  Caminho invalido: $Destino" -ForegroundColor Red
    Sair 1
}

$mesmaPasta = (Normaliza $Destino) -eq (Normaliza $raiz)
Write-Host ""
Write-Host "  Destino: $Destino"
Write-Host ""

# ---------------------------------------------- permissao do Windows (UAC)
$antigaPrecisaAdmin = $false
if ($marca -and $marca.InstallDir) {
    $antigaPrecisaAdmin = PrecisaAdmin ([string]$marca.InstallDir)
}
if ($interativo -and (-not $elevado) -and (-not $mesmaPasta) -and
    ((PrecisaAdmin $Destino) -or $antigaPrecisaAdmin)) {
    Write-Host "  Essa pasta e protegida pelo Windows. O instalador vai" -ForegroundColor Yellow
    Write-Host "  pedir permissao agora: clique em Sim na janela do Windows." -ForegroundColor Yellow
    Write-Host ""
    try {
        $argumentos = "-NoProfile -ExecutionPolicy Bypass -File `"{0}`" -Destino `"{1}`"" -f `
            $PSCommandPath, $Destino
        Start-Process -FilePath "powershell.exe" -ArgumentList $argumentos -Verb RunAs
        exit 0
    } catch {
        Write-Host "  Permissao nao concedida - nada foi alterado." -ForegroundColor Red
        Read-Host "  Tecle ENTER para fechar"
        exit 0
    }
}

# --------------------------------------------- versao anterior (atualizacao)
if ($marca -and $marca.InstallDir) {
    $antigaDir = [string]$marca.InstallDir
    # a propria pasta do pacote (fontes, dist\, tools\) nunca e removida
    if ((Normaliza $antigaDir) -ne (Normaliza $raiz)) {
        if (Test-Path -LiteralPath $antigaDir) {
            Remover-VersaoAntiga $antigaDir ([string]$marca.ExeInstalado)
        } else {
            Write-Host ""
            Write-Host "  A pasta da versao anterior ja nao existe - sigo em frente." -ForegroundColor Yellow
            Remove-Item -Path $chave -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

# ------------------------------------------------------- copiar arquivos
$exeOrigem = Get-ChildItem -Path (Join-Path $raiz "dist") -Filter *.exe -File -ErrorAction SilentlyContinue |
    Select-Object -First 1

if ($mesmaPasta) {
    Write-Host "  O programa ja esta nesta pasta - nada para copiar." -ForegroundColor Yellow
    if (-not $exeOrigem) {
        Write-Host "  Nao encontrei o executavel em dist\." -ForegroundColor Red
        Write-Host "  Compile primeiro (veja o README.md) e rode de novo." -ForegroundColor Red
        Sair 1
    }
} else {
    if (-not $exeOrigem) {
        Write-Host "  Nao encontrei o executavel em dist\." -ForegroundColor Red
        Write-Host "  Compile primeiro (veja o README.md) e rode de novo." -ForegroundColor Red
        Sair 1
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
        Sair 1
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
    Sair 1
}

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

# ------------------------------------------------- registrar a instalacao
# O registro diz a uma proxima rodada onde esta a versao antiga (para remove-la)
# e onde ficam os dados do usuario (nunca sao apagados pelo instalador).
try {
    New-Item -Path $chave -Force | Out-Null
    Set-ItemProperty -Path $chave -Name "InstallDir" -Value $Destino
    Set-ItemProperty -Path $chave -Name "ExeInstalado" -Value $exeInstalado.FullName
    Set-ItemProperty -Path $chave -Name "InstaladoEm" -Value (Get-Date -Format "dd/MM/yyyy")
    $versao = $exeInstalado.VersionInfo.ProductVersion
    if ($versao) {
        Set-ItemProperty -Path $chave -Name "Versao" -Value $versao
    }
} catch {
    Write-Host "  Aviso: nao deu para registrar a instalacao: $($_.Exception.Message)" -ForegroundColor Yellow
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
Write-Host "  os dados (padrao: ao lado do programa, pasta"
Write-Host "  ControleVeiculos). Se a pasta nao aceitar gravacao -"
Write-Host "  como o Program Files - ele usa sozinho a pasta"
Write-Host "  Documentos\ControleVeiculos."
Write-Host "  Em seguida ele pede um usuario e uma senha (tranca local)."
Write-Host ""
Write-Host "  Guia completo: INSTALAR-COMO-USAR.md (tem versao .txt tambem,"
Write-Host "  que abre pelo botao Ajuda do programa)."
Write-Host ""
Read-Host "  Tecle ENTER para fechar"
exit 0
