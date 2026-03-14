from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from google_auth_oauthlib.flow import Flow
from database.db import save_youtube_token, upsert_user
from config import Config
import uvicorn

app = FastAPI()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def create_flow():
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
    """Generate Google OAuth URL for user"""
    flow = create_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=str(telegram_id),
        prompt="consent"
    )
    from fastapi.responses import RedirectResponse
    return RedirectResponse(auth_url)


@app.get("/callback")
async def callback(request: Request):
    """Handle Google OAuth callback"""
    code = request.query_params.get("code")
    state = request.query_params.get("state")  # telegram_id

    if not code or not state:
        return HTMLResponse("<h2>❌ Authorization failed.</h2>")

    telegram_id = int(state)

    flow = create_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Save token to MongoDB
    await save_youtube_token(telegram_id, {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": Config.GOOGLE_CLIENT_ID,
        "client_secret": Config.GOOGLE_CLIENT_SECRET,
    })

    await upsert_user(telegram_id, {"youtube_connected": True})

    return HTMLResponse("""
        <html>
        <body style="font-family:sans-serif;text-align:center;padding:50px">
            <h2>✅ YouTube Connected!</h2>
            <p>Go back to Telegram and send a video to upload.</p>
        </body>
        </html>
    """)


@app.get("/health")
async def health():
    return {"status": "ok"}


def run_oauth_server():
    uvicorn.run(app, host=Config.OAUTH_SERVER_HOST, port=Config.OAUTH_SERVER_PORT)
