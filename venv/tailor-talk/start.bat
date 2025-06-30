@echo off
REM Startup script for Tailor-Talk (Windows)

echo 🚀 Starting Tailor-Talk Appointment Booking System...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8+ and try again.
    pause
    exit /b 1
)

REM Install dependencies
echo 📦 Installing dependencies...
pip install -r requirements.txt

REM Check if credentials.json exists
if not exist "credentials.json" (
    echo ⚠️  Warning: credentials.json not found.
    echo 📝 Please add your Google Calendar API credentials to credentials.json
    echo ℹ️  The app will run in demo mode without calendar integration.
    echo.
)

REM Start the Streamlit app
echo 🎨 Starting Streamlit frontend on http://localhost:8501
echo 📱 The chat interface will open in your browser automatically.
echo.
echo 💡 To also start the FastAPI backend:
echo    Run: python backend/api.py
echo    API will be available at: http://localhost:8000
echo.

streamlit run frontend/app.py
