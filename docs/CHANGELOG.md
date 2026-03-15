# Changelog

All notable changes to GramUploader are documented here.
Format: `[vX.Y.Z] — YYYY-MM-DD`

---

## [v2.7.0] — 2026-03-15

### Added

- **Dual-stage progress bars** (`utils/messages.py` — `_dual_progress()`) — download and
  upload progress are now shown side-by-side in the same message throughout the upload flow:
  `📥 Download: [██████░░░░] 60%` / `📤 Upload: [░░░░░░░░░░] 0%`. Both bars update live.
  `Messages.progress_downloading()` and `Messages.progress_uploading()` updated accordingly.

- **Upload done — YouTube thumbnail card** (`services/queue_worker.py`) — on successful
  upload, the progress message is deleted and the video's YouTube thumbnail is sent as a
  photo with the done caption and action buttons (`Watch`, `Manage Video`, `History`).
  URL: `https://img.youtube.com/vi/{video_id}/hqdefault.jpg`. Falls back to plain text if
  the thumbnail fetch fails.

- **Video duration on confirmation screen** (`handlers/video.py`, `utils/messages.py`) —
  `message.video.duration` is captured and shown as `⏱ Duration: 2:34`. Stored in
  `_pending` and carried through privacy-change and back-navigation re-renders.
  Not available for documents (Telegram doesn't expose duration for those).

- **Shorts eligibility hint** — if `duration ≤ 60s`, the duration line appends
  `📱 Shorts eligible`. Informational only — no automatic `#Shorts` tag added.

- **YouTube Shorts toggle on confirmation screen** (`handlers/video.py`,
  `utils/keyboards.py`, `utils/messages.py`) — a `📱 Short: ON/OFF` toggle button
  is shown on every upload confirmation screen. For videos ≤ 60s the toggle defaults
  to **ON**; for longer videos it defaults to **OFF**. User can flip it at any time
  before confirming. When ON:
  - `#Shorts` is appended to the title (trimmed to 100 chars).
  - Privacy is forced to `public` (YouTube Shorts do not work as private/unlisted).
  - The confirmation screen shows a note: *"will upload as Short (#Shorts added,
    privacy forced Public)"*.
  When the toggle is flipped ON → OFF, the `#Shorts` append and privacy override
  are simply not applied — no further state change. The toggle state is stored in
  `_pending[key]["is_short"]` and carried through all confirm screen re-renders
  (title edit, privacy change, back navigation). New callback: `upload_toggle_shorts:<key>`.

- **File type emoji on confirmation screen** (`_FILE_TYPE_EMOJI` dict in `messages.py`) —
  `🎬` mp4/mov · `📦` mkv · `🌐` webm · `📼` avi/wmv/flv/mpeg · `📱` 3gp · `🎞` unknown.

- **Upload history dates** (`Messages.history_page()`) — each entry now shows the upload
  date as `· 14 Mar` in italic, pulled from `Upload.created_at`.

- **Quota reset countdown** (`Messages.quota_text()`) — shows `🕐 Resets in 3h 42m`
  computed live from `datetime.now(timezone.utc)` to midnight UTC, replacing the static hint.

- **Connected YouTube channel name in Settings** (`_send_settings()` in `start.py`,
  `Messages.settings_text()`) — shows `📺 Channel: <name>` when connected, fetched via
  `get_channel_stats()`. Silently omitted if the call fails.

- **Live queue depth in Admin Stats** (`_fetch_stats()` in `admin.py`,
  `Messages.admin_stats()`) — shows `⏳ Queue: N pending` when the queue is non-empty.
  Hidden when queue is 0 to keep the panel clean.

- **Help text updated** — `/disconnect` and `/queue` added to the command list in
  `Messages.help_text()`.

### Fixed

- **`admin_user_info()` `AttributeError` on `user.plan`** — after `use_enum_values: True`
  was added in v2.6.0, `user.plan` is a plain string. Calling `.value` on it crashed.
  Fixed with `user.plan if isinstance(user.plan, str) else user.plan.value`.

- **Start screen identical for connected/disconnected users** — connected users saw the same
  "Tap Connect below" text as new users. Screen now branches: connected → "Just send me a
  video!"; disconnected → connect call-to-action.

- **`ValueError: Unknown format code 'd' for object of type 'float'`** —
  `message.video.duration` from Telegram is a `float` (e.g. `102.5`). Passing it
  directly to `divmod()` produced float quotients; `f"{m:02d}"` then crashed because
  `:d` format only accepts integers. Fixed by casting to `int` before `divmod`:
  `divmod(int(duration), 60)`.

