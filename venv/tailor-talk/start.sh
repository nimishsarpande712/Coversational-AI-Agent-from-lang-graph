#!/bin/bash
# Startup script for Tailor-Talk

echo "🚀 Starting Tailor-Talk Appointment Booking System..."

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.8+ and try again."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Check if credentials.json exists
if [ ! -f "credentials.json" ]; then
    echo "⚠️  Warning: credentials.json not found."
    echo "📝 Please add your Google Calendar API credentials to credentials.json"
    echo "ℹ️  The app will run in demo mode without calendar integration."
fi

# Start the Streamlit app
echo "🎨 Starting Streamlit frontend on http://localhost:8501"
echo "📱 The chat interface will open in your browser automatically."
echo ""
echo "💡 To also start the FastAPI backend:"
echo "   Run: python backend/api.py"
echo "   API will be available at: http://localhost:8000"
echo ""

streamlit run frontend/app.py
