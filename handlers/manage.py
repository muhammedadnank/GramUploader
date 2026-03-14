"""
/manage handler — YouTube Studio-like panel
Full video management: edit, delete, thumbnail, captions, playlists, stats

FSM text/photo/document handling has been moved to handlers/fsm_router.py
to avoid Pyrogram handler conflicts.
"""

from pyrogram import Client, filters
from pyrogram.errors import MessageNotModified
from pyrogram import enums


async def _safe_edit(message, text=None, reply_markup=None, parse_mode=None):
    """Edit message ignoring MessageNotModified."""
    try:
        kwargs = {}
        if reply_markup is not None:
            kwargs["reply_markup"] = reply_markup
        if parse_mode is not None:
            kwargs["parse_mode"] = parse_mode
        if text is not None:
            await message.edit_text(text, **kwargs)
        else:
            await message.edit_reply_markup(reply_markup=reply_markup)
    except MessageNotModified:
        pass
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from core.middlewares import apply_middlewares
from services.youtube_manager import (
    get_my_videos, get_video_details, update_video,
    delete_video, set_thumbnail, get_my_playlists,
    add_to_playlist, create_playlist, upload_caption,
    get_captions, delete_caption, get_channel_stats,
    format_count
)
from utils.manage.keyboards import ManagerKeyboards
from utils.manage.messages import ManagerMessages
from utils.keyboards import Keyboards
from utils.logger import log

# FSM state store: {user_id: {state, video_id, ...}}
_states: dict = {}

STATE_EDIT_TITLE   = "edit_title"
STATE_EDIT_DESC    = "edit_desc"
STATE_EDIT_TAGS    = "edit_tags"
STATE_THUMBNAIL    = "thumbnail"
STATE_CAPTION_FILE = "caption_file"
STATE_CAPTION_LANG = "caption_lang"
STATE_SCHEDULE     = "schedule"
STATE_NEW_PLAYLIST = "new_playlist"


def set_state(user_id: int, state: str, **kwargs):
    _states[user_id] = {"state": state, **kwargs}


def get_state(user_id: int) -> dict:
    return _states.get(user_id, {})


def clear_state(user_id: int):
    _states.pop(user_id, None)


