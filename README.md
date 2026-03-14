# GramUploader

Upload Telegram videos directly to YouTube — with a full YouTube Studio-like management panel, all from Telegram.

## Features

- **Upload** videos from GramUploader with live progress
- **Manage** existing YouTube videos (edit, delete, thumbnail, captions, playlists)
- **Confirmation screen** before upload — set title, privacy, category
- **Queue system** — multiple uploads handled sequentially
- **Free / Premium** plan support with daily upload limits
- **Admin panel** — stats, broadcast, ban, API key management
- **Multi-language** — English & Malayalam (i18n ready)
- **YouTube Studio-like** `/manage` panel

## Tech Stack

| Layer | Library |
|-------|---------|
| Telegram MTProto | Kurigram (Pyrogram fork) |
| YouTube API | Google API Python Client v3 |
| Database | MongoDB Atlas (Motor async) |
| OAuth2 Server | FastAPI + Uvicorn |
| Deploy | Azure Container Instances |
| Language | Python 3.11+ |

## Project Structure

```
gramuploader/
├── main.py                    # Entry point
├── config.py                  # All env config
├── Dockerfile                 # Azure / Docker deploy
├── deploy.sh                  # Azure ACI deploy script
├── Procfile                   # Railway deploy (alternative)
│
├── core/
│   ├── bot.py                 # Pyrogram client singleton
│   ├── filters.py             # Custom filters (is_admin, is_youtube_connected)
│   └── middlewares.py         # Rate limit, ban check, auto user upsert
│
├── database/
│   ├── db.py                  # MongoDB connection + repo instances
│   ├── models.py              # Pydantic models (User, Upload, APIKey)
│   └── repositories/
│       ├── user_repo.py       # User CRUD
│       ├── upload_repo.py     # Upload CRUD
│       └── apikey_repo.py     # API key rotation
│
├── handlers/
│   ├── __init__.py            # register_all() — registers all handlers
│   ├── manage.py              # /manage — YouTube Studio panel (register first)
│   ├── start.py               # /start /connect /history /quota /settings
│   ├── video.py               # Video upload handler + confirmation flow
│   └── admin.py               # /stats /ban /broadcast /addkey
│
├── services/
│   ├── queue_worker.py        # Background upload queue processor
│   ├── youtube_uploader.py    # Resumable YouTube upload + token refresh
│   ├── yt_manager.py          # YouTube Studio API (edit/delete/captions/playlists)
│   └── oauth_server.py        # FastAPI Google OAuth2 callback server
│
├── utils/
│   ├── messages.py            # All bot message templates
│   ├── keyboards.py           # All inline keyboard layouts
│   ├── manager_messages.py    # /manage panel message templates
│   ├── manager_keyboards.py   # /manage panel keyboard layouts
│   ├── fonts.py               # Unicode small caps sc() utility
│   ├── formatters.py          # Progress bar, file size, status emoji
│   ├── validators.py          # File type, size, title sanitization
│   ├── logger.py              # Rotating file + console logger
│   └── i18n.py                # Multi-language support (en/ml)
│
├── locales/
│   ├── en.json                # English strings
│   └── ml.json                # Malayalam strings
│
└── tests/                     # (WIP)
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
cp .env.example .env
nano .env   # fill in all values
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
```

### 5. Install & Run Locally

```bash
pip install -r requirements.txt
python main.py
```

---

## Deploy on Azure (Recommended)

> Requires Azure CLI and an active Azure subscription.
> Azure for Students $100 credit — estimated cost ~$3.67/month.

### 1. Install Azure CLI (Linux)

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az login
```

### 2. Edit deploy.sh

Open `deploy.sh` and update the config at the top:

```bash
REGISTRY_NAME="youruniquename"   # globally unique, lowercase, no hyphens
DNS_LABEL="your-bot-oauth"       # subdomain for OAuth callback URL
```

### 3. Run Deploy Script

```bash
chmod +x deploy.sh
./deploy.sh
```

The script will:
1. Create Resource Group + Container Registry
2. Build & push Docker image to Azure
3. Show OAuth redirect URI → add it to Google Console, then press Enter
4. Deploy the container with all env vars injected
5. Print useful management commands

### 4. Update Google Console

When the script pauses, add the shown URL to:
> Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client → Authorized redirect URIs

### 5. Useful Commands

```bash
# Live logs
az container logs -g bots-rg -n gramuploader --follow

# Check status
az container show -g bots-rg -n gramuploader --query instanceView.state

