from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow
from database.db import user_repo
from database.models import YouTubeToken
from config import Config
from utils.logger import log
import uvicorn

app = FastAPI()

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def create_flow() -> Flow:
    return Flow.from_client_config(
        {
            "web": {
                "client_id": Config.GOOGLE_CLIENT_ID,
                "client_secret": Config.GOOGLE_CLIENT_SECRET,
                "redirect_uris": [Config.GOOGLE_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=Config.GOOGLE_REDIRECT_URI
    )


@app.get("/auth/{telegram_id}")
async def auth(telegram_id: int):
    """Redirect user to Google OAuth consent screen."""
    flow = create_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=str(telegram_id),
        prompt="consent"
    )
    return RedirectResponse(auth_url)


@app.get("/callback")
async def callback(request: Request):
    """Handle Google OAuth2 callback, save token to DB."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")  # telegram_id

    if not code or not state:
        return HTMLResponse("<h2>❌ Authorization failed. Missing code or state.</h2>")

    try:
        telegram_id = int(state)
    except ValueError:
        return HTMLResponse("<h2>❌ Invalid state parameter.</h2>")

    try:
        flow = create_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials

        token = YouTubeToken(
            access_token=creds.token,
            refresh_token=creds.refresh_token or "",
            client_id=Config.GOOGLE_CLIENT_ID,
            client_secret=Config.GOOGLE_CLIENT_SECRET,
        )

        # Save token + mark connected
        await user_repo.set_youtube_token(telegram_id, token)
        await user_repo.upsert(telegram_id, {"youtube_connected": True})

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
