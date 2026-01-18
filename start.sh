#!/bin/bash

# Voice Agent - Installation and Startup Script
# This script installs dependencies and starts both the API server and LiveKit agent

set -e  # Exit on error

echo "🚀 Voice Agent - Starting Setup and Launch"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found!${NC}"
    echo "Please create a .env file with all required environment variables."
    echo "See README.md for required variables."
    exit 1
fi

# Check Python version
echo -e "${BLUE}📋 Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.12+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python $PYTHON_VERSION found"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}📦 Creating virtual environment...${NC}"
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo -e "${BLUE}🔌 Activating virtual environment...${NC}"
source .venv/bin/activate

# Install/upgrade pip
echo -e "${BLUE}📦 Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# Install dependencies
echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "❌ requirements.txt not found!"
    exit 1
fi

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "❌ backend directory not found!"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down services...${NC}"
    kill $API_PID $AGENT_PID 2>/dev/null || true
    wait $API_PID $AGENT_PID 2>/dev/null || true
    echo "✅ Services stopped"
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup SIGINT SIGTERM

# Start API server
echo -e "${GREEN}🌐 Starting FastAPI server...${NC}"
cd backend
python api.py &
API_PID=$!
cd ..

# Wait a moment for API to start
sleep 2

# Check if API started successfully
if ! kill -0 $API_PID 2>/dev/null; then
    echo "❌ Failed to start API server"
    exit 1
fi

echo "✅ API server started (PID: $API_PID)"
echo "   API available at: http://localhost:8000"
echo "   API docs at: http://localhost:8000/docs"

# Start LiveKit agent
echo -e "${GREEN}🤖 Starting LiveKit agent...${NC}"
cd backend
python main.py start &
AGENT_PID=$!
cd ..

# Wait a moment for agent to start
sleep 3

# Check if agent started successfully
if ! kill -0 $AGENT_PID 2>/dev/null; then
    echo "❌ Failed to start LiveKit agent"
    kill $API_PID 2>/dev/null || true
    exit 1
fi

echo "✅ LiveKit agent started (PID: $AGENT_PID)"
echo ""
echo -e "${GREEN}=========================================="
echo "✅ All services are running!"
echo "==========================================${NC}"
echo ""
echo "📊 Services Status:"
echo "   • FastAPI Server: http://localhost:8000"
echo "   • API Documentation: http://localhost:8000/docs"
echo "   • LiveKit Agent: Running"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for both processes
wait $API_PID $AGENT_PID
