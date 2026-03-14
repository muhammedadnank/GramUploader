"""
Manager panel keyboards — YouTube Studio-like UI
"""
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class ManagerKeyboards:

    # ─── VIDEO LIST ─────────────────────────────────────────────

    @staticmethod
    def video_list(videos: list, next_token: str = None, prev_token: str = None) -> InlineKeyboardMarkup:
        buttons = []
        for v in videos:
            vid_id = v["id"]
            title = v["snippet"]["title"][:32]
            privacy = v["status"]["privacyStatus"]
            emoji = {"public": "🌍", "private": "🔒", "unlisted": "🔗"}.get(privacy, "❓")
            buttons.append([InlineKeyboardButton(
                f"{emoji} {title}",
                callback_data=f"mgr_video:{vid_id}"
            )])

        nav = []
        if prev_token:
            nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"mgr_list:{prev_token}"))
        if next_token:
            nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"mgr_list:{next_token}"))
        if nav:
            buttons.append(nav)

        buttons.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="mgr_list:"),
            InlineKeyboardButton("📊 Channel Stats", callback_data="mgr_channel_stats"),
        ])
        buttons.append([InlineKeyboardButton("« Back to Menu", callback_data="back_start")])
        return InlineKeyboardMarkup(buttons)

    # ─── VIDEO PANEL ────────────────────────────────────────────

    @staticmethod
    def video_panel(video_id: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✏️ Edit Title", callback_data=f"mgr_edit_title:{video_id}"),
                InlineKeyboardButton("📝 Edit Desc", callback_data=f"mgr_edit_desc:{video_id}"),
            ],
            [
                InlineKeyboardButton("🏷 Edit Tags", callback_data=f"mgr_edit_tags:{video_id}"),
                InlineKeyboardButton("🗂 Category", callback_data=f"mgr_category:{video_id}"),
            ],
            [
                InlineKeyboardButton("🔒 Privacy", callback_data=f"mgr_privacy:{video_id}"),
                InlineKeyboardButton("🖼 Thumbnail", callback_data=f"mgr_thumbnail:{video_id}"),
            ],
            [
                InlineKeyboardButton("📋 Playlist", callback_data=f"mgr_playlist:{video_id}"),
                InlineKeyboardButton("📝 Captions", callback_data=f"mgr_captions:{video_id}"),
            ],
            [
                InlineKeyboardButton("📊 Stats", callback_data=f"mgr_stats:{video_id}"),
                InlineKeyboardButton("⚙️ Advanced", callback_data=f"mgr_advanced:{video_id}"),
            ],
            [
                InlineKeyboardButton("🔗 Open on YouTube ↗", url=f"https://youtube.com/watch?v={video_id}"),
            ],
            [
                InlineKeyboardButton("🗑 Delete Video", callback_data=f"mgr_delete_confirm:{video_id}"),
                InlineKeyboardButton("« Back", callback_data="mgr_list:"),
            ]
        ])

    # ─── PRIVACY ────────────────────────────────────────────────

    @staticmethod
    def privacy(video_id: str, current: str) -> InlineKeyboardMarkup:
        def tick(p): return f"✅ " if current == p else ""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"{tick('public')}🌍 Public", callback_data=f"mgr_set_privacy:public:{video_id}"),
                InlineKeyboardButton(f"{tick('private')}🔒 Private", callback_data=f"mgr_set_privacy:private:{video_id}"),
                InlineKeyboardButton(f"{tick('unlisted')}🔗 Unlisted", callback_data=f"mgr_set_privacy:unlisted:{video_id}"),
            ],
            [InlineKeyboardButton("« Back", callback_data=f"mgr_video:{video_id}")]
        ])

    # ─── CATEGORY ───────────────────────────────────────────────

    @staticmethod
    def category(video_id: str, current_id: str = None) -> InlineKeyboardMarkup:
        from services.youtube_manager import CATEGORIES
        buttons = []
        row = []
        for cat_id, cat_name in CATEGORIES.items():
            tick = "✅ " if cat_id == current_id else ""
            row.append(InlineKeyboardButton(
                f"{tick}{cat_name[:20]}",
                callback_data=f"mgr_set_category:{cat_id}:{video_id}"
            ))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("« Back", callback_data=f"mgr_video:{video_id}")])
        return InlineKeyboardMarkup(buttons)

    # ─── PLAYLIST ───────────────────────────────────────────────

    @staticmethod
    def playlist_select(video_id: str, playlists: list) -> InlineKeyboardMarkup:
        buttons = []
        for p in playlists[:20]:
            pid = p["id"]
            title = p["snippet"]["title"][:30]
            count = p["contentDetails"]["itemCount"]
            buttons.append([InlineKeyboardButton(
                f"📋 {title} ({count})",
                callback_data=f"mgr_add_playlist:{pid}:{video_id}"
            )])
        buttons.append([
            InlineKeyboardButton("➕ New Playlist", callback_data=f"mgr_new_playlist:{video_id}"),
            InlineKeyboardButton("« Back", callback_data=f"mgr_video:{video_id}")
        ])
        return InlineKeyboardMarkup(buttons)

    # ─── CAPTIONS ───────────────────────────────────────────────

    @staticmethod
    def captions(video_id: str, captions: list) -> InlineKeyboardMarkup:
        buttons = []
        for c in captions:
            cid = c["id"]
            lang = c["snippet"]["language"]
            name = c["snippet"]["name"] or lang
            buttons.append([
                InlineKeyboardButton(f"🌐 {name} ({lang})", callback_data="noop"),
                InlineKeyboardButton("🗑", callback_data=f"mgr_del_caption:{cid}:{video_id}")
            ])
        buttons.append([
            InlineKeyboardButton("➕ Upload Caption", callback_data=f"mgr_upload_caption:{video_id}"),
            InlineKeyboardButton("« Back", callback_data=f"mgr_video:{video_id}")
        ])
        return InlineKeyboardMarkup(buttons)

    # ─── ADVANCED ───────────────────────────────────────────────

    @staticmethod
    def advanced(video_id: str, status: dict) -> InlineKeyboardMarkup:
        kids = status.get("selfDeclaredMadeForKids", False)
        embed = status.get("embeddable", True)
        lic = status.get("license", "youtube")

        return InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"👶 Made for Kids: {'✅ ON' if kids else 'OFF'}",
                callback_data=f"mgr_toggle_kids:{video_id}"
            )],
            [InlineKeyboardButton(
                f"🔗 Embeddable: {'✅ ON' if embed else 'OFF'}",
                callback_data=f"mgr_toggle_embed:{video_id}"
            )],
            [InlineKeyboardButton(
                f"📜 License: {'Creative Commons' if lic == 'creativeCommon' else 'Standard YouTube'}",
                callback_data=f"mgr_toggle_license:{video_id}"
            )],
            [InlineKeyboardButton("🕐 Schedule Publish", callback_data=f"mgr_schedule:{video_id}")],
            [InlineKeyboardButton("« Back", callback_data=f"mgr_video:{video_id}")]
        ])

    # ─── DELETE CONFIRM ─────────────────────────────────────────

    @staticmethod
    def delete_confirm(video_id: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes, Delete", callback_data=f"mgr_delete_do:{video_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"mgr_video:{video_id}"),
            ]
        ])