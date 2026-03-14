#!/bin/bash
# GramUploader — Quick Start
# Run: ./run.sh

cd "$(dirname "$0")"

# Activate venv if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check .env
if [ ! -f ".env" ]; then
    echo "❌ .env not found. Run ./setup_local.sh first."
    exit 1
fi

echo "🚀 Starting GramUploader..."
python main.py