def register(app: Client):

    # ─── /manage ────────────────────────────────────────────────

    @app.on_message(filters.command("manage") & filters.private)
    async def manage(client: Client, message: Message):
        if not await apply_middlewares(client, message):
            return
        msg = await message.reply("⏳ Fetching your videos...")
        try:
            data = await get_my_videos(message.from_user.id)
            videos = data["items"]
            if not videos:
                await msg.edit_text(
                    "📭 <b>No videos found.</b>\n\nUpload a video first!",
                    parse_mode=enums.ParseMode.HTML
                )
                return
            await msg.edit_text(
                ManagerMessages.video_list_header(len(videos)),
                reply_markup=ManagerKeyboards.video_list(
                    videos,
                    next_token=data.get("nextPageToken"),
                    prev_token=data.get("prevPageToken")
                ),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            await msg.edit_text(f"❌ {e}")

    # ─── VIDEO LIST (paginated) ──────────────────────────────────

    @app.on_callback_query(filters.regex(r"^mgr_list:(.*)$"))
    async def cb_list(client: Client, cq: CallbackQuery):
        token = cq.matches[0].group(1) or None
        await cq.message.edit_text("⏳ Loading...")
        try:
            data = await get_my_videos(cq.from_user.id, page_token=token)
            videos = data["items"]
            if not videos:
                await cq.message.edit_text("📭 No videos found.")
                return
            await cq.message.edit_text(
                ManagerMessages.video_list_header(len(videos)),
                reply_markup=ManagerKeyboards.video_list(
                    videos,
                    next_token=data.get("nextPageToken"),
                    prev_token=data.get("prevPageToken")
                ),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            await cq.message.edit_text(f"❌ {e}")

    # ─── VIDEO PANEL ────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^mgr_video:(.+)$"))
    async def cb_video_panel(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        # Clear any active FSM state when returning to video panel
        clear_state(cq.from_user.id)
        await cq.message.edit_text("⏳ Loading video details...")
        try:
            video = await get_video_details(cq.from_user.id, video_id)
            await cq.message.edit_text(
                ManagerMessages.video_panel(video),
                reply_markup=ManagerKeyboards.video_panel(video_id),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            await cq.message.edit_text(f"❌ {e}")

    # ─── CHANNEL STATS ──────────────────────────────────────────

    @app.on_callback_query(filters.regex("^mgr_channel_stats$"))
    async def cb_channel_stats(client: Client, cq: CallbackQuery):
        await cq.message.edit_text("⏳ Fetching channel stats...")
        try:
            channel = await get_channel_stats(cq.from_user.id)
            await cq.message.edit_text(
                ManagerMessages.channel_stats(channel),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back to Videos", callback_data="mgr_list:"),
                    InlineKeyboardButton("🏠 Menu", callback_data="back_start"),
                ]]),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            await cq.message.edit_text(f"❌ {e}")

    # ─── EDIT TITLE ─────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^mgr_edit_title:(.+)$"))
    async def cb_edit_title(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        video = await get_video_details(cq.from_user.id, video_id)
        current = video["snippet"]["title"]
        set_state(cq.from_user.id, STATE_EDIT_TITLE, video_id=video_id)
        await cq.message.edit_text(ManagerMessages.edit_prompt("Title", current), parse_mode=enums.ParseMode.HTML)

    # ─── EDIT DESCRIPTION ───────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^mgr_edit_desc:(.+)$"))
    async def cb_edit_desc(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        video = await get_video_details(cq.from_user.id, video_id)
        current = video["snippet"].get("description", "")
        set_state(cq.from_user.id, STATE_EDIT_DESC, video_id=video_id)
        await cq.message.edit_text(ManagerMessages.edit_prompt("Description", current), parse_mode=enums.ParseMode.HTML)

    # ─── EDIT TAGS ──────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^mgr_edit_tags:(.+)$"))
    async def cb_edit_tags(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        video = await get_video_details(cq.from_user.id, video_id)
        current_tags = ", ".join(video["snippet"].get("tags", []))
        set_state(cq.from_user.id, STATE_EDIT_TAGS, video_id=video_id)
        await cq.message.edit_text(ManagerMessages.edit_prompt("Tags", current_tags or "No tags"), parse_mode=enums.ParseMode.HTML)

    # ─── PRIVACY ────────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^mgr_privacy:(.+)$"))
    async def cb_privacy(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        video = await get_video_details(cq.from_user.id, video_id)
        current = video["status"]["privacyStatus"]
        await cq.message.edit_text(
            f"🔒 <b>Change Privacy</b>\n\nCurrent: <b>{current.capitalize()}</b>",
            reply_markup=ManagerKeyboards.privacy(video_id, current),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex(r"^mgr_set_privacy:(\w+):(.+)$"))
    async def cb_set_privacy(client: Client, cq: CallbackQuery):
        privacy = cq.matches[0].group(1)
        video_id = cq.matches[0].group(2)
        try:
            await update_video(cq.from_user.id, video_id, {"privacyStatus": privacy})
            await cq.answer(f"✅ Privacy set to {privacy}")
            video = await get_video_details(cq.from_user.id, video_id)
            await cq.message.edit_text(
                ManagerMessages.video_panel(video),
                reply_markup=ManagerKeyboards.video_panel(video_id),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            await cq.answer(f"❌ {e}", show_alert=True)

    # ─── CATEGORY ───────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^mgr_category:(.+)$"))
    async def cb_category(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        video = await get_video_details(cq.from_user.id, video_id)
        current = video["snippet"].get("categoryId", "22")
        await cq.message.edit_text(
            "🗂 <b>Select Category</b>",
            reply_markup=ManagerKeyboards.category(video_id, current),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex(r"^mgr_set_category:(\w+):(.+)$"))
    async def cb_set_category(client: Client, cq: CallbackQuery):
        cat_id = cq.matches[0].group(1)
        video_id = cq.matches[0].group(2)
        try:
            await update_video(cq.from_user.id, video_id, {"categoryId": cat_id})
            await cq.answer("✅ Category updated!")
            video = await get_video_details(cq.from_user.id, video_id)
            await cq.message.edit_text(
                ManagerMessages.video_panel(video),
                reply_markup=ManagerKeyboards.video_panel(video_id),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            await cq.answer(f"❌ {e}", show_alert=True)

    # ─── THUMBNAIL ──────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^mgr_thumbnail:(.+)$"))
    async def cb_thumbnail(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        set_state(cq.from_user.id, STATE_THUMBNAIL, video_id=video_id)
        await cq.message.edit_text(
            ManagerMessages.thumbnail_prompt(video_id),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data=f"mgr_video:{video_id}")
            ]]),
            parse_mode=enums.ParseMode.HTML
        )

    # ─── PLAYLISTS ──────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^mgr_playlist:(.+)$"))
    async def cb_playlist(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        await cq.message.edit_text("⏳ Fetching playlists...")
        try:
            playlists = await get_my_playlists(cq.from_user.id)
            if not playlists:
                await cq.message.edit_text(
                    "📭 No playlists found.\nTap to create one.",
                    reply_markup=ManagerKeyboards.playlist_select(video_id, []),
                    parse_mode=enums.ParseMode.HTML
                )
                return
            await cq.message.edit_text(
                f"📋 <b>Add to Playlist</b>\n\nSelect a playlist:",
                reply_markup=ManagerKeyboards.playlist_select(video_id, playlists),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            await cq.message.edit_text(f"❌ {e}")

    @app.on_callback_query(filters.regex(r"^mgr_add_playlist:([^:]+):(.+)$"))
    async def cb_add_playlist(client: Client, cq: CallbackQuery):
        playlist_id = cq.matches[0].group(1)
        video_id = cq.matches[0].group(2)
        try:
            await add_to_playlist(cq.from_user.id, video_id, playlist_id)
            await cq.answer("✅ Added to playlist!")
            video = await get_video_details(cq.from_user.id, video_id)
            await cq.message.edit_text(
                ManagerMessages.video_panel(video),
                reply_markup=ManagerKeyboards.video_panel(video_id),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            await cq.answer(f"❌ {e}", show_alert=True)

    @app.on_callback_query(filters.regex(r"^mgr_new_playlist:(.+)$"))
    async def cb_new_playlist(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        set_state(cq.from_user.id, STATE_NEW_PLAYLIST, video_id=video_id)
        await cq.message.edit_text(
            "➕ <b>Create Playlist</b>\n\nSend the playlist name.\nSend /cancel to abort.",
            parse_mode=enums.ParseMode.HTML
        )

    # ─── CAPTIONS ───────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^mgr_captions:(.+)$"))
    async def cb_captions(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        await cq.message.edit_text("⏳ Fetching captions...")
        try:
            captions = await get_captions(cq.from_user.id, video_id)
            count = len(captions)
            await cq.message.edit_text(
                f"📝 <b>Captions</b>\n\n{count} caption track{'s' if count != 1 else ''} found.",
                reply_markup=ManagerKeyboards.captions(video_id, captions),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            await cq.message.edit_text(f"❌ {e}")

    @app.on_callback_query(filters.regex(r"^mgr_upload_caption:(.+)$"))
    async def cb_upload_caption(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        set_state(cq.from_user.id, STATE_CAPTION_FILE, video_id=video_id)
        await cq.message.edit_text(ManagerMessages.caption_prompt(), parse_mode=enums.ParseMode.HTML)

    @app.on_callback_query(filters.regex(r"^mgr_del_caption:([^:]+):(.+)$"))
    async def cb_del_caption(client: Client, cq: CallbackQuery):
        caption_id = cq.matches[0].group(1)
        video_id = cq.matches[0].group(2)
        try:
            await delete_caption(cq.from_user.id, caption_id)
            await cq.answer("✅ Caption deleted!")
            captions = await get_captions(cq.from_user.id, video_id)
            await cq.message.edit_text(
                f"📝 <b>Captions</b>\n\n{len(captions)} track(s) remaining.",
                reply_markup=ManagerKeyboards.captions(video_id, captions),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            await cq.answer(f"❌ {e}", show_alert=True)

    # ─── ADVANCED ───────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^mgr_advanced:(.+)$"))
    async def cb_advanced(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        video = await get_video_details(cq.from_user.id, video_id)
        status = video["status"]
        await cq.message.edit_text(
            "⚙️ <b>Advanced Settings</b>",
            reply_markup=ManagerKeyboards.advanced(video_id, status),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex(r"^mgr_toggle_kids:(.+)$"))
    async def cb_toggle_kids(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        video = await get_video_details(cq.from_user.id, video_id)
        current = video["status"].get("selfDeclaredMadeForKids", False)
        await update_video(cq.from_user.id, video_id, {"madeForKids": not current})
        await cq.answer(f"Made for Kids: {'ON' if not current else 'OFF'}")
        video = await get_video_details(cq.from_user.id, video_id)
        await _safe_edit(cq.message, reply_markup=ManagerKeyboards.advanced(video_id, video["status"]))

    @app.on_callback_query(filters.regex(r"^mgr_toggle_embed:(.+)$"))
    async def cb_toggle_embed(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        video = await get_video_details(cq.from_user.id, video_id)
        current = video["status"].get("embeddable", True)
        await update_video(cq.from_user.id, video_id, {"embeddable": not current})
        await cq.answer(f"Embeddable: {'ON' if not current else 'OFF'}")
        video = await get_video_details(cq.from_user.id, video_id)
        await _safe_edit(cq.message, reply_markup=ManagerKeyboards.advanced(video_id, video["status"]))

    @app.on_callback_query(filters.regex(r"^mgr_toggle_license:(.+)$"))
    async def cb_toggle_license(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        video = await get_video_details(cq.from_user.id, video_id)
        current = video["status"].get("license", "youtube")
        new_lic = "creativeCommon" if current == "youtube" else "youtube"
        await update_video(cq.from_user.id, video_id, {"license": new_lic})
        await cq.answer(f"License: {'CC' if new_lic == 'creativeCommon' else 'Standard'}")
        video = await get_video_details(cq.from_user.id, video_id)
        await _safe_edit(cq.message, reply_markup=ManagerKeyboards.advanced(video_id, video["status"]))

    @app.on_callback_query(filters.regex(r"^mgr_schedule:(.+)$"))
    async def cb_schedule(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        set_state(cq.from_user.id, STATE_SCHEDULE, video_id=video_id)
        await cq.message.edit_text(ManagerMessages.schedule_prompt(), parse_mode=enums.ParseMode.HTML)

    # ─── STATS ──────────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^mgr_stats:(.+)$"))
    async def cb_stats(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        video = await get_video_details(cq.from_user.id, video_id)
        stats = video.get("statistics", {})
        await cq.message.edit_text(
            f"📊 <b>Video Statistics</b>\n\n"
            f"👁 Views: <b>{format_count(stats.get('viewCount', 0))}</b>\n"
            f"👍 Likes: <b>{format_count(stats.get('likeCount', 0))}</b>\n"
            f"💬 Comments: <b>{format_count(stats.get('commentCount', 0))}</b>\n"
            f"⭐ Favorites: <b>{format_count(stats.get('favoriteCount', 0))}</b>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data=f"mgr_video:{video_id}")
            ]]),
            parse_mode=enums.ParseMode.HTML
        )

    # ─── DELETE ─────────────────────────────────────────────────

    @app.on_callback_query(filters.regex(r"^mgr_delete_confirm:(.+)$"))
    async def cb_delete_confirm(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        video = await get_video_details(cq.from_user.id, video_id)
        title = video["snippet"]["title"]
        await cq.message.edit_text(
            ManagerMessages.delete_confirm(title),
            reply_markup=ManagerKeyboards.delete_confirm(video_id),
            parse_mode=enums.ParseMode.HTML
        )

    @app.on_callback_query(filters.regex(r"^mgr_delete_do:(.+)$"))
    async def cb_delete_do(client: Client, cq: CallbackQuery):
        video_id = cq.matches[0].group(1)
        try:
            video = await get_video_details(cq.from_user.id, video_id)
            title = video["snippet"]["title"]
            await delete_video(cq.from_user.id, video_id)
            await cq.message.edit_text(
                ManagerMessages.delete_done(title),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back to Videos", callback_data="mgr_list:")
                ]]),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            await cq.answer(f"❌ {e}", show_alert=True)