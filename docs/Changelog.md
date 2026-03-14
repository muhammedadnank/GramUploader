# Changelog

All notable changes to GramUploader are documented here.
Format: `[vX.Y.Z] — YYYY-MM-DD`

---

## [v2.1.0] — 2026-03-14

### Bug Fixes

- **`handlers/start.py`** — `cb_manage_open` and `cb_ai_menu` callbacks were accidentally defined outside `register()` due to indentation error; fixed
- **`services/youtube_uploader.py`** — removed calls to non-existent DB functions (`get_youtube_token`, `save_youtube_token`, `get_active_api_key`, `increment_key_usage`); replaced with correct `user_repo.get_youtube_token()` / `user_repo.set_youtube_token()` / `apikey_repo.get_active()` / `apikey_repo.increment_usage()`
- **`services/youtube_uploader.py`** — token refresh (`creds.refresh()`) was not awaited; fixed with `asyncio.to_thread`
- **`services/oauth_server.py`** — removed calls to non-existent `save_youtube_token` and `upsert_user`; replaced with `user_repo.set_youtube_token()` and `user_repo.upsert()`
- **`services/oauth_server.py`** — added `refresh_token or ""` guard for first-time OAuth (token may be None)

### Structure

- `services/yt_manager.py` → renamed to `services/youtube_manager.py` (consistent with `youtube_uploader.py`)
- `utils/manager_keyboards.py` → moved to `utils/manage/keyboards.py`
- `utils/manager_messages.py` → moved to `utils/manage/messages.py`
- `utils/manage/__init__.py` created
- `handlers/video_handler.py` (old v1 leftover) deleted
- Junk folder `{handlers,services,database,utils}/` deleted
- All imports updated to reflect new paths

### Render Deploy Support

- `render.yaml` added — auto-detected by Render on connect
- `Procfile` fixed — was `cmd1 & cmd2` (broken); now `web: python main.py`
- `config.py` — `OAUTH_SERVER_PORT` now reads `$PORT` env var first (required by Render)
- `Dockerfile` — added `ffmpeg`, `g++`, `python3-dev`; created `/app/logs` dir
- `services/ai_service.py` — RAM availability check before loading Whisper model; lazy import with clear error if `openai-whisper` not installed
- `requirements.txt` — added `psutil` for RAM check

### Local Deploy Support

- `setup_local.sh` added — installs `ffmpeg`, creates `venv`, validates `.env`, creates `downloads/` and `logs/` dirs
- `run.sh` added — activates `venv` and starts bot
- `utils/logger.py` — log file path changed from relative `bot.log` to absolute `logs/bot.log` inside project root (fixes wrong location when running from different directories)

---

## [v2.0.0] — 2026-03-13

### YouTube Studio Panel (`/manage`)

- New `/manage` command — full video management directly from Telegram
- Edit title, description, tags, category (15 categories), privacy
- Set custom thumbnail by sending a photo
- Upload `.srt` caption files / delete existing caption tracks
- Add videos to existing or new playlists
- Advanced settings: made-for-kids toggle, embeddable toggle, license (Standard / CC), scheduled publish
- Channel stats panel (subscribers, total views, video count)
- Per-video stats (views, likes, comments, favorites)
- Delete video with confirmation screen
- Paginated video list (8 per page, next/prev navigation)

### AI Features (`/ai`)

- New `/ai` command with Gemini 1.5 Flash (free tier) + Whisper
- AI metadata generation: title (≤70 chars), description (150–300 chars), tags (up to 8)
- AI caption generation: Whisper transcribes video audio → `.srt` file returned
- `✨ AI Suggest` button on upload confirmation screen — auto-fills title/desc/tags
- `🔄 Regen Title` button — regenerate title only
- Language-aware generation (English / Malayalam)
- RAM guard before Whisper model load

### Other Changes

- `utils/fonts.py` — `sc()` utility converts regular text to Unicode small caps
- `/start` message redesigned with small caps styling and cleaner layout
- `🤖 AI Tools` button added to `/start` menu
- `🎬 Manage Videos` button added to `/start` menu
- Azure Container Instances deploy: `Dockerfile` + `deploy.sh`
- `.gitignore` added — protects `.env`, `*.session`, `downloads/`, `logs/`
- `.dockerignore` added

---

## [v1.0.0] — 2026-02-01

### Initial Release

- Telegram → YouTube video upload with live download + upload progress bars
- Upload confirmation screen — set title, change privacy, cancel before uploading
- In-memory queue worker — sequential upload processing
- Google OAuth2 connect flow via FastAPI callback server
- MongoDB Atlas with Motor async driver
- Repository pattern — `UserRepository`, `UploadRepository`, `APIKeyRepository`
- Pydantic models — `User`, `Upload`, `APIKey`, `YouTubeToken`
- Free / Premium plan with configurable daily upload limits (`FREE_UPLOADS_PER_DAY`)
- YouTube API key rotation — auto-switches when daily quota (~8000 units) exceeded
- Admin panel: `/stats`, `/ban`, `/unban`, `/addkey`, `/broadcast`
- `/history` — paginated upload history (5 per page)
- `/quota` — today's upload count with progress bar
- `/settings` — default privacy, language, auto-title from caption
- Rate limiter — 5 requests per 10 seconds per user
- Maintenance mode toggle (admin only)
- Multi-language support: English & Malayalam via JSON locales (`locales/en.json`, `locales/ml.json`)
- Rotating file logger — `logs/bot.log` (5MB × 3 backups)
