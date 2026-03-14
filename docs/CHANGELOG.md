# Changelog

All notable changes to GramUploader are documented here.
Format: `[vX.Y.Z] — YYYY-MM-DD`

---

## [v2.4.0] — 2026-03-14

### Removed

- **Gemini AI integration removed** — `google-generativeai` and all AI metadata generation
  features have been removed to reduce dependencies and eliminate the external API dependency
  on Gemini.
  - `services/ai_service.py` — deleted entirely (`generate_metadata()`, `regenerate_title()`)
  - `handlers/ai.py` — deleted entirely (`/ai` command, `cb_metadata_start`, `cb_ai_suggest`,
    `cb_ai_apply_yt`, `cb_regen_title`, AI FSM state management)
  - `handlers/__init__.py` — `ai` import and `ai.register(app)` removed
  - `handlers/fsm_router.py` — `STATE_WAIT_HINT` AI FSM branch removed
  - `handlers/start.py` — `cb_ai_menu` callback handler removed
  - `utils/keyboards.py` — `🤖 AI Tools` button removed from start menu;
    `upload_confirm()` simplified — `ai_applied` param, `✨ AI Suggest`, and `🔄 Regen Title`
    buttons removed
  - `config.py` — `GEMINI_API_KEY` env var removed
  - `requirements.txt` — `google-generativeai` removed

---

## [v2.3.0] — 2026-03-14

### Removed

- **Whisper AI captions removed** — `openai-whisper` depended on PyTorch (~2.5 GB install),
  making Render builds fail (2 GB disk limit exceeded) and causing OOM crashes on any instance
  with less than 512 MB free RAM. The feature has been removed entirely until a lighter
  alternative (e.g. `faster-whisper`) is integrated.
  - `services/ai_service.py` — `generate_captions()`, `_format_srt_time()`, `_segments_to_srt()` removed
  - `handlers/ai.py` — `STATE_WAIT_VIDEO`, `cb_caption_start` handler removed
  - `handlers/fsm_router.py` — Whisper document FSM branch removed
  - `config.py` — `WHISPER_MODEL` env var removed
  - `render.yaml` — `WHISPER_MODEL` env var removed; `apt-get install ffmpeg` removed from buildCommand
  - `requirements.txt` — `openai-whisper`, `ffmpeg-python` removed
  - `requirements-whisper.txt` — deleted
  - `handlers/start.py` — "🎙 AI Captions (Whisper)" button removed from `/ai` menu

- Manual `.srt` caption upload via `/manage → 📝 Captions` is **not affected** — that feature
  uploads user-provided subtitle files directly to YouTube and has no dependency on Whisper.

---

## [v2.2.0] — 2026-03-14

### Critical Bug Fixes

- **FSM handler conflict** — `manage.py`, `ai.py`, and `video.py` were each registering their own
  `filters.text & filters.private` and `filters.document & filters.private` handlers. Pyrogram fires
  the first matching handler and ignores the rest, so AI FSM (`STATE_WAIT_HINT`) and Whisper caption
  input (`STATE_WAIT_VIDEO`) were silently unreachable. Fixed by extracting all FSM text/photo/document
  routing into a new `handlers/fsm_router.py` that is registered last, after all command and callback
  handlers. Priority order: upload title edit → AI FSM → manage FSM → video upload fallback.

- **Broadcast sent hardcoded string** — `/broadcast` replied to admin's message correctly but the
  callback always sent `"📢 Announcement from bot admin."` instead of forwarding the actual replied
  message. Fixed: `_broadcast_msg` dict stores the replied `Message` object per admin; the confirm
  callback calls `source_msg.forward(uid)` for each user.

- **Blocking `flow.fetch_token()` in async OAuth route** — `fetch_token()` is a synchronous network
  call (200–2000ms) that was awaited directly inside a FastAPI async route, blocking the entire uvicorn
  event loop for the duration of the Google token exchange. Fixed with
  `await asyncio.to_thread(flow.fetch_token, code=code)`.

- **Document handler race between manage FSM and video upload** — `manage.py` registered a
  `filters.document` handler for `.srt` caption uploads; `video.py` registered another for video
  uploads. A document sent while in `STATE_CAPTION_FILE` could be routed to the wrong handler.
  Resolved by the central `fsm_router.py` which checks FSM state before deciding whether to treat
  a document as a caption file or a regular video upload.

### Bug Fixes

- **`upload_edit_title` button had no handler** — the keyboard button with
  `callback_data="upload_edit_title:<key>"` existed but no `on_callback_query` handler matched it;
  clicking silently did nothing. Handler added in `video.py`; title edit state tracked via
  `_pending_edit` dict and resolved in `fsm_router.py`.

- **`admin_keys` and `admin_broadcast` buttons had no handlers** — both buttons in the admin panel
  keyboard had `callback_data` values with no matching handlers. Added `cb_admin_keys` (lists all
  API keys with usage) and `cb_admin_broadcast` (usage instructions) in `admin.py`.

- **`set_status()` mutable default argument** — `async def set_status(..., extra: dict = {})` used a
  mutable default argument, a classic Python bug where a mutated dict persists across calls.
  Fixed: `extra: dict = None`, then `extra = extra or {}` inside the function.

- **`increment_usage()` KeyError on missing `_id`** — `apikey_repo.get_active()` returns a raw MongoDB
  dict; if `_id` was somehow absent, `api_key_doc["_id"]` raised `KeyError`. Added
  `if key_id is None: return` guard in `increment_usage()`.

- **Schedule FSM gave no format feedback** — invalid datetime input raised `ValueError` caught by the
  outer `except Exception`, giving users a cryptic `❌ Error: ...` message. Now catches `ValueError`
  specifically and replies with the correct format and an example.

### Improvements

- **`_pending` TTL** — upload confirmation entries in the in-memory `_pending` dict never expired,
  causing a slow memory leak under heavy use. Each entry now stores a `_ts` timestamp; a
  `_cleanup_pending()` call on every new upload removes entries older than 10 minutes.

- **Startup stuck-job recovery** — on restart, uploads with status `PENDING` or `DOWNLOADING` (left
  over from a crash) are now automatically marked `FAILED` with a clear message
  `"Bot restarted during upload. Please resend the video."` so users are not left waiting indefinitely.

- **Startup config validation** — `main.py` now logs a warning if `ADMIN_IDS` is empty (no admin
  access possible), `BOT_TOKEN` is missing (exits early), or Google OAuth credentials are unset.

### Structure

- `handlers/fsm_router.py` — new file; sole handler for `filters.text`, `filters.photo`,
  and `filters.document` in private chats
- `handlers/manage.py` — FSM text/photo/document handlers removed; only command + callback handlers remain
- `handlers/ai.py` — FSM text/video handlers removed; only command + callback handlers remain
- `handlers/video.py` — `handle_video_upload()` extracted as a standalone async function callable
  from `fsm_router`; `_pending_edit` dict added for upload title edit FSM
- `handlers/__init__.py` — `fsm_router.register(app)` added as the last registration step
- `database/repositories/upload_repo.py` — `get_stuck_jobs()` method added for startup recovery
- `database/repositories/apikey_repo.py` — `None` guard in `increment_usage()`

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
- All imports updated to reflect new paths

### Render Deploy Support

- `render.yaml` added — auto-detected by Render on connect
- `Procfile` fixed — was `cmd1 & cmd2` (broken); now `web: python main.py`
- `config.py` — `OAUTH_SERVER_PORT` now reads `$PORT` env var first (required by Render)
- `Dockerfile` — added `ffmpeg`, `g++`, `python3-dev`; created `/app/logs` dir
- `requirements.txt` — added `psutil` for RAM check

### Local Deploy Support

- `setup_local.sh` added — installs `ffmpeg`, creates `venv`, validates `.env`, creates `downloads/` and `logs/` dirs
- `run.sh` added — activates `venv` and starts bot
- `utils/logger.py` — log file path changed from relative `bot.log` to absolute `logs/bot.log` inside project root

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

- New `/ai` command with Gemini 1.5 Flash (free tier)
- AI metadata generation: title (≤70 chars), description (150–300 chars), tags (up to 8)
- `✨ AI Suggest` button on upload confirmation screen — auto-fills title/desc/tags
- `🔄 Regen Title` button — regenerate title only
- Language-aware generation (English / Malayalam)

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
