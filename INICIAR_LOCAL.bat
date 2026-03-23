@echo off
title Fastvideo Local v3.1
echo ==========================================
echo    Fastvideo - Inicia el panel local
echo ==========================================
echo.
echo [1/2] Verificando librerias...
python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: No se pudieron instalar las librerias.
    echo Asegurate de tener Python instalado y añadido al PATH.
    pause
    exit /b
)

echo.
echo [2/2] Lanzando servidor local...
echo.
python app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR al iniciar la aplicacion.
    pause
)
