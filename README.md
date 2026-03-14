# GramUploader

Upload Telegram videos directly to YouTube — with AI metadata, YouTube Studio-like management panel, and live progress.

## Features

- **Upload** videos from Telegram to YouTube with live progress
- **Manage** existing YouTube videos (edit, delete, thumbnail, captions, playlists)
- **AI Tools** — title, description & tags via Gemini · captions via Whisper
- **Confirmation screen** before upload — set title, privacy, cancel
- **Queue system** — multiple uploads handled sequentially
- **Free / Premium** plan support with daily upload limits
- **Admin panel** — stats, broadcast, ban, API key management
- **Multi-language** — English & Malayalam (i18n ready)

## Tech Stack

| Layer | Library |
|-------|---------|
| Telegram MTProto | Kurigram (Pyrogram fork) |
| YouTube API | Google API Python Client v3 |
| AI Metadata | Gemini 1.5 Flash (free tier) |
| AI Captions | OpenAI Whisper (local) |
| Database | MongoDB Atlas (Motor async) |
| OAuth2 Server | FastAPI + Uvicorn |
| Deploy | Azure Container Instances |
| Language | Python 3.11+ |

## Project Structure

```
GramUploader/
├── main.py                        # Entry point
├── config.py                      # All env config
├── Dockerfile                     # Azure / Docker deploy
├── deploy.sh                      # Azure ACI deploy script
├── Procfile                       # Railway deploy (alternative)
│
├── core/
│   ├── bot.py                     # Pyrogram client singleton
│   ├── filters.py                 # Custom filters (is_admin, is_youtube_connected)
│   └── middlewares.py             # Rate limit, ban check, auto user upsert
│
├── database/
│   ├── db.py                      # MongoDB connection + repo instances
│   ├── models.py                  # Pydantic models (User, Upload, APIKey)
│   └── repositories/
│       ├── user_repo.py           # User CRUD
│       ├── upload_repo.py         # Upload CRUD
│       └── apikey_repo.py         # API key rotation
│
├── handlers/
│   ├── __init__.py                # register_all() — order matters (manage > ai > start > video > admin)
│   ├── manage.py                  # /manage — YouTube Studio panel
│   ├── ai.py                      # /ai — Gemini metadata + Whisper captions
│   ├── start.py                   # /start /connect /history /quota /settings
│   ├── video.py                   # Video upload handler + confirmation flow
│   └── admin.py                   # /stats /ban /broadcast /addkey
│
├── services/
│   ├── queue_worker.py            # Background upload queue processor
│   ├── youtube_uploader.py        # Resumable YouTube upload + token refresh
│   ├── youtube_manager.py         # YouTube Studio API (edit/delete/captions/playlists)
│   ├── ai_service.py              # Gemini metadata + Whisper transcription
│   └── oauth_server.py            # FastAPI Google OAuth2 callback server
│
├── utils/
│   ├── messages.py                # All bot message templates
│   ├── keyboards.py               # All inline keyboard layouts
│   ├── manage/
│   │   ├── keyboards.py           # /manage panel keyboards
│   │   └── messages.py            # /manage panel messages
│   ├── fonts.py                   # Unicode small caps sc() utility
│   ├── formatters.py              # Progress bar, file size, status emoji
│   ├── validators.py              # File type, size, title sanitization
│   ├── logger.py                  # Rotating file + console logger
│   └── i18n.py                    # Multi-language support (en/ml)
│
├── locales/
│   ├── en.json                    # English strings
│   └── ml.json                    # Malayalam strings
│
└── tests/                         # (WIP)
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

### 4. Gemini API Key (AI features)

- Visit https://aistudio.google.com
- Create API key → free tier available
- Set as `GEMINI_API_KEY`

### 5. Environment Variables

```bash
cp .env.example .env
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

# AI
GEMINI_API_KEY=your_gemini_api_key
WHISPER_MODEL=base
```

### 6. Install & Run Locally

```bash
pip install -r requirements.txt
python main.py
```

---

## Deploy on Azure (Recommended)

> Requires Azure CLI and an active Azure subscription.
> Azure for Students $100 credit — estimated ~$3.67/month.

### 1. Install Azure CLI (Linux)

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az login
```

### 2. Edit deploy.sh

```bash
REGISTRY_NAME="youruniquename"   # globally unique, lowercase, no hyphens
DNS_LABEL="gramuploader-oauth"   # subdomain for OAuth callback
```

### 3. Run Deploy Script

```bash
chmod +x deploy.sh
./deploy.sh
```

The script will:
1. Create Resource Group + Container Registry
2. Build & push Docker image
3. Show OAuth redirect URI → add to Google Console, press Enter
4. Deploy container with all env vars
5. Print management commands

### 4. Useful Commands

```bash
# Live logs
az container logs -g bots-rg -n gramuploader --follow

# Status
az container show -g bots-rg -n gramuploader --query instanceView.state

# Restart
az container restart -g bots-rg -n gramuploader

# Delete
az container delete -g bots-rg -n gramuploader --yes
```

### Cost Estimate

