@echo off
title Fastvideo Desktop v7.0
echo ==========================================
echo    Fastvideo - Instalador Escritorio
echo ==========================================
echo.

:: Detectar Python
set PYTHON_CMD=python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set PYTHON_CMD=py
    py --version >nul 2>&1
)

echo [1/3] Verificando componentes...
%PYTHON_CMD% -m pip install -r requirements.txt

echo.
echo [2/3] Creando acceso directo en escritorio...
cscript //nologo CREAR_ACCESO.vbs

echo.
echo [3/3] Iniciando aplicacion...
echo.
%PYTHON_CMD% app.py
pause
