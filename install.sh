#!/bin/bash

# Voice Agent - Installation Script Only
# This script only installs dependencies without starting services

set -e  # Exit on error

echo "📦 Voice Agent - Installation Script"
echo "===================================="

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
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
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

# Check frontend dependencies
if [ -d "frontend" ]; then
    echo -e "${BLUE}📦 Installing frontend dependencies...${NC}"
    cd frontend
    if [ -f "package.json" ]; then
        npm install
        echo "✅ Frontend dependencies installed"
    else
        echo "⚠️  package.json not found in frontend directory"
    fi
    cd ..
fi

echo ""
echo -e "${GREEN}===================================="
echo "✅ Installation complete!"
echo "====================================${NC}"
echo ""
echo "To start the services, run:"
echo "  ./start.sh          (Linux/Mac)"
echo "  start.bat            (Windows)"
echo ""
