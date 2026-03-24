@echo off
setlocal

where python >nul 2>nul
if errorlevel 1 (
    echo Missing required command: python
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo Missing required command: node
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo Missing required command: npm
    exit /b 1
)

if not exist .venv\Scripts\python.exe (
    echo Creating Python virtual environment...
    python -m venv .venv
)

echo Checking Python dependencies...
.venv\Scripts\python -c "import flask, flask_sqlalchemy, flask_login, flask_cors" >nul
if errorlevel 1 (
    echo Installing Python dependencies...
    .venv\Scripts\python -m pip install --upgrade pip
    .venv\Scripts\python -m pip install -r requirements.txt
    .venv\Scripts\python -m pip install -e .
)

echo Checking Node.js dependencies...
if not exist node_modules (
    echo Installing Node.js dependencies...
    call npm ci
) else (
    call npm ls --depth=0 >nul
    if errorlevel 1 (
        echo Reinstalling incomplete Node.js dependencies...
        call npm ci
    )
)

if not exist src\sstq\static\js\scan_barcode.bundle.js (
    echo Building frontend bundle...
    call npm run build:scan-barcode
)

echo Starting application...
.venv\Scripts\python -m sstq.main
endlocal
