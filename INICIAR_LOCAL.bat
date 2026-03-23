@echo off
title Fastvideo Local v5.0 (FINAL)
echo ==========================================
echo    Fastvideo - Inicia el panel local
echo ==========================================
echo.

:: Detectar el comando de Python correcto
set PYTHON_CMD=python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set PYTHON_CMD=py
    py --version >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        set PYTHON_CMD=python3
        python3 --version >nul 2>&1
        if %ERRORLEVEL% NEQ 0 (
            echo.
            echo ERROR: No se detecto Python instalado.
            echo Por favor, instala Python y marcan la opcion "Add to PATH".
            pause
            exit /b
        )
    )
)

echo [1/2] Verificando librerias...
%PYTHON_CMD% -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: No se pudieron instalar las librerias.
    pause
    exit /b
)

echo.
echo [2/2] Lanzando servidor local...
echo.
%PYTHON_CMD% app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR al iniciar la aplicacion.
    pause
)
