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

- **Shorts eligibility hint** — if `duration ≤ 180s`, the duration line appends
  `📱 Shorts eligible`.

- **YouTube Shorts toggle on confirmation screen** (`handlers/video.py`,
  `utils/keyboards.py`, `utils/messages.py`) — `📱 Short: ON/OFF` toggle button
  on every upload confirmation screen. When ON: `#Shorts` appended to title, privacy
  forced public. New callback: `upload_toggle_shorts:<key>`.

- **Shorts privacy enforcement** — `cb_set_privacy` now blocks non-public selections
  for Shorts and replies with an alert instead of silently overriding at confirm.

- **File type emoji on confirmation screen** — `🎬` mp4/mov · `📦` mkv · `🌐` webm ·
  `📼` avi/wmv/flv/mpeg · `📱` 3gp · `🎞` unknown.

- **Upload history dates** — each entry shows upload date as `· 14 Mar` in italic.

- **Quota reset countdown** — shows `🕐 Resets in 3h 42m` computed live from UTC midnight.

- **Connected YouTube channel name in Settings** — shows `📺 Channel: <n>` when connected.

- **Live queue depth in Admin Stats** — shows `⏳ Queue: N pending` when non-empty.

- **YouTube Shorts thumbnail prepend** (`services/video_processor.py`) — ffmpeg prepends
  a 2-second still of the user's thumbnail photo before the Short. Safe margin: skipped
  if `duration > 178s`. Falls back to original video on ffmpeg failure.

- **`apply_cb_middlewares()`** (`core/middlewares.py`) — lightweight ban + maintenance
  check for `CallbackQueryHandler`s. Previously all callbacks bypassed middleware entirely;
  now `cb_upload_confirm` and `cb_back_start` are protected.

- **`SECURITY.md`** — vulnerability reporting policy, scope, and contact.

- **`.github/dependabot.yml`** — daily dependency update checks for pip packages and
  GitHub Actions. `kurigram` minor/major updates ignored (manual upgrade required).

- **`.github/workflows/security-scan.yml`** — `pip-audit` + Safety dependency scan
  on push, PR, and daily schedule. Report saved as workflow artifact.

- **Token expiry tracking** — `YouTubeToken` model gains `token_expiry: Optional[datetime]`
  field. OAuth callback now saves expiry from `expires_in`. Uploader passes `expiry=` to
  `Credentials()` so `creds.expired` works correctly; also force-refreshes when
  `token_expiry is None` (existing users on first run after upgrade).

### Fixed

- **`user.plan.value` crash in `/user` command** (`handlers/admin.py`) — `User` model has
  `use_enum_values=True`, so `user.plan` is already a plain string. Calling `.value` on it
  raised `AttributeError`. Changed to `user.plan`.

- **OAuth token refresh never triggered** (`services/youtube_uploader.py`) — `Credentials`
  was built without an `expiry=` parameter, so `creds.expired` was always `False`. Tokens
  expired silently after ~1 hour causing 401 errors on all API calls.

- **Refresh token overwritten on re-connect** (`services/oauth_server.py`) — Google only
  returns `refresh_token` on first consent. Re-connecting without revoking first would
  overwrite the valid stored token with an empty string. Now preserves the existing token
  when the new response omits it.

- **`UPLOADING` jobs not recovered on restart** (`database/repositories/upload_repo.py`) —
  `get_stuck_jobs()` only recovered `PENDING` and `DOWNLOADING` statuses. Jobs that crashed
  mid-upload were stuck in `UPLOADING` forever. Added `UPLOADING` to the recovery filter.

- **`cb_stats` `MessageNotModified` crash** (`handlers/manage.py`) — the stats callback
  was the only one in manage.py not wrapped with `_safe_edit()`. Fixed.

- **All `"⏳ Loading..."` edit_text calls unguarded** (`handlers/manage.py`) — five callbacks
  (`cb_video_panel`, `cb_list`, `cb_channel_stats`, `cb_playlist`, `cb_captions`) used bare
  `edit_text()` for the loading state. Double-tap raised `MessageNotModified`. All wrapped
  in `try/except MessageNotModified`.

- **Double temp file deletion** (`services/youtube_uploader.py`) — the uploader's `finally`
  block deleted `file_path` independently; `queue_worker` also deleted it. Removed the
  duplicate `finally` from the uploader — cleanup is owned solely by `queue_worker`.

- **`clip_path` tempfile leak in video_processor** (`services/video_processor.py`) —
  `mkstemp` for the intermediate thumbnail clip was called before the `try` block. On
  early-return paths (ffprobe failure), the file was created but never cleaned up. Moved
  `mkstemp` inside the `try` block; `finally` now guards with `if clip_path`.

- **`out_path` orphaned on ffmpeg failure** (`services/video_processor.py`) — when the
  ffmpeg clip or concat step failed and returned early, the empty `out_path` tempfile was
  left on disk. Added cleanup before each early return.

- **`_rate_data` dict grows forever** (`core/middlewares.py`) — per-user timestamp lists
  were cleaned on each request but the key was never evicted. After cleanup, empty keys
  are now deleted.

- **Small caps Unicode removed from all messages** (`utils/messages.py`) — `sc()` and
  `fonts.py` were used for welcome and progress text. Removed in favour of plain text for
  consistent rendering across Telegram clients (Android, iOS, Desktop).

