import os
import json
import logging
import httpx

logger = logging.getLogger(__name__)

ACCOUNT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "userbot", "account.json")

def load_userbot_file_data():
    if not os.path.exists(ACCOUNT_FILE):
        return {"enabled": True, "accounts": []}
    try:
        with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading userbot account.json: {e}")
        return {"enabled": True, "accounts": []}

def save_userbot_file_data(data: dict):
    os.makedirs(os.path.dirname(ACCOUNT_FILE), exist_ok=True)
    with open(ACCOUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_all_userbot_accounts():
    data = load_userbot_file_data()
    return data.get("accounts", [])

def load_userbot_accounts(active_only: bool = True):
    accounts = get_all_userbot_accounts()
    if active_only:
        return [acc for acc in accounts if acc.get("active", True)]
    return accounts

def get_userbot_by_id(account_id: int):
    accounts = get_all_userbot_accounts()
    for acc in accounts:
        if acc.get("id") == account_id:
            return acc
    return accounts[0] if accounts else None

def update_userbot_account(account_id: int, **fields) -> bool:
    data = load_userbot_file_data()
    accounts = data.get("accounts", [])
    updated = False
    for acc in accounts:
        if acc.get("id") == account_id:
            for k, v in fields.items():
                if v is not None:
                    acc[k] = v
            updated = True
            break
    if updated:
        save_userbot_file_data(data)
    return updated

async def attempt_send_gift_via_userbot(account_id: int, recipient_id: str, gift_tg_id: str, gift_text: str = None) -> dict:
    """Attempts to deliver gift using the Hydrogram userbot account.
    Returns warning if userbot lacks stars or session is inactive, while ensuring user knows gift will still be delivered manually!
    """
    account = get_userbot_by_id(account_id)
    if not account or not account.get("active"):
        return {
            "success": False,
            "warning": "⚠️ Payment received! Auto-delivery userbot is currently inactive, but do not worry — your gift will be sent manually by our team shortly!"
        }

    session_string = account.get("session_string")
    if not session_string:
        return {
            "success": False,
            "warning": "⚠️ Payment received! Userbot sender balance/session check pending. Do not worry — your gift will be sent manually by our team shortly!"
        }

    # Execute Hydrogram Client sending logic
    try:
        from hydrogram import Client
        from hydrogram.raw.functions.payments import SendGift
        from hydrogram.raw.types import InputUser

        api_id = account.get("api_id")
        api_hash = account.get("api_hash")

        async with Client(f"userbot_{account_id}", api_id=api_id, api_hash=api_hash, session_string=session_string, in_memory=True) as client:
            user = await client.get_users(recipient_id)
            if not user:
                return {
                    "success": False,
                    "warning": f"⚠️ Payment received! Target recipient {recipient_id} not found by userbot. Admin will send your gift manually!"
                }
            
            # Send gift call
            await client.invoke(
                SendGift(
                    user_id=await client.resolve_peer(user.id),
                    gift_id=int(gift_tg_id),
                    message=gift_text or ""
                )
            )
            return {"success": True, "message": "🎁 Gift sent successfully via Userbot!"}

    except Exception as e:
        err_msg = str(e)
        logger.error(f"Userbot gift transfer failed for account {account_id}: {err_msg}")
        return {
            "success": False,
            "warning": f"⚠️ Payment received! Sender userbot encountered an issue ({err_msg}). Do not worry — your gift will be sent manually by our team shortly!"
        }

async def verify_telegram_user(bot_token: str, query: str) -> dict:
    """Verifies whether a Telegram user exists by username or User ID via Bot API getChat."""
    clean_query = query.strip()
    if not clean_query:
        return {"exists": False, "error": "Empty query"}

    # Format username / user_id
    if clean_query.isdigit():
        target = int(clean_query)
    else:
        target = "@" + clean_query.lstrip("@")

    async with httpx.AsyncClient(timeout=6.0) as client:
        try:
            res = await client.post(
                f"https://api.telegram.org/bot{bot_token}/getChat",
                json={"chat_id": target}
            )
            data = res.json()
            if data.get("ok"):
                result = data["result"]
                username = result.get("username")
                first_name = result.get("first_name", "")
                last_name = result.get("last_name", "")
                full_name = f"{first_name} {last_name}".strip() or "Telegram User"
                
                # Fetch profile photo if available
                photo_url = None
                try:
                    photos_res = await client.post(
                        f"https://api.telegram.org/bot{bot_token}/getUserProfilePhotos",
                        json={"user_id": result["id"], "limit": 1}
                    )
                    photos_data = photos_res.json()
                    if photos_data.get("ok") and photos_data["result"]["total_count"] > 0:
                        file_id = photos_data["result"]["photos"][0][-1]["file_id"]
                        file_res = await client.post(
                            f"https://api.telegram.org/bot{bot_token}/getFile",
                            json={"file_id": file_id}
                        )
                        file_data = file_res.json()
                        if file_data.get("ok"):
                            file_path = file_data["result"]["file_path"]
                            photo_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
                except Exception as photo_err:
                    logger.warning(f"Failed to fetch profile photo: {photo_err}")

                return {
                    "exists": True,
                    "id": result["id"],
                    "username": f"@{username}" if username else None,
                    "first_name": first_name,
                    "last_name": last_name,
                    "full_name": full_name,
                    "photo_url": photo_url
                }
            else:
                return {"exists": False, "error": data.get("description", "User not found")}
        except Exception as e:
            logger.error(f"verify_telegram_user error for {target}: {e}")
            return {"exists": False, "error": str(e)}
