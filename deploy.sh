#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Azure Deploy Script — GramUploader
# Run: chmod +x deploy.sh && ./deploy.sh
# ─────────────────────────────────────────────────────────────

set -e  # exit on any error

# ── CONFIG — change these ─────────────────────────────────────
RESOURCE_GROUP="bots-rg"
REGISTRY_NAME="mybotregistry"        # must be globally unique, lowercase
CONTAINER_NAME="gramuploader"
IMAGE_NAME="gramuploader"
LOCATION="eastus"
CPU="0.5"
MEMORY="1"
OAUTH_PORT="8080"
DNS_LABEL="tg-youtube-oauth"         # → tg-youtube-oauth.eastus.azurecontainer.io

# ── Load .env ─────────────────────────────────────────────────
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✅ Loaded .env"
else
    echo "❌ .env file not found. Copy .env.example → .env and fill values."
    exit 1
fi

# ── Required env check ────────────────────────────────────────
REQUIRED=(API_ID API_HASH BOT_TOKEN MONGO_URI GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET ADMIN_IDS)
for var in "${REQUIRED[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required env var: $var"
        exit 1
    fi
done
echo "✅ All required env vars present"

# ── Step 1: Login check ───────────────────────────────────────
echo ""
echo "── Step 1: Azure login ──────────────────────────"
az account show > /dev/null 2>&1 || az login
echo "✅ Logged in: $(az account show --query name -o tsv)"

# ── Step 2: Resource Group ────────────────────────────────────
echo ""
echo "── Step 2: Resource Group ───────────────────────"
az group create --name $RESOURCE_GROUP --location $LOCATION --output none
echo "✅ Resource group: $RESOURCE_GROUP"

# ── Step 3: Container Registry ────────────────────────────────
echo ""
echo "── Step 3: Container Registry ───────────────────"
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $REGISTRY_NAME \
    --sku Basic \
    --admin-enabled true \
    --output none 2>/dev/null || echo "  (registry already exists)"
echo "✅ Registry: $REGISTRY_NAME"

# ── Step 4: Build & Push Image ────────────────────────────────
echo ""
echo "── Step 4: Build & Push Docker Image ────────────"
az acr build \
    --registry $REGISTRY_NAME \
    --image $IMAGE_NAME:latest \
    .
echo "✅ Image built and pushed"

# ── Step 5: Get Registry Credentials ─────────────────────────
echo ""
echo "── Step 5: Fetching registry credentials ────────"
ACR_SERVER="$REGISTRY_NAME.azurecr.io"
ACR_USER=$(az acr credential show -n $REGISTRY_NAME --query username -o tsv)
ACR_PASS=$(az acr credential show -n $REGISTRY_NAME --query passwords[0].value -o tsv)
echo "✅ Registry credentials ready"

# ── Step 6: OAuth redirect URI ────────────────────────────────
OAUTH_URL="http://$DNS_LABEL.$LOCATION.azurecontainer.io:$OAUTH_PORT"
echo ""
echo "── Step 6: OAuth Redirect URI ───────────────────"
echo "  ⚠️  Add this to Google Console → Authorized redirect URIs:"
echo "  $OAUTH_URL/callback"
echo ""
read -p "Press Enter when you've added it to Google Console..."

# ── Step 7: Deploy Container ──────────────────────────────────
echo ""
echo "── Step 7: Deploy Container ─────────────────────"

# Delete existing container if it exists
az container delete \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --yes 2>/dev/null || true

az container create \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --image $ACR_SERVER/$IMAGE_NAME:latest \
    --cpu $CPU \
    --memory $MEMORY \
    --restart-policy Always \
    --ports $OAUTH_PORT \
    --ip-address Public \
    --dns-name-label $DNS_LABEL \
    --registry-login-server $ACR_SERVER \
    --registry-username $ACR_USER \
    --registry-password $ACR_PASS \
    --environment-variables \
        API_ID="$API_ID" \
        API_HASH="$API_HASH" \
        BOT_TOKEN="$BOT_TOKEN" \
        MONGO_URI="$MONGO_URI" \
        DB_NAME="${DB_NAME:-gramuploader}" \
        GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" \
        GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" \
        GOOGLE_REDIRECT_URI="$OAUTH_URL/callback" \
        OAUTH_BASE_URL="$OAUTH_URL" \
        ADMIN_IDS="$ADMIN_IDS" \
        FREE_UPLOADS_PER_DAY="${FREE_UPLOADS_PER_DAY:-2}" \
        MAX_FILE_SIZE_MB="${MAX_FILE_SIZE_MB:-2000}" \
        MAINTENANCE_MODE="${MAINTENANCE_MODE:-false}" \
        START_IMAGE_URL="${START_IMAGE_URL:-}" \
        OWNER_URL="${OWNER_URL:-}" \
        SUPPORT_URL="${SUPPORT_URL:-}" \
        PREMIUM_URL="${PREMIUM_URL:-}" \
    --output none

echo "✅ Container deployed!"

# ── Done ──────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════"
echo "✅ DEPLOY COMPLETE"
echo "════════════════════════════════════════════════"
echo ""
echo "🤖 Bot:        $CONTAINER_NAME"
echo "🌐 OAuth URL:  $OAUTH_URL"
echo "📋 Logs:       az container logs -g $RESOURCE_GROUP -n $CONTAINER_NAME --follow"
echo "📊 Status:     az container show  -g $RESOURCE_GROUP -n $CONTAINER_NAME --query instanceView.state"
echo "🔄 Restart:    az container restart -g $RESOURCE_GROUP -n $CONTAINER_NAME"
echo "🗑  Delete:     az container delete  -g $RESOURCE_GROUP -n $CONTAINER_NAME --yes"
echo ""