- **Circular import regression in keyboards + manage/messages** — a previous commit
  re-introduced `from handlers.video import _pending, _pending_edit, _pending_thumb` into
  `utils/keyboards.py` and `utils/manage/messages.py`. These are unused in both files
  and cause a circular import crash on startup. Removed again.

- **`sanitize_title()` didn't strip control characters** (`utils/validators.py`) —
  YouTube rejects titles containing `\n`, `\r`, `\t`, and other ASCII control chars
  (`\x00–\x1f`). Now stripped via `re.sub(r'[\x00-\x1f]', ' ', title)` before the
  existing forbidden-char removal.

- **`/diconnect` typo in help text** — corrected to `/disconnect`.

### Changed

- **Version** bumped to `2.7.0` in `config.py`.
- `utils/fonts.py` — `sc()` no longer imported or used; file is dead code (safe to delete).

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
  - `services/ai_service.py` — deleted entirely
  - `handlers/ai.py` — deleted entirely
  - `handlers/__init__.py` — `ai` import and `ai.register(app)` removed
  - `handlers/fsm_router.py` — `STATE_WAIT_HINT` AI FSM branch removed
  - `handlers/start.py` — `cb_ai_menu` callback handler removed
  - `utils/keyboards.py` — `🤖 AI Tools` button removed from start menu
  - `config.py` — `GEMINI_API_KEY` env var removed
  - `requirements.txt` — `google-generativeai` removed

---

## [v2.3.0] — 2026-03-14

### Removed

- **Whisper AI captions removed** — `openai-whisper` depended on PyTorch (~2.5 GB install),
  making Render builds fail (2 GB disk limit exceeded) and causing OOM crashes on any instance
  with less than 512 MB free RAM.
  - `services/ai_service.py` — `generate_captions()` and helpers removed
  - `handlers/ai.py` — `STATE_WAIT_VIDEO`, `cb_caption_start` handler removed
  - `handlers/fsm_router.py` — Whisper document FSM branch removed
  - `config.py` — `WHISPER_MODEL` env var removed
  - `requirements.txt` — `openai-whisper`, `ffmpeg-python` removed

- Manual `.srt` caption upload via `/manage → 📝 Captions` is **not affected**.

---

## [v2.2.0] — 2026-03-14

### Critical Bug Fixes

- **FSM handler conflict** — `manage.py`, `ai.py`, and `video.py` each registered their own
  `filters.text` and `filters.document` handlers. Fixed by extracting all FSM routing into
  `handlers/fsm_router.py` registered last.

- **Broadcast sent hardcoded string** — `/broadcast` always sent a fixed string instead of
  forwarding the replied message. Fixed: `_broadcast_msg` stores the replied `Message` object.

- **Blocking `flow.fetch_token()` in async OAuth route** — fixed with
  `await asyncio.to_thread(flow.fetch_token, code=code)`.

- **Document handler race between manage FSM and video upload** — resolved by central
  `fsm_router.py`.

### Bug Fixes

- `upload_edit_title` button had no handler — handler added in `video.py`.
- `admin_keys` and `admin_broadcast` buttons had no handlers — added in `admin.py`.
- `set_status()` mutable default argument — fixed `extra: dict = None`.
- `increment_usage()` KeyError on missing `_id` — `None` guard added.
- Schedule FSM gave no format feedback — specific `ValueError` catch with format hint.

### Improvements

- **`_pending` TTL** — entries expire after 10 minutes via `_cleanup_pending()`.
- **Startup stuck-job recovery** — `PENDING`/`DOWNLOADING` jobs marked `FAILED` on restart.
- **Startup config validation** — warnings for missing `ADMIN_IDS`, `BOT_TOKEN`, Google creds.

---

## [v2.1.0] — 2026-03-14

### Bug Fixes

- `handlers/start.py` — callbacks accidentally defined outside `register()` due to indentation error.
- `services/youtube_uploader.py` — removed calls to non-existent DB functions; token refresh not awaited.
- `services/oauth_server.py` — removed calls to non-existent functions; `refresh_token` None guard added.

### Structure

- `services/yt_manager.py` → renamed to `services/youtube_manager.py`
- `utils/manager_keyboards.py` → moved to `utils/manage/keyboards.py`
- `utils/manager_messages.py` → moved to `utils/manage/messages.py`

### Render Deploy Support

- `render.yaml`, `Procfile`, `Dockerfile` updates; `$PORT` env var support.

### Local Deploy Support

- `setup_local.sh`, `run.sh` added.

---

## [v2.0.0] — 2026-03-13

### YouTube Studio Panel (`/manage`)

- Edit title, description, tags, category, privacy, thumbnail, captions, playlists,
  advanced settings (kids/embed/license/schedule), stats, delete with confirmation.

### Other Changes

- Azure Container Instances deploy: `Dockerfile` + `deploy.sh`.
- `.gitignore`, `.dockerignore` added.

---

## [v1.0.0] — 2026-02-01

### Initial Release

- Telegram → YouTube video upload with live progress bars.
- Upload confirmation screen, in-memory queue worker, Google OAuth2, MongoDB Atlas.
- Repository pattern, Pydantic models, Free/Premium plan, API key rotation.
- Admin panel, history, quota, settings, rate limiter, maintenance mode, multi-language.
