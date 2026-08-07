import os
import json
import logging
import httpx

logger = logging.getLogger(__name__)

ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "account.json")
USER_ACCOUNTS_FILE = os.path.join(os.path.dirname(__file__), "user_accounts.json")

def load_userbot_file_data():
    filepath = ACCOUNT_FILE if os.path.exists(ACCOUNT_FILE) else USER_ACCOUNTS_FILE
    if not os.path.exists(filepath):
        return {"enabled": True, "accounts": []}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading userbot account file: {e}")
        return {"enabled": True, "accounts": []}

def save_userbot_file_data(data: dict):
    for path in [ACCOUNT_FILE, USER_ACCOUNTS_FILE]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
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

def create_userbot_account(fields: dict) -> dict:
    data = load_userbot_file_data()
    accounts = data.get("accounts", [])
    max_id = max([acc.get("id", 0) for acc in accounts], default=0)
    new_acc = {
        "id": max_id + 1,
        "session": f"account_{max_id + 1}",
        "phone": fields.get("phone", ""),
        "session_string": fields.get("session_string", ""),
        "api_id": fields.get("api_id", 0),
        "api_hash": fields.get("api_hash", ""),
        "first_name": fields.get("first_name", ""),
        "last_name": fields.get("last_name", ""),
        "username": fields.get("username", ""),
        "bio": fields.get("bio", ""),
        "photo": fields.get("photo", ""),
        "active": fields.get("active", True)
    }
    accounts.append(new_acc)
    data["accounts"] = accounts
    save_userbot_file_data(data)
    return new_acc


async def sync_userbot_telegram_profile(account: dict):
    """Syncs userbot name, bio, username, and profile photo directly to Telegram using Hydrogram client."""
    session_string = account.get("session_string")
    if not session_string:
        return
    api_id = account.get("api_id")
    api_hash = account.get("api_hash")
    account_id = account.get("id")

    try:
        from hydrogram import Client
        async with Client(f"userbot_sync_{account_id}", api_id=api_id, api_hash=api_hash, session_string=session_string, in_memory=True) as client:
            first_name = account.get("first_name", "") or ""
            last_name = account.get("last_name", "") or ""
            bio = account.get("bio", "") or ""
            
            try:
                await client.update_profile(first_name=first_name, last_name=last_name, bio=bio)
                logger.info(f"Updated live profile for userbot {account_id}")
            except Exception as e:
                logger.warning(f"Live update_profile for userbot {account_id} error: {e}")

            if account.get("username"):
                clean_un = account["username"].lstrip("@")
                try:
                    await client.set_username(clean_un)
                    logger.info(f"Updated live username for userbot {account_id} to @{clean_un}")
                except Exception as e:
                    logger.warning(f"Live set_username for userbot {account_id} error: {e}")

            if account.get("photo") and (account["photo"].startswith("http") or os.path.exists(account["photo"])):
                try:
                    await client.set_profile_photo(photo=account["photo"])
                    logger.info(f"Updated live profile photo for userbot {account_id}")
                except Exception as e:
                    logger.warning(f"Live set_profile_photo for userbot {account_id} error: {e}")
    except Exception as e:
        logger.error(f"sync_userbot_telegram_profile failed for account {account_id}: {e}")


def update_userbot_account(account_id: int, **fields) -> bool:
    data = load_userbot_file_data()
    accounts = data.get("accounts", [])
    updated = False
    updated_acc = None
    for acc in accounts:
        if acc.get("id") == account_id:
            for k, v in fields.items():
                if v is not None:
                    acc[k] = v
            updated = True
            updated_acc = acc
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


