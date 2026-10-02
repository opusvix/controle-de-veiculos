@echo off
title Instalar Controle de Veiculos
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\instalar.ps1"
if errorlevel 1 pause
