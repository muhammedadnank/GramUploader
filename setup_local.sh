#!/bin/bash
# ─────────────────────────────────────────────────────────────
# GramUploader — Local Linux Setup Script
# Run from project root: chmod +x setup_local.sh && ./setup_local.sh
# ─────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"  # always run from project root

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  GramUploader — Local Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Python version check ──────────────────────────────────────
echo ""
echo "── Checking Python version ──"
if command -v python3.11 &>/dev/null; then
    PYTHON=python3.11
elif command -v python3 &>/dev/null; then
    VER=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
    MAJOR=$(echo $VER | cut -d. -f1)
    MINOR=$(echo $VER | cut -d. -f2)
    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
        PYTHON=python3
    else
        echo "❌ Python 3.10+ required. Found: $(python3 --version)"
        exit 1
    fi
else
    echo "❌ Python 3 not found. Install with: sudo apt install python3.11"
    exit 1
fi
echo "✅ Using: $($PYTHON --version)"

# ── System packages ───────────────────────────────────────────
echo ""
echo "── Installing system packages ──"
sudo apt-get update -qq
sudo apt-get install -y \
    ffmpeg \
    gcc \
    g++ \
    python3-dev \
    python3-pip \
    libffi-dev \
    > /dev/null
echo "✅ ffmpeg: $(ffmpeg -version 2>&1 | head -1)"

# ── Virtual environment ───────────────────────────────────────
echo ""
echo "── Setting up virtual environment ──"
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    echo "✅ Created venv/"
else
    echo "  venv/ already exists, skipping"
fi

source venv/bin/activate
echo "✅ venv activated"

# ── pip upgrade ───────────────────────────────────────────────
pip install --upgrade pip --quiet

# ── Python dependencies ───────────────────────────────────────
echo ""
echo "── Installing Python dependencies ──"
echo "  (openai-whisper will download PyTorch ~2GB on first run)"
pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"

# ── .env check ───────────────────────────────────────────────
echo ""
echo "── Checking .env ──"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  .env created from .env.example"
    echo "   Fill in your values: nano .env"
    echo ""
    echo "   Required:"
    echo "     API_ID, API_HASH, BOT_TOKEN"
    echo "     MONGO_URI"
    echo "     GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET"
    echo "     OAUTH_BASE_URL (use http://localhost:8080 for local)"
    echo "     GOOGLE_REDIRECT_URI (use http://localhost:8080/callback for local)"
    echo "     ADMIN_IDS"
    exit 0
else
    echo "✅ .env found"
fi

# ── Required env vars check ───────────────────────────────────
echo ""
echo "── Validating .env ──"
source .env 2>/dev/null || true
MISSING=()
for VAR in API_ID API_HASH BOT_TOKEN MONGO_URI GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET ADMIN_IDS; do
    if [ -z "${!VAR}" ]; then
        MISSING+=("$VAR")
    fi
done

if [ ${#MISSING[@]} -ne 0 ]; then
    echo "❌ Missing required env vars:"
    for v in "${MISSING[@]}"; do echo "     $v"; done
    echo ""
    echo "   Edit .env: nano .env"
    exit 1
fi
echo "✅ All required env vars present"

# ── MongoDB Atlas IP whitelist reminder ──────────────────────
echo ""
echo "⚠️  MongoDB Atlas: Make sure your IP is whitelisted"
echo "   https://cloud.mongodb.com → Network Access → Add IP Address"
echo "   (or use 0.0.0.0/0 for dev)"

# ── Downloads/logs dirs ──────────────────────────────────────
mkdir -p downloads logs
echo "✅ downloads/ and logs/ directories ready"

# ── Done ─────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup complete!"
echo ""
echo "  Run the bot:"
echo "    source venv/bin/activate"
echo "    python main.py"
echo ""
echo "  Or use the run script:"
echo "    ./run.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
