import asyncio
import json
import logging
import os
from datetime import datetime
import httpx

try:
    from db import (
        get_all_managed_bots, add_managed_bot, toggle_managed_bot_status,
        delete_managed_bot, update_managed_bot_commands, get_managed_bot_by_id,
        save_bot_user_message, get_bot_user_chat_history, get_bot_chat_contacts
    )
except ImportError:
    from backend.db import (
        get_all_managed_bots, add_managed_bot, toggle_managed_bot_status,
        delete_managed_bot, update_managed_bot_commands, get_managed_bot_by_id,
        save_bot_user_message, get_bot_user_chat_history, get_bot_chat_contacts
    )

logger = logging.getLogger(__name__)

# Active running bot polling tasks
_RUNNING_BOT_TASKS = {}
_WEBSOCKET_BROADCAST_CALLBACK = None

def set_bot_ws_broadcast_callback(cb):
    global _WEBSOCKET_BROADCAST_CALLBACK
    _WEBSOCKET_BROADCAST_CALLBACK = cb

async def validate_bot_token(token: str) -> dict:
    """Validates Bot API Token using getMe."""
    url = f"https://api.telegram.org/bot{token}/getMe"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url)
        data = r.json()
        if data.get("ok"):
            res = data["result"]
            return {
                "success": True,
                "bot_id": res.get("id"),
                "bot_username": res.get("username", ""),
                "bot_name": res.get("first_name", "")
            }
        else:
            return {"success": False, "error": data.get("description", "Invalid Bot Token")}

async def send_bot_api_message(token: str, chat_id: int, text: str):
    """Sends message from Bot API to a user."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
        return r.json()

async def send_bot_api_media(token: str, chat_id: int, file_path_or_url: str, caption: str = "", media_type: str = "photo"):
    """Sends media (photo, video, audio, document) from Bot API to a user."""
    method_map = {
        "photo": "sendPhoto",
        "video": "sendVideo",
        "audio": "sendAudio",
        "voice": "sendAudio",
        "music": "sendAudio",
        "document": "sendDocument"
    }
    method = method_map.get(media_type, "sendDocument")
    field_map = {
        "sendPhoto": "photo",
        "sendVideo": "video",
        "sendAudio": "audio",
        "sendDocument": "document"
    }
    field_name = field_map[method]
    url = f"https://api.telegram.org/bot{token}/{method}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        if file_path_or_url.startswith("http://") or file_path_or_url.startswith("https://"):
            # URL attachment
            payload = {"chat_id": chat_id, field_name: file_path_or_url, "caption": caption or "", "parse_mode": "HTML"}
            r = await client.post(url, json=payload)
            return r.json()
        elif os.path.exists(file_path_or_url):
            # Local file upload
            data = {"chat_id": str(chat_id), "caption": caption or "", "parse_mode": "HTML"}
            with open(file_path_or_url, "rb") as f:
                files = {field_name: (os.path.basename(file_path_or_url), f)}
                r = await client.post(url, data=data, files=files)
                return r.json()
        else:
            # Fallback URL string or asset path
            payload = {"chat_id": chat_id, field_name: file_path_or_url, "caption": caption or "", "parse_mode": "HTML"}
            r = await client.post(url, json=payload)
            return r.json()

async def fetch_bot_user_profile_photo(token: str, user_id: int) -> str:
    """Gets user profile photo from Telegram Bot API and returns it as base64 Data URL."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"https://api.telegram.org/bot{token}/getUserProfilePhotos"
            r = await client.get(url, params={"user_id": user_id, "limit": 1})
            if r.status_code != 200:
                return None
            data = r.json()
            if not data.get("ok") or not data.get("result") or not data["result"].get("photos"):
                return None
            
            photos = data["result"]["photos"][0]
            if not photos:
                return None
            # Smallest photo file_id
            file_id = photos[0]["file_id"]
            
            url_file = f"https://api.telegram.org/bot{token}/getFile"
            rf = await client.get(url_file, params={"file_id": file_id})
            if rf.status_code != 200:
                return None
            file_data = rf.json()
            if not file_data.get("ok") or not file_data.get("result"):
                return None
            
            file_path = file_data["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
            rd = await client.get(download_url)
            if rd.status_code == 200:
                import base64
                b64 = base64.b64encode(rd.content).decode("utf-8")
                return f"data:image/jpeg;base64,{b64}"
    except Exception as e:
        logger.warning(f"Failed to fetch profile photo for user {user_id}: {e}")
    return None

async def poll_bot_updates(bot_data: dict):
    """Long-polling loop for a single managed bot instance."""
    token = bot_data["token"]
    bot_id = bot_data["id"]
    offset = 0
    logger.info(f"Started polling loop for Managed Bot @{bot_data.get('bot_username')} (ID {bot_id})")

    try:
        from db import save_bot_user_profile
    except ImportError:
        from backend.db import save_bot_user_profile

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                # Check if bot is still active in DB
                curr = await get_managed_bot_by_id(bot_id)
                if not curr:
                    logger.info(f"Stopping polling loop for Managed Bot ID {bot_id} (deleted)")
                    break

                url = f"https://api.telegram.org/bot{token}/getUpdates"
                r = await client.get(url, params={"offset": offset, "timeout": 20})
                if r.status_code != 200:
                    await asyncio.sleep(5)
                    continue

                data = r.json()
                if not data.get("ok"):
                    await asyncio.sleep(5)
                    continue

                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message")
                    if not msg or "from" not in msg:
                        continue

                    user = msg["from"]
                    user_id = user["id"]
                    user_username = user.get("username", "")
                    user_first_name = user.get("first_name", "User")
                    text = msg.get("text", "")
                    date_str = datetime.now().strftime("%H:%M")

                    # Media/file extraction and download
                    media_type = None
                    media_data = None
                    file_name = None
                    file_id = None

                    if "photo" in msg:
                        media_type = "photo"
                        file_id = msg["photo"][-1]["file_id"]
                        file_name = "photo.jpg"
                    elif "document" in msg:
                        media_type = "document"
                        file_id = msg["document"]["file_id"]
                        file_name = msg["document"].get("file_name", "document")
                    elif "voice" in msg:
                        media_type = "voice"
                        file_id = msg["voice"]["file_id"]
                        file_name = "voice.ogg"
                    elif "audio" in msg:
                        media_type = "audio"
                        file_id = msg["audio"]["file_id"]
                        file_name = msg["audio"].get("file_name", "audio.mp3")
                    elif "video" in msg:
                        media_type = "video"
                        file_id = msg["video"]["file_id"]
                        file_name = "video.mp4"
                    elif "sticker" in msg:
                        media_type = "sticker"
                        file_id = msg["sticker"]["file_id"]
                        file_name = "sticker.webp"

                    if media_type and file_id:
                        try:
                            # getFile
                            url_file = f"https://api.telegram.org/bot{token}/getFile"
                            rf = await client.get(url_file, params={"file_id": file_id})
                            if rf.status_code == 200:
                                fd = rf.json()
                                if fd.get("ok") and fd.get("result"):
                                    file_path = fd["result"]["file_path"]
                                    download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
                                    rd = await client.get(download_url)
                                    if rd.status_code == 200:
                                        import base64
                                        import mimetypes
                                        mime, _ = mimetypes.guess_type(file_name)
                                        if not mime:
                                            mime = "application/octet-stream"
                                        b64 = base64.b64encode(rd.content).decode("utf-8")
                                        media_data = f"data:{mime};base64,{b64}"
                                        # If text is empty, set default description
                                        if not text:
                                            text = msg.get("caption") or f"Sent {media_type}"
                        except Exception as m_err:
                            logger.error(f"Failed downloading message media for bot: {m_err}")

                    # Fetch profile photo and metadata
                    try:
                        photo_b64 = await fetch_bot_user_profile_photo(token, user_id)
                        user_info_json = json.dumps({
                            "id": user_id,
                            "username": user_username,
                            "first_name": user_first_name,
                            "last_name": user.get("last_name", ""),
                            "language_code": user.get("language_code", ""),
                            "is_bot": user.get("is_bot", False)
                        })
                        await save_bot_user_profile(token, user_id, user_username, user_first_name, photo=photo_b64, info=user_info_json)
                    except Exception as pe:
                        logger.warning(f"Failed to fetch/save profile: {pe}")

                    # Save incoming user message
                    saved = await save_bot_user_message(
                        token, user_id, user_username, user_first_name,
                        msg.get("message_id", 0), text, out=0, date_str=date_str,
                        media_type=media_type, media_data=media_data, file_name=file_name
                    )

                    # Notify WebSocket clients
                    if _WEBSOCKET_BROADCAST_CALLBACK:
                        try:
                            await _WEBSOCKET_BROADCAST_CALLBACK(token, user_id, saved)
                        except Exception as wse:
                            logger.error(f"Bot WS broadcast failed: {wse}")

                    # Process Custom Command Scripts & Auto-Replies ONLY IF active
                    if curr.get("active"):
                        commands_list = []
                        scripts_dict = {}
                        try:
                            commands_list = json.loads(curr.get("commands_json") or "[]")
                            scripts_dict = json.loads(curr.get("scripts_json") or "{}")
                        except Exception:
                            pass

                        reply_text = None

                        # Check exact command match
                        cmd_clean = text.split()[0].lower() if text else ""
                        if cmd_clean in scripts_dict:
                            reply_text = scripts_dict[cmd_clean]
                        elif text in scripts_dict:
                            reply_text = scripts_dict[text]
                        elif cmd_clean == "/start":
                            reply_text = f"👋 Hello {user_first_name}! Welcome to @{curr.get('bot_username')}.\nHow can I help you today?"

                        # If auto-reply triggered, send response
                        if reply_text:
                            res = await send_bot_api_message(token, user_id, reply_text)
                            if res.get("ok"):
                                bot_msg_id = res["result"].get("message_id", 0)
                                saved_out = await save_bot_user_message(
                                    token, user_id, user_username, user_first_name,
                                    bot_msg_id, reply_text, out=1, date_str=date_str
                                )
                                if _WEBSOCKET_BROADCAST_CALLBACK:
                                    try:
                                        await _WEBSOCKET_BROADCAST_CALLBACK(token, user_id, saved_out)
                                    except Exception:
                                        pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in polling loop for Bot {bot_id}: {e}")
                await asyncio.sleep(5)

async def start_bot_instance(bot_data: dict):
    """Starts polling loop for a managed bot."""
    try:
        from config import BOT_TOKEN
    except ImportError:
        from backend.config import BOT_TOKEN

    token = bot_data.get("token", "")
    if token and token == BOT_TOKEN:
        logger.info(f"Skipping polling loop for main BOT_TOKEN (@{bot_data.get('bot_username')}) to prevent 409 Conflict")
        return

    bot_id = bot_data["id"]
    if bot_id in _RUNNING_BOT_TASKS:
        task = _RUNNING_BOT_TASKS[bot_id]
        if not task.done():
            return
    task = asyncio.create_task(poll_bot_updates(bot_data))
    _RUNNING_BOT_TASKS[bot_id] = task

async def stop_bot_instance(bot_id: int):
    """Stops polling loop for a managed bot."""
    if bot_id in _RUNNING_BOT_TASKS:
        task = _RUNNING_BOT_TASKS.pop(bot_id)
        if not task.done():
            task.cancel()

async def sync_all_managed_bots():
    """Starts all managed bots from DB on server startup to collect chats."""
    try:
        bots = await get_all_managed_bots()
        for b in bots:
            await start_bot_instance(b)
    except Exception as e:
        logger.error(f"sync_all_managed_bots error: {e}")
