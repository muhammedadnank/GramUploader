# GramUploader

Upload Telegram videos directly to YouTube — with a YouTube Studio-like management panel, dual-stage live progress, and rich upload confirmations.

## Features

- **Upload** videos from Telegram to YouTube with dual-stage live progress (download + upload bars side-by-side)
- **YouTube Shorts support** — videos ≤ 3 min (180s) auto-detected; toggle on confirmation screen to upload as Short (`#Shorts` appended, privacy forced public); send a thumbnail photo to have it prepended as the first 2 seconds via ffmpeg
- **Rich confirmation screen** — title, size, duration, file type, privacy, Shorts toggle before upload
- **Upload done card** — YouTube thumbnail photo sent automatically on completion
- **Manage** existing YouTube videos (edit, delete, thumbnail, captions, playlists)
- **Queue system** — multiple uploads handled sequentially with position indicator
- **Free / Premium** plan support with daily upload limits and reset countdown
- **Settings panel** — shows connected YouTube channel name, default privacy, language, auto-title
- **Admin panel** — stats (with live queue depth), broadcast, ban, API key management
- **Multi-language** — English & Malayalam (i18n ready)
- **Security** — rate limiting, ban system, maintenance mode, OAuth token auto-refresh with expiry tracking

## Tech Stack

| Layer | Library |
|-------|---------|
| Telegram MTProto | Kurigram (Pyrogram fork) |
| YouTube API | Google API Python Client v3 |
| Database | MongoDB Atlas (Motor async) |
| OAuth2 Server | FastAPI + Uvicorn |
| Deploy | Azure ACI · Render · Railway |
| Language | Python 3.11+ |

## Project Structure

```
GramUploader/
├── main.py                        # Entry point + startup validation + stuck-job recovery + DB indexes
├── config.py                      # All env config
├── Dockerfile                     # Docker / Azure ACI deploy
├── deploy.sh                      # Azure ACI one-click deploy script
├── render.yaml                    # Render deploy config
├── Procfile                       # Render / Railway process definition
├── setup_local.sh                 # Local Linux setup script
├── run.sh                         # Local quick-start script
│
├── .github/
│   ├── dependabot.yml             # Daily dependency update checks
│   └── workflows/
│       └── security-scan.yml      # pip-audit + Safety dependency scan
│
├── core/
│   ├── bot.py                     # Pyrogram client singleton
│   ├── filters.py                 # Custom filters (is_admin, is_youtube_connected)
│   └── middlewares.py             # Rate limit, ban check, auto user upsert, apply_cb_middlewares()
│
├── database/
│   ├── db.py                      # MongoDB connection + repo instances + ensure_indexes()
│   ├── models.py                  # Pydantic models (User, Upload, APIKey, YouTubeToken with expiry)
│   └── repositories/
│       ├── user_repo.py           # User CRUD + iter_all_ids() + clear_youtube_token()
│       ├── upload_repo.py         # Upload CRUD + stuck-job query (PENDING/DOWNLOADING/UPLOADING)
│       └── apikey_repo.py         # API key rotation
│
├── handlers/
│   ├── __init__.py                # register_all() — callbacks first, fsm_router last
│   ├── fsm_router.py              # Central FSM: sole text/photo/document handler
│   ├── manage.py                  # /manage — YouTube Studio panel (callbacks only)
│   ├── start.py                   # /start /connect /disconnect /history /quota /queue /settings
│   ├── video.py                   # Video upload handler + confirmation flow (duration, file type)
│   └── admin.py                   # /stats /ban /broadcast /addkey
│
├── services/
│   ├── queue_worker.py            # Background upload queue processor + thumbnail done card
│   ├── youtube_uploader.py        # Resumable YouTube upload + token refresh with expiry
│   ├── youtube_manager.py         # YouTube Studio API (edit/delete/captions/playlists)
│   ├── oauth_server.py            # FastAPI Google OAuth2 callback server + Telegram notify
│   └── video_processor.py         # ffmpeg thumbnail prepend for Shorts
│
├── utils/
│   ├── messages.py                # All bot message templates (dual progress, quota countdown, channel name)
│   ├── keyboards.py               # All inline keyboard layouts
│   ├── manage/
│   │   ├── __init__.py
│   │   ├── keyboards.py           # /manage panel keyboards
│   │   └── messages.py            # /manage panel messages
│   ├── formatters.py              # Progress bar, file size, ETA, status emoji
│   ├── validators.py              # File type, size, title sanitization (strips control chars)
│   ├── logger.py                  # Rotating file + console logger
│   └── i18n.py                    # Multi-language support (en/ml)
│
├── locales/
│   ├── en.json                    # English strings
│   └── ml.json                    # Malayalam strings
│
├── docs/
│   └── CHANGELOG.md               # Full version history
│
└── SECURITY.md                    # Vulnerability reporting policy
```

---

## Setup

### 1. Telegram

- Get `API_ID` and `API_HASH` from https://my.telegram.org
- Create bot via @BotFather → get `BOT_TOKEN`

### 2. Google Cloud Console

- Create project → Enable **YouTube Data API v3**
- Create **OAuth 2.0 credentials** → Web application
- Add Authorized redirect URI: `https://yourdomain.com/callback`
- Copy `CLIENT_ID` and `CLIENT_SECRET`

### 3. MongoDB Atlas

- Create free cluster at https://mongodb.com/atlas
- Get connection string → set as `MONGO_URI`

### 4. Environment Variables

```bash
cp core/env.example .env
nano .env
```

```env
# Telegram
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
ADMIN_IDS=123456789,987654321

# MongoDB
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
DB_NAME=gramuploader

# Google OAuth2
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/callback
OAUTH_BASE_URL=https://yourdomain.com

# Bot settings
FREE_UPLOADS_PER_DAY=2
MAX_FILE_SIZE_MB=2000
MAINTENANCE_MODE=false

# UI / Links
START_IMAGE_URL=https://your-image-url.jpg
OWNER_URL=https://t.me/yourusername
SUPPORT_URL=https://t.me/yoursupport
PREMIUM_URL=https://t.me/yoursupport

# OAuth server (optional — defaults work for most deploys)
OAUTH_SERVER_HOST=0.0.0.0
OAUTH_SERVER_PORT=8080
```

### 5. Install & Run Locally

```bash
chmod +x setup_local.sh run.sh
./setup_local.sh

# Every time after
./run.sh
```

Or manually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## Deploy Options

### Option 1 — Azure Container Instances (Recommended for Students)

> Azure for Students: $100 free credit → ~27 months at ~$3.67/month.

**1. Install Azure CLI**

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az login
```

**2. Edit `deploy.sh`**

```bash
REGISTRY_NAME="youruniquename"   # globally unique, lowercase, no hyphens
DNS_LABEL="gramuploader-oauth"   # subdomain for OAuth callback URL
```

**3. Run**

```bash
chmod +x deploy.sh
./deploy.sh
```

**Useful commands**

```bash
az container logs -g bots-rg -n gramuploader --follow
az container show -g bots-rg -n gramuploader --query instanceView.state
az container restart -g bots-rg -n gramuploader
az container delete -g bots-rg -n gramuploader --yes
```

**Cost**

| Resource | Spec | Monthly |
|---|---|---|
| GramUploader | 0.5 vCPU, 512MB RAM | ~$3.50 |
| MongoDB Atlas | Free tier | $0.00 |
| Container Registry | Basic SKU | ~$0.17 |
| **Total** | | **~$3.67/month** |

---

### Option 2 — Render

> Free tier available. `render.yaml` included — auto-detected on deploy.

**1. Push repo to GitHub**

**2. Connect on Render**

- Go to https://render.com → New → Web Service
- Connect GitHub repo → Render auto-detects `render.yaml`

**3. Set Environment Variables**

```
API_ID, API_HASH, BOT_TOKEN, ADMIN_IDS
MONGO_URI
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = https://gramuploader.onrender.com/callback
OAUTH_BASE_URL      = https://gramuploader.onrender.com
START_IMAGE_URL, OWNER_URL, SUPPORT_URL, PREMIUM_URL
```

**4. Update Google Console**

Add `https://gramuploader.onrender.com/callback` to Authorized redirect URIs.

> ℹ️ The bot will sleep after 15 minutes of inactivity on free tier.

---

### Option 3 — Railway

```bash
railway login
railway init
railway up
```

Set all env vars in Railway dashboard → Variables.

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Main menu |
| `/connect` | Link YouTube channel via Google OAuth |
| `/disconnect` | Unlink your YouTube account |
| `/manage` | YouTube Studio panel |
| `/history` | Recent upload history (paginated, with dates) |
| `/quota` | Today's upload usage + reset countdown |
| `/queue` | Check current upload queue size |
| `/settings` | Preferences — shows linked channel name |
| `/cancel` | Cancel active FSM input (works anywhere) |

### Admin Commands