async def userbot_send_message(account_id: int, recipient: str, message_text: str) -> dict:
    """Sends a message directly to a Telegram user by username or ID using the specified Hydrogram userbot session."""
    account = get_userbot_by_id(account_id)
    if not account:
        return {"success": False, "error": "Userbot account not found"}
    session_string = account.get("session_string")
    if not session_string:
        return {"success": False, "error": "Userbot session_string is missing or account has no session"}

    api_id = account.get("api_id")
    api_hash = account.get("api_hash")
    clean_target = recipient.strip()
    if clean_target.isdigit():
        target = int(clean_target)
    else:
        target = "@" + clean_target.lstrip("@")

    try:
        from hydrogram import Client
        async with Client(f"ub_send_{account_id}", api_id=api_id, api_hash=api_hash, session_string=session_string, in_memory=True) as client:
            sent = await client.send_message(chat_id=target, text=message_text)
            return {
                "success": True,
                "message_id": sent.id,
                "chat_id": sent.chat.id
            }
    except Exception as e:
        logger.error(f"userbot_send_message failed for account {account_id}: {e}")
        return {"success": False, "error": str(e)}


# ── Web-based Interactive Phone Login ─────────────────────────────────────────
_PENDING_CLIENTS = {}


async def request_userbot_phone_code(phone: str, api_id: int = None, api_hash: str = None) -> dict:
    clean_phone = phone.strip()
    if not clean_phone:
        return {"success": False, "error": "Phone number is required"}

    data = load_userbot_file_data()
    accounts = data.get("accounts", [])
    first_acc = accounts[0] if accounts else {}

    use_api_id = api_id or first_acc.get("api_id") or 35251724
    use_api_hash = api_hash or first_acc.get("api_hash") or "b11e753959873b1df047454a8d816604"

    from hydrogram import Client

    client = Client(f"web_login_{clean_phone}", api_id=use_api_id, api_hash=use_api_hash, in_memory=True)
    try:
        await client.connect()
        code_info = await client.send_code(clean_phone)
        _PENDING_CLIENTS[clean_phone] = {
            "client": client,
            "phone_code_hash": code_info.phone_code_hash,
            "api_id": use_api_id,
            "api_hash": use_api_hash,
        }
        return {"success": True, "message": f"Verification code sent to {clean_phone}"}
    except Exception as e:
        logger.error(f"request_userbot_phone_code error: {e}")
        try:
            await client.disconnect()
        except:
            pass
        return {"success": False, "error": str(e)}


async def confirm_userbot_phone_code(phone: str, code: str, password: str = None) -> dict:
    clean_phone = phone.strip()
    pending = _PENDING_CLIENTS.get(clean_phone)
    if not pending:
        return {"success": False, "error": "No pending login session found for this phone number. Please request code first."}

    client = pending["client"]
    phone_code_hash = pending["phone_code_hash"]
    api_id = pending["api_id"]
    api_hash = pending["api_hash"]

    from hydrogram.errors import SessionPasswordNeeded

    try:
        try:
            await client.sign_in(clean_phone, phone_code_hash, code.strip())
        except SessionPasswordNeeded:
            if not password:
                return {"success": False, "requires_password": True, "error": "2FA Password is required for this account"}
            await client.check_password(password.strip())

        me = await client.get_me()
        session_str = await client.export_session_string()

        data = load_userbot_file_data()
        accounts = data.get("accounts", [])
        
        # Check if phone already exists
        existing = next((a for a in accounts if a.get("phone") == clean_phone), None)
        if existing:
            existing["session_string"] = session_str
            existing["api_id"] = api_id
            existing["api_hash"] = api_hash
            existing["first_name"] = me.first_name or ""
            existing["last_name"] = me.last_name or ""
            existing["username"] = me.username or ""
            existing["active"] = True
            acc_result = existing
        else:
            max_id = max([a.get("id", 0) for a in accounts], default=0)
            new_acc = {
                "id": max_id + 1,
                "session": f"account_{max_id + 1}",
                "phone": clean_phone,
                "session_string": session_str,
                "api_id": api_id,
                "api_hash": api_hash,
                "first_name": me.first_name or "",
                "last_name": me.last_name or "",
                "username": me.username or "",
                "photo": "",
                "active": True
            }
            accounts.append(new_acc)
            acc_result = new_acc

        data["accounts"] = accounts
        save_userbot_file_data(data)
        _PENDING_CLIENTS.pop(clean_phone, None)

        return {
            "success": True,
            "account": acc_result,
            "message": f"Successfully authenticated {me.first_name} (@{me.username or 'no_user'})!"
        }
    except Exception as e:
        logger.error(f"confirm_userbot_phone_code error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        try:
            await client.disconnect()
        except:
            pass