### Changed

- **`Messages.upload_confirm()`** — optional `duration: int = None` and
  `is_short: bool = False` params added.
- **`Keyboards.upload_confirm()`** — optional `is_short: bool = False` param added;
  renders the Shorts toggle button with current state.
- **`Messages.settings_text()`** — optional `channel_name: str = None` param added.
- **`Messages.admin_stats()`** — optional `queue_size: int = 0` param added.
- **`Messages.upload_done()`** — optional `privacy: str = "public"` param added.
- **Version** bumped to `2.7.0` in `config.py`.

---

## [v2.6.0] — 2026-03-14

### Added

- **`/disconnect`** — users can unlink their YouTube account. Wipes `youtube_token` and
  sets `youtube_connected: false` via new `user_repo.clear_youtube_token()`.

- **`user_repo.iter_all_ids()`** — memory-safe async generator for broadcast; streams one
  ID at a time instead of loading all users into RAM.

- **`database/db.py` — `ensure_indexes()`** — creates MongoDB indexes on startup
  (idempotent). Indexes: `uploads.telegram_id`, `uploads.status`, `uploads.created_at`,
  compound `(telegram_id, created_at)`, `users.youtube_connected`, `users.is_banned`.

- **Post-OAuth Telegram notification** — bot sends `✅ YouTube Connected!` after OAuth,
  so users don't have to guess whether the flow succeeded.

### Fixed

- **`UploadStatus` enum stored as object not string** — all status writes in
  `queue_worker.py` and `main.py` now use `.value`.

- **`model_config = {"use_enum_values": True}`** added to `User` and `Upload` models —
  ensures enums serialize as strings in `model_dump()`.

- **Downloaded, thumbnail, and SRT temp files never deleted** — `finally` blocks added
  in `process_job`, `fsm_photo_router`, and `fsm_text_router` respectively.

- **`cq.answer()` missing from all 40+ callback handlers** — Telegram showed a loading
  spinner indefinitely. Added as the first line in every `@on_callback_query`.

- **`cb_back_start` swallowed unrelated exceptions** — replaced catch-all `Exception`
  with explicit `message.photo` check + `MessageNotModified` catch.

- **`/cancel` left title-edit FSM state on session expiry** — `_pending_edit.pop()`
  now always runs before checking if `pending_key` is still alive.

- **`quota_text()` `TypeError` for premium users** — `limit="∞"` caused int arithmetic
  to crash. Fixed with `isinstance(limit, int)` guard.

- **`sanitize_title()` stripped apostrophes** — `'` removed from forbidden chars;
  only `<`, `>`, and `"` are stripped now.

- **Broadcast OOM** — replaced `get_all_ids()` with `iter_all_ids()` async generator.

### Changed

- **`GEMINI_API_KEY`** removed from `config.py`, `render.yaml`, `core/env.example` —
  AI features were fully removed in v2.3.0–v2.4.0; dead config entries cleaned up.

- **Version** bumped to `2.6.0` in `config.py`.

---

## [v2.5.0] — 2026-03-14

### Added

- **`/user <id>`** — admin command: inspect user details + inline ban/unban/plan buttons.
- **`/deletekey <key>`** — deactivate an API key (repo method existed, command was missing).
- **`/setpremium <id>` / `/setfree <id>`** — change plan from command line.
- **Inline user management callbacks** — `admin_ban_user`, `admin_unban_user`,
  `admin_set_premium`, `admin_set_free`.
- **`Keyboards.admin_user()`** and **`Keyboards.admin_back()`** — new keyboard layouts.
- **`Messages.admin_user_info()`** — user detail message template.
- **`apikey_repo.find_by_key()`** and **`upload_repo.count_by_user()`** — new repo methods.

### Fixed

- **Broadcast flood** — added `asyncio.sleep(0.05)` + `FloodWait` retry.
- **`/ban` silent fail on new users** — `upsert=True` added to `ban()`.
- **`/addkey` duplicate keys** — duplicate check via `find_by_key()`.
- **Admin panel back buttons** — `admin_keys` / `admin_broadcast` now use `admin_back()`.
- **Maintenance toggle feedback** — stats panel refreshes after toggle.
- **Stats code duplication** — extracted into `_fetch_stats()` helper.
- **Admin panel missing back button** — `« Back` → `back_start` added.

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
