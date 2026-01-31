#!/bin/bash
# VakLab Quick Start Script
# Checks dependencies and starts the system

set -e

echo "🚀 VakLab Quick Start"
echo "===================="
echo ""

# Check we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Run this script from the VakLab root directory"
    exit 1
fi

# Check Python version
echo "✓ Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "  Found: Python $python_version"

# Check if virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment active"
    echo "   Consider running: python -m venv venv && source venv/bin/activate"
fi

# Check PostgreSQL
echo ""
echo "✓ Checking PostgreSQL..."
if docker ps | grep -q outbound_agent_db; then
    echo "  ✅ Database is running"
else
    echo "  ❌ Database is NOT running"
    echo "  Starting database..."
    docker compose up -d
    sleep 3
fi

# Check .env file
echo ""
echo "✓ Checking .env configuration..."
if [ ! -f ".env" ]; then
    echo "  ❌ .env file not found"
    echo "  Creating from template..."
    cp .env.example .env 2>/dev/null || echo "  ⚠️  Please create .env file manually"
    exit 1
fi

# Check critical env vars
source .env
if [ "$TWILIO_SID" = "your_twilio_account_sid" ]; then
    echo "  ⚠️  TWILIO_SID not configured"
fi
if [ "$DOMAIN" = "https://your-ngrok-url.ngrok.io" ]; then
    echo "  ⚠️  DOMAIN not configured (update after starting ngrok)"
fi

# Check pipecat installation
echo ""
echo "✓ Checking dependencies..."
if ! pip list | grep -q pipecat-ai; then
    echo "  ❌ pipecat-ai not installed"
    echo "  Installing now..."
    pip install "pipecat-ai[google,silero]"
else
    echo "  ✅ pipecat-ai installed"
fi

# Check Google credentials
echo ""
echo "✓ Checking Google credentials..."
if [ -f "cool-furnace-483603-b2-fdd4814415cb.json" ]; then
    echo "  ✅ Credentials file found"
    export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/cool-furnace-483603-b2-fdd4814415cb.json"
else
    echo "  ❌ Credentials file not found"
    exit 1
fi

# Check ngrok
echo ""
echo "✓ Checking ngrok..."
if command -v ngrok &> /dev/null; then
    echo "  ✅ ngrok installed"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Start ngrok in a new terminal: ngrok http 8000"
    echo "   2. Copy the HTTPS URL from ngrok"
    echo "   3. Update DOMAIN in .env"
    echo "   4. Run this script again"
    echo ""
else
    echo "  ❌ ngrok not installed"
    echo "  Install from: https://ngrok.com/download"
    exit 1
fi

# Check if server is already running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "⚠️  Server is already running on port 8000"
    echo "   Stop it first with: pkill -f 'uvicorn main:app'"
    exit 1
fi

echo ""
echo "✅ All checks passed!"
echo ""
echo "🚀 Starting server..."
echo "   Press Ctrl+C to stop"
echo ""

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
