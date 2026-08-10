import asyncio
import json
import logging
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

async def poll_bot_updates(bot_data: dict):
    """Long-polling loop for a single managed bot instance."""
    token = bot_data["token"]
    bot_id = bot_data["id"]
    offset = 0
    logger.info(f"Started polling loop for Managed Bot @{bot_data.get('bot_username')} (ID {bot_id})")

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                # Check if bot is still active in DB
                curr = await get_managed_bot_by_id(bot_id)
                if not curr or not curr.get("active"):
                    logger.info(f"Stopping polling loop for Managed Bot ID {bot_id} (inactive or deleted)")
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

                    # Save incoming user message
                    saved = await save_bot_user_message(
                        token, user_id, user_username, user_first_name,
                        msg.get("message_id", 0), text, out=0, date_str=date_str
                    )

                    # Notify WebSocket clients
                    if _WEBSOCKET_BROADCAST_CALLBACK:
                        try:
                            await _WEBSOCKET_BROADCAST_CALLBACK(token, user_id, saved)
                        except Exception as wse:
                            logger.error(f"Bot WS broadcast failed: {wse}")

                    # Process Custom Command Scripts & Auto-Replies
                    commands_list = []
                    scripts_dict = {}
                    try:
                        commands_list = json.loads(curr.get("commands_json") or "[]")
                        scripts_dict = json.loads(curr.get("scripts_json") or "{}")
                    except Exception:
                        pass

                    reply_text = None

                    # Check exact command match (e.g. /start or custom)
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
    """Starts all active managed bots from DB on server startup."""
    try:
        bots = await get_all_managed_bots()
        for b in bots:
            if b.get("active"):
                await start_bot_instance(b)
    except Exception as e:
        logger.error(f"sync_all_managed_bots error: {e}")
