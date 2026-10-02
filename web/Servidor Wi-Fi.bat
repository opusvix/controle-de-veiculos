@echo off
chcp 65001 >nul
title Controle de Veiculos - Servidor Wi-Fi
cd /d "%~dp0"

echo.
echo  ==================================================
echo   CONTROLE DE VEICULOS  -  Servidor Wi-Fi
echo  ==================================================
echo.
rem -- Python 3 instalado? (o atalho da Microsoft Store nao vale) --
python -c "import sys;sys.exit(0 if sys.version_info[0]>=3 else 1)" >nul 2>nul
if errorlevel 1 goto :sem_python
rem -- descobre o IP local deste computador --
set "IP=127.0.0.1"
for /f "delims=" %%A in ('python -c "import socket;s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(('8.8.8.8',80));print(s.getsockname()[0])" 2^>nul') do set "IP=%%A"
echo   No celular, abra o navegador e digite:
echo.
echo        http://%IP%:8000/controle-veiculos.html
echo.
echo   * celular e PC precisam estar na mesma rede Wi-Fi
echo   * para encerrar, feche esta janela ou pressione Ctrl+C
echo   * o botao Sincronizar da pagina atualiza os dados do PC
echo.
echo  --------------------------------------------------
echo.
python "%~dp0servidor.py"
if errorlevel 1 goto :sem_sincronismo
echo.
echo  Servidor encerrado.
pause
goto :fim

:sem_sincronismo
echo.
echo   O servidor com sincronizacao nao abriu. Usando o
echo   servidor simples: a pagina abre normalmente, mas o
echo   botao Sincronizar fica indisponivel.
echo.
python -m http.server 8000 --bind 0.0.0.0
echo.
echo  Servidor encerrado.
pause
goto :fim

:sem_python
echo   Python nao instalado neste PC - tudo bem.
echo   O servidor vai usar o PowerShell que ja vem com o
echo   Windows. Nao e preciso instalar nada.
echo   (sem Python nao ha botao Sincronizar: use Baixar/
echo   Importar dados.json como sempre)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0servidor-wifi.ps1"
echo.
pause
:fim