| Resource | Spec | Monthly |
|---|---|---|
| GramUploader | 0.5 vCPU, 512MB RAM | ~$3.50 |
| MongoDB Atlas | Free tier (512MB) | $0.00 |
| Container Registry | Basic SKU | ~$0.17 |
| **Total** | | **~$3.67/month** |

$100 credit → ~**27 months**

---

## Deploy on Railway (Alternative)

```bash
railway login
railway init
railway up
```

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Main menu |
| `/connect` | Link YouTube channel via Google OAuth |
| `/manage` | YouTube Studio panel |
| `/ai` | AI Tools (Gemini metadata + Whisper captions) |
| `/history` | Recent upload history (paginated) |
| `/quota` | Today's upload usage |
| `/settings` | Preferences: privacy, language, auto-title |
| `/cancel` | Cancel active FSM input |

### Admin Commands

| Command | Description |
|---------|-------------|
| `/stats` | Bot statistics + admin panel |
| `/ban <id>` | Ban a user |
| `/unban <id>` | Unban a user |
| `/addkey <key>` | Add YouTube API key |
| `/broadcast` | Broadcast to all users (reply to a message) |

---

## User Flow

```
/start
  └── Connect YouTube → Google OAuth2
        └── Send video
              └── Confirmation screen
                    ├── ✨ AI Suggest → Gemini generates title/desc/tags
                    ├── ✏️ Edit Title / 🔒 Privacy
                    └── Upload Now → Queue → Download → Upload → YouTube link
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

## AI Tools

```
/ai
  ├── ✨ AI Metadata → send hint → Gemini generates title + description + tags
  └── 🎙 AI Captions → send video → Whisper transcribes → .srt file returned
```

Whisper model sizes (set via `WHISPER_MODEL`):

| Model | RAM | Speed | Accuracy |
|---|---|---|---|
| `tiny` | ~390MB | fastest | basic |
| `base` | ~500MB | fast | good ✅ |
| `small` | ~1GB | medium | better |
| `medium` | ~3GB | slow | best |

---

## Known Limitations

- YouTube Data API free quota: ~6 uploads/day per key (add more via `/addkey`)
- Telegram MTProto: up to 2GB per file (4GB with Telegram Premium)
- Cards, End Screens, Audio replacement — not available via YouTube Data API
- OAuth token auto-refreshed on next use
- In-memory queue — bot restart clears pending uploads (use Redis for production)
- Whisper captions: max recommended file size 500MB for reasonable speed

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
# or
git checkout -b fix/bug-description
```

Branch naming:
- `feature/` — new feature
- `fix/` — bug fix
- `docs/` — documentation only
- `refactor/` — code cleanup, no behavior change

### 3. Code Style

- All DB access via repository pattern — no direct collection calls in handlers
- New message templates → `utils/messages.py` only
- New keyboards → `utils/keyboards.py` or `utils/manage/keyboards.py`
- Use `log.info()` / `log.error()` — no bare `print()`
- Never commit `.env` or `*.session` files

### 4. Commit Format

```
feat: add scheduled publish support
fix: oauth token refresh not awaited
docs: update Azure deploy steps
refactor: move progress bar to formatters
```

---

## Changelog

### v2.1.0 — 2026-03-14

**Bug Fixes**
- `handlers/start.py` — `cb_manage_open` and `cb_ai_menu` were outside `register()` due to wrong indentation; fixed
- `services/youtube_uploader.py` — replaced non-existent `get_youtube_token`, `save_youtube_token`, `get_active_api_key`, `increment_key_usage` with correct `user_repo` / `apikey_repo` calls
- `services/youtube_uploader.py` — token refresh now properly awaited via `asyncio.to_thread`
- `services/oauth_server.py` — replaced non-existent `save_youtube_token`, `upsert_user` with `user_repo.set_youtube_token()` / `user_repo.upsert()`
- `services/oauth_server.py` — `refresh_token or ""` guard added for first-time auth

**Structure**
- `services/yt_manager.py` → renamed to `services/youtube_manager.py`
- `utils/manager_keyboards.py` → moved to `utils/manage/keyboards.py`
- `utils/manager_messages.py` → moved to `utils/manage/messages.py`
- `handlers/video_handler.py` (old v1 file) — deleted
- Junk folder `{handlers,services,...}/` — deleted
- All imports updated to reflect new paths

### v2.0.0 — 2026-03-13

**YouTube Studio Panel**
- `/manage` command — full video management from Telegram
- Edit title, description, tags, category, privacy
- Set custom thumbnail, upload/delete captions (.srt)
- Playlist management, advanced settings, channel stats

**AI Features**
- `/ai` command — Gemini 1.5 Flash metadata generation
- Whisper speech-to-text captions (.srt output)
- `✨ AI Suggest` + `🔄 Regen Title` buttons on upload confirm screen

**Other**
- `fonts.py` — `sc()` Unicode small caps utility
- New `/start` message design
- Azure Container Instances deploy (`Dockerfile` + `deploy.sh`)
- `.gitignore` added

### v1.0.0 — 2026-02-01

**Initial Release**
- Telegram → YouTube upload with live progress
- Upload confirmation screen
- In-memory queue worker
- Google OAuth2 via FastAPI
- MongoDB Atlas with Motor async
- Free / Premium plans
- Admin panel, history, quota, settings
- English & Malayalam support
