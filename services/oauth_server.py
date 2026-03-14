import asyncio
import urllib.parse
import requests as _requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from database.models import YouTubeToken
from config import Config
from utils.logger import log
import uvicorn

app = FastAPI()

# Main event loop reference — set from main.py after bot starts
_main_loop: asyncio.AbstractEventLoop = None

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def set_main_loop(loop: asyncio.AbstractEventLoop):
    global _main_loop
    _main_loop = loop


@app.get("/auth/{telegram_id}")
async def auth(telegram_id: int):
    params = {
        "client_id": Config.GOOGLE_CLIENT_ID,
        "redirect_uri": Config.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": str(telegram_id),
        "include_granted_scopes": "true",
    }
    auth_url = "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params)
    return RedirectResponse(auth_url)


@app.get("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code or not state:
        return HTMLResponse("<h2>❌ Authorization failed. Missing code or state.</h2>")

    try:
        telegram_id = int(state)
    except ValueError:
        return HTMLResponse("<h2>❌ Invalid state parameter.</h2>")

    try:
        # Token exchange — blocking, safe in thread
        def _exchange():
            resp = _requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": Config.GOOGLE_CLIENT_ID,
                    "client_secret": Config.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": Config.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            return resp.json()

        token_data = await asyncio.to_thread(_exchange)

        token = YouTubeToken(
            access_token=token_data.get("access_token", ""),
            refresh_token=token_data.get("refresh_token", ""),
            client_id=Config.GOOGLE_CLIENT_ID,
            client_secret=Config.GOOGLE_CLIENT_SECRET,
        )

        # Run DB calls on the main event loop (Motor requires its own loop)
        async def _save():
            from database.db import user_repo
            await user_repo.set_youtube_token(telegram_id, token)
            await user_repo.upsert(telegram_id, {"youtube_connected": True})

        if _main_loop and _main_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(_save(), _main_loop)
            future.result(timeout=10)
        else:
            await _save()

        log.info(f"YouTube connected for user {telegram_id}")

        return HTMLResponse("""
            <html>
            <head><meta charset="utf-8"></head>
            <body style="font-family:sans-serif;text-align:center;padding:60px;background:#0f0f0f;color:#fff">
                <h2>✅ YouTube Connected!</h2>
                <p style="color:#aaa">Go back to Telegram and send a video to upload.</p>
                <p style="margin-top:30px;font-size:13px;color:#555">You can close this window.</p>
            </body>
            </html>
        """)

    except Exception as e:
        log.error(f"OAuth callback error for user {state}: {e}")
        return HTMLResponse(f"<h2>❌ Error: {e}</h2>")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "GramUploader OAuth"}


def run_oauth_server():
    uvicorn.run(
        app,
        host=Config.OAUTH_SERVER_HOST,
        port=Config.OAUTH_SERVER_PORT,
        log_level="warning"
    )