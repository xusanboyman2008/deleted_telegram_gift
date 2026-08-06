import os
import json
import logging
import httpx

logger = logging.getLogger(__name__)

ACCOUNT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "userbot", "account.json")

def load_userbot_accounts():
    if not os.path.exists(ACCOUNT_FILE):
        return []
    try:
        with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [acc for acc in data.get("accounts", []) if acc.get("active", True)]
    except Exception as e:
        logger.error(f"Error loading userbot account.json: {e}")
        return []

def get_userbot_by_id(account_id: int):
    accounts = load_userbot_accounts()
    for acc in accounts:
        if acc.get("id") == account_id:
            return acc
    return accounts[0] if accounts else None

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
