@echo off
REM Voice Agent - Installation and Startup Script (Windows)
REM This script installs dependencies and starts both the API server and LiveKit agent

echo 🚀 Voice Agent - Starting Setup and Launch
echo ==========================================

REM Check if .env exists
if not exist .env (
    echo ⚠️  Warning: .env file not found!
    echo Please create a .env file with all required environment variables.
    echo See README.md for required variables.
    pause
    exit /b 1
)

REM Check Python version
echo 📋 Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.12+ first.
    pause
    exit /b 1
)

python --version
echo ✅ Python found

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo 📦 Creating virtual environment...
    python -m venv .venv
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment already exists
)

REM Activate virtual environment
echo 🔌 Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install/upgrade pip
echo 📦 Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo 📦 Installing Python dependencies...
if exist "requirements.txt" (
    pip install -r requirements.txt
    echo ✅ Dependencies installed
) else (
    echo ❌ requirements.txt not found!
    pause
    exit /b 1
)

REM Check if backend directory exists
if not exist "backend" (
    echo ❌ backend directory not found!
    pause
    exit /b 1
)

REM Start API server
echo 🌐 Starting FastAPI server...
cd backend
start "FastAPI Server" cmd /k "python api.py"
cd ..
timeout /t 2 /nobreak >nul

echo ✅ API server started
echo    API available at: http://localhost:8000
echo    API docs at: http://localhost:8000/docs

REM Start LiveKit agent
echo 🤖 Starting LiveKit agent...
cd backend
start "LiveKit Agent" cmd /k "python main.py start"
cd ..
timeout /t 3 /nobreak >nul

echo ✅ LiveKit agent started
echo.
echo ==========================================
echo ✅ All services are running!
echo ==========================================
echo.
echo 📊 Services Status:
echo    • FastAPI Server: http://localhost:8000
echo    • API Documentation: http://localhost:8000/docs
echo    • LiveKit Agent: Running
echo.
echo Close the command windows to stop the services
echo.
pause
