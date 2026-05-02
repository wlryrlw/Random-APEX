@echo off
setlocal

cd /d "%~dp0"

set "CONDA_ACTIVATE=H:\Anaconda3\Scripts\activate.bat"
set "APP_FILE=%~dp0apex_randomizer.py"

if not exist "%CONDA_ACTIVATE%" (
    echo Cannot find conda activate script:
    echo %CONDA_ACTIVATE%
    echo.
    pause
    exit /b 1
)

if not exist "%APP_FILE%" (
    echo Cannot find app file:
    echo %APP_FILE%
    echo.
    pause
    exit /b 1
)

call "%CONDA_ACTIVATE%" randomAPEX
if errorlevel 1 (
    echo Failed to activate conda environment: randomAPEX
    echo.
    pause
    exit /b 1
)

python "%APP_FILE%"
if errorlevel 1 (
    echo.
    echo App exited with an error.
    pause
    exit /b 1
)

endlocal