# Restart
az container restart -g bots-rg -n gramuploader

# Delete
az container delete -g bots-rg -n gramuploader --yes
```

### Azure Cost Estimate

| Resource | Spec | Monthly |
|---|---|---|
| TG→YouTube Bot | 0.5 vCPU, 512MB RAM | ~$3.50 |
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

Set all `.env` values in Railway dashboard → Variables.
Railway runs both the bot and OAuth server via `Procfile`.

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Main menu |
| `/connect` | Link YouTube channel via Google OAuth |
| `/manage` | YouTube Studio panel |
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
              └── Confirmation screen (title / privacy / cancel)
                    └── Upload Now → Queue → Download → Upload → YouTube link
```

## /manage Panel Flow

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

## Known Limitations

- YouTube Data API free quota: ~6 uploads/day per key (add more via `/addkey`)
- Telegram Bot API file size: 50MB (Kurigram MTProto: up to 2GB / 4GB with Premium)
- Cards, End Screens, Audio replacement — not available via YouTube Data API
- OAuth token expires — auto-refreshed on next use
- In-memory queue — bot restart clears pending uploads (use Redis for production)

---

## Contributing

Contributions are welcome! Please follow these steps:

### 1. Fork & Clone

```bash
git clone https://github.com/yourusername/gramuploader.git
cd gramuploader
```

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

Branch naming convention:
- `feature/` — new feature
- `fix/` — bug fix
- `docs/` — documentation only
- `refactor/` — code cleanup, no behavior change

### 3. Code Style

- Follow async/await pattern throughout
- Add new message templates to `utils/messages.py` — never hardcode strings in handlers
- Add new keyboards to `utils/keyboards.py` or `utils/manager_keyboards.py`
- Use `log.info()` / `log.error()` from `utils/logger.py` — no bare `print()`
- Use repository pattern for all DB access — no direct collection calls in handlers
- Never commit `.env`, `*.session`, or downloaded media files

### 4. Test Locally

```bash
pip install -r requirements.txt
python main.py
```

### 5. Submit PR

```bash
git add .
git commit -m "feat: short description"
git push origin feature/your-feature-name
```

Open a Pull Request with a clear description of what changed and why.

### Commit Message Format

```
feat: add scheduled publish support
fix: queue worker missing privacy param
docs: update Azure deploy steps
refactor: move progress bar to formatters
```

---

## Changelog

### v2.0.0 — 2026-03-13

**YouTube Studio Panel**
- `/manage` command — full video management from Telegram
- Edit title, description, tags, category, privacy
- Set custom thumbnail by sending a photo
- Upload / delete caption tracks (.srt)
- Add videos to existing or new playlists
- Advanced settings: made-for-kids, embeddable, license, scheduled publish
- Channel stats panel (subscribers, views, video count)
- Video stats per video (views, likes, comments)
- Delete video with confirmation screen

**Improvements**
- `fonts.py` — `sc()` Unicode small caps converter utility
- New `/start` message with small caps styling and cleaner layout
- Azure Container Instances support — `Dockerfile` + `deploy.sh`
- `.gitignore` added — session files and `.env` protected
- Updated `requirements.txt` — added `pymongo`, `pydantic` explicitly

**Bug Fixes**
- `queue_worker.py` — fixed old non-existent DB function calls (`update_upload`, `get_upload`)
- `queue_worker.py` — `privacy` param was missing from upload job
- `queue_worker.py` — `status_msg.edit()` → `edit_text()`; division-by-zero guard in progress
- `models.py` — mutable default `dict` fixed with `Field(default_factory=dict)`
- `models.py` — `settings` field added to `User` model
- `user_repo.py` — `find()` now sets default `settings: {}` + error logging
- `handlers/` — `manage` registered first so FSM handlers take priority over `video.py`
- `manage.py` — all imports moved to top; removed stale bottom-of-file import

### v1.0.0 — 2026-02-01

**Initial Release**
- Telegram → YouTube video upload with live download + upload progress
- Upload confirmation screen — set title, privacy, cancel before uploading
- In-memory queue worker for sequential uploads
- Google OAuth2 connect flow via FastAPI callback server
- MongoDB Atlas with Motor async driver
- Free / Premium plan with configurable daily upload limits
- Admin panel: stats, ban/unban, broadcast, YouTube API key rotation
- `/history` paginated upload history
- `/quota` today's usage
- `/settings` privacy, language, auto-title preferences
- Multi-language support: English & Malayalam (i18n via JSON locales)
