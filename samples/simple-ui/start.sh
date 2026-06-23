#!/bin/bash

# Simple UI Sample - Quick Start Script
# This script helps you get the application running quickly

set -e  # Exit on error

echo "🚀 Simple UI Sample - Quick Start"
echo "=================================="
echo ""

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Please run this script from the samples/simple-ui directory"
    exit 1
fi

# Step 1: Install Python dependencies
echo "📦 Step 1/4: Installing Python dependencies..."
if ! command -v poetry &> /dev/null; then
    echo "❌ Error: Poetry not found. Please install Poetry first:"
    echo "   curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

poetry install
poetry add python-jose[cryptography] 2>/dev/null || echo "   python-jose already installed"

echo "✅ Python dependencies installed"
echo ""

# Step 2: Install Node.js dependencies
echo "📦 Step 2/4: Installing Node.js dependencies..."
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm not found. Please install Node.js first:"
    echo "   https://nodejs.org/"
    exit 1
fi

cd ui
npm install

echo "✅ Node.js dependencies installed"
echo ""

# Step 3: Build frontend assets
echo "🔨 Step 3/4: Building frontend assets..."
npm run build

echo "✅ Frontend assets built"
echo ""

# Step 4: Start the application
cd ..
echo "🎯 Step 4/4: Starting the application..."
echo ""
echo "==================================="
echo "🎉 Setup Complete!"
echo "==================================="
echo ""
echo "📝 Demo User Accounts:"
echo "   • admin     / admin123    (See all tasks, can create)"
echo "   • manager   / manager123  (See non-admin tasks)"
echo "   • john.doe  / user123     (See assigned tasks)"
echo "   • jane.smith / user123    (See assigned tasks)"
echo ""
echo "🌐 Application starting at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the application"
echo "==================================="
echo ""

poetry run python main.py