| Command | Description |
|---------|-------------|
| `/stats` | Bot statistics + admin panel (includes live queue depth) |
| `/ban <id>` | Ban a user |
| `/unban <id>` | Unban a user |
| `/user <id>` | View user details, ban/unban, change plan |
| `/addkey <key>` | Add YouTube API key |
| `/deletekey <key>` | Deactivate a YouTube API key |
| `/setpremium <id>` | Upgrade user to Premium |
| `/setfree <id>` | Downgrade user to Free |
| `/broadcast` | Broadcast to all users (reply to a message) |

---

## User Flow

```
/start
  └── Connect YouTube → Google OAuth2 → ✅ Telegram notification sent
        └── Send video
              └── Confirmation screen
                    ├── ✏️ Edit Title → send new title as message
                    ├── 🔒 Privacy → Public / Private / Unlisted
                    ├── 📱 Short: ON/OFF → auto-ON if ≤180s
                    │         ON: appends #Shorts to title, forces Public privacy
                    ├── 🖼 Add Thumbnail → send photo → prepended as first 2s via ffmpeg
                    └── Upload Now
                          ├── 📥 Download:  [██████░░░░] 60%
                          │   📤 Upload:    [░░░░░░░░░░]  0%
                          │         ↓
                          ├── 📥 Download:  [██████████] ✅
                          │   📤 Upload:    [████████░░] 80%
                          │         ↓
                          └── 🖼 Thumbnail card + YouTube link + Manage button

/disconnect → Unlinks YouTube account (token wiped from DB)
```

## /manage Panel

```
/manage → Video list (paginated)
  └── Tap video → Video panel
        ├── ✏️ Edit Title / Description / Tags
        ├── 🗂 Category (15 categories)
        ├── 🔒 Privacy (Public / Private / Unlisted)
        ├── 🖼 Set Thumbnail (send photo)
        ├── 📋 Playlist (select or create)
        ├── 📝 Captions (upload .srt / delete)
        ├── 📊 Stats (views / likes / comments)
        ├── ⚙️ Advanced (kids / embed / license / schedule)
        ├── 🔗 Open on YouTube
        └── 🗑 Delete (with confirmation)
```

---

## Architecture Note — FSM Routing

Pyrogram fires the **first** matching handler and ignores all subsequent ones. GramUploader solves this with a dedicated `handlers/fsm_router.py` registered **last**, acting as the sole handler for text, photo, and document messages. It routes based on per-user state:

```
Text message received
  ├── user in _pending_edit?        → upload title edit
  └── manage state active?          → edit title / desc / tags / schedule / playlist / caption lang

Document received
  ├── manage state == CAPTION_FILE? → .srt caption upload
  └── (no state)                    → normal video upload flow

Photo received
  └── manage state == THUMBNAIL?    → set video thumbnail
```

All command and callback query handlers are registered before `fsm_router`, so they always take priority.

---

## Known Limitations

- YouTube Data API free quota: ~6 uploads/day per key (add more keys via `/addkey`)
- Telegram MTProto file size: up to 2GB (4GB with Telegram Premium)
- Cards, End Screens, Audio replacement — not available via YouTube Data API
- OAuth token auto-refreshed on next use (expiry tracked in DB since v2.7.0)
- In-memory queue — bot restart marks pending uploads as failed (use Redis for production)
- Render free tier: bot sleeps after 15 min inactivity, first wake-up is slow
- YouTube thumbnail in done card may take a few seconds to appear after upload (YouTube processing)

---

## Security

See [SECURITY.md](SECURITY.md) for the vulnerability reporting policy.

---

## Contributing

### 1. Fork & Clone

```bash
git clone https://github.com/muhammedadnank/GramUploader.git
cd GramUploader
```

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
git checkout -b fix/bug-description
```

Branch naming: `feature/` · `fix/` · `docs/` · `refactor/`

### 3. Code Style

- All DB access via repository pattern — no direct collection calls in handlers
- New message templates → `utils/messages.py` only
- New keyboards → `utils/keyboards.py` or `utils/manage/keyboards.py`
- FSM state → `handlers/fsm_router.py` only; never register `filters.text` in other handlers
- Use `log.info()` / `log.error()` — no bare `print()`
- Never commit `.env` or `*.session` files

### 4. Commit Format

```
feat: add scheduled publish support
fix: oauth token refresh not awaited
docs: update Render deploy steps
refactor: move progress bar to formatters
```

---

## Changelog

See [docs/CHANGELOG.md](docs/CHANGELOG.md) for full version history.

Latest: **v2.7.0** · [v2.6.0] · [v2.5.0] · [v2.4.0] · [v2.3.0] · [v2.2.0] · [v2.1.0] · [v2.0.0] · [v1.0.0]
