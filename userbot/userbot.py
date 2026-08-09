import os
import json
import logging
import httpx
import re

logger = logging.getLogger(__name__)

ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "account.json")
USER_ACCOUNTS_FILE = os.path.join(os.path.dirname(__file__), "user_accounts.json")

def load_userbot_file_data():
    # 1. Primary: Try reading from Database
    try:
        try:
            from backend.db import db_get_userbot_accounts
        except ImportError:
            from db import db_get_userbot_accounts
        db_accs = db_get_userbot_accounts()
        if db_accs:
            return {"enabled": True, "accounts": db_accs}
    except Exception as db_err:
        logger.error(f"Database userbot load failed: {db_err}")

    # 2. Fallback: Try reading JSON files
    for filepath in [ACCOUNT_FILE, USER_ACCOUNTS_FILE]:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if content.get("accounts"):
                        return content
            except Exception as e:
                logger.warning(f"Error reading {filepath}: {e}")

    return {"enabled": True, "accounts": []}


def save_userbot_file_data(data: dict):
    accounts = data.get("accounts", [])
    json_saved = False
    # 1. Save to JSON files
    for path in [ACCOUNT_FILE, USER_ACCOUNTS_FILE]:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            json_saved = True
        except Exception as e:
            logger.error(f"Failed to write to {path}: {e}")

    # 2. Always sync to Database as persistent fallback
    try:
        try:
            from backend.db import db_save_userbot_accounts
        except ImportError:
            from db import db_save_userbot_accounts
        db_save_userbot_accounts(accounts)
    except Exception as db_err:
        logger.error(f"Database sync save failed: {db_err}")
        if not json_saved:
            raise RuntimeError(f"Failed to save userbot accounts to both JSON and Database! Error: {db_err}")

def get_all_userbot_accounts():
    data = load_userbot_file_data()
    return data.get("accounts", [])

def load_userbot_accounts(active_only: bool = True, user_tg_id: int = None, is_admin: bool = False):
    accounts = get_all_userbot_accounts()
    if active_only:
        accounts = [acc for acc in accounts if acc.get("active", True)]
    
    if is_admin:
        return accounts
    
    if user_tg_id:
        # System userbots (no owner) + user's own account
        return [acc for acc in accounts if not acc.get("owner_tg_id") or acc.get("owner_tg_id") == user_tg_id]
    
    # Fallback for public: only system userbots
    return [acc for acc in accounts if not acc.get("owner_tg_id")]

def get_userbot_by_id(account_id):
    accounts = get_all_userbot_accounts()
    str_id = str(account_id)
    try:
        from backend.db import hash_userbot_id
    except ImportError:
        try:
            from db import hash_userbot_id
        except ImportError:
            hash_userbot_id = lambda x: str(x)

    for acc in accounts:
        if str(acc.get("id")) == str_id or hash_userbot_id(acc.get("id")) == str_id:
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
    Returns warning and error_type if userbot lacks stars or session is inactive, while ensuring user knows gift will still be delivered!
    """
    account = get_userbot_by_id(account_id)
    ub_name = account.get('first_name') or f"Account #{account_id}" if account else f"Account #{account_id}"
    
    if not account or not account.get("active"):
        return {
            "success": False,
            "error_type": "INACTIVE_USERBOT",
            "error": f"Userbot {ub_name} is inactive.",
            "warning": "⚠️ Payment received! Auto-delivery userbot is currently inactive, but do not worry — your gift will be sent automatically via Main Bot or manually by our team shortly!"
        }

    session_string = account.get("session_string")
    if not session_string:
        return {
            "success": False,
            "error_type": "MISSING_SESSION",
            "error": f"Userbot {ub_name} has no valid session string.",
            "warning": "⚠️ Payment received! Userbot sender session check pending. Do not worry — your gift will be sent automatically via Main Bot or manually by our team shortly!"
        }

    # Execute Hydrogram Client sending logic
    try:
        from hydrogram import Client
        from hydrogram.raw.functions.payments import SendGift

        api_id = account.get("api_id")
        api_hash = account.get("api_hash")

        async with Client(f"userbot_{account.get('id', 1)}", api_id=api_id, api_hash=api_hash, session_string=session_string, in_memory=True) as client:
            stars = await get_userbot_stars_balance(client)
            update_userbot_account(account.get("id"), stars_balance=stars)
            if stars < 55:
                return {
                    "success": False,
                    "error_type": "INSUFFICIENT_STARS",
                    "error": f"Userbot {ub_name} has only {stars} ⭐ Stars (minimum 55 ⭐ required).",
                    "warning": f"⚠️ Payment received! Userbot {ub_name} has only {stars} ⭐ Stars. Do not worry — your gift will be sent automatically via Main Bot or manually by our team shortly!"
                }

            user = await client.get_users(recipient_id)
            if not user:
                return {
                    "success": False,
                    "error_type": "RECIPIENT_NOT_FOUND",
                    "error": f"Target recipient {recipient_id} not found by userbot.",
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
            return {"success": True, "message": f"🎁 Gift sent successfully via Userbot {ub_name}!"}

    except Exception as e:
        err_msg = str(e)
        err_upper = err_msg.upper()
        logger.error(f"Userbot gift transfer failed for account {account.get('id', 1)}: {err_msg}")
        
        is_star_error = any(token in err_upper for token in [
            "BALANCE_TOO_LOW", "NOT_ENOUGH_STARS", "STARGIFT_USAGE_LIMITED", 
            "STAR", "BALANCE", "PAYMENT_REQUIRED", "PREPAYMENT_REQUIRED"
        ])
        
        if is_star_error:
            error_type = "INSUFFICIENT_STARS"
            clean_error = f"Userbot account {ub_name} has insufficient Telegram Stars balance to complete the transfer."
        else:
            error_type = "USERBOT_RPC_ERROR"
            clean_error = f"Userbot {ub_name} returned error: {err_msg}"

        return {
            "success": False,
            "error_type": error_type,
            "error": clean_error,
            "warning": f"⚠️ Payment received! {clean_error} Do not worry — your gift will be sent automatically via Main Bot or manually by our team shortly!"
        }

async def verify_telegram_user(bot_token: str, query: str) -> dict:
    """Verifies whether a Telegram user exists by username or User ID via Bot API getChat and Hydrogram Userbot.
    Downloads profile photo to frontend/assets/user_photos/{user_id}.jpg so frontend displays real profile image.
    """
    raw = query.strip()
    if not raw:
        return {"exists": False, "found": False, "error": "Empty query"}

    clean_query = re.sub(r'^(https?://)?(t\.me/|telegram\.me/)?@?', '', raw).strip()
    if not clean_query:
        return {"exists": False, "found": False, "error": "Invalid query"}

    is_id = clean_query.isdigit()
    target = int(clean_query) if is_id else clean_query
    bot_target = target if is_id else "@" + clean_query

    photos_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "assets", "user_photos"))
    os.makedirs(photos_dir, exist_ok=True)

    # 1. Try Telegram Bot API getChat first (fast & reliable for numeric IDs)
    async with httpx.AsyncClient(timeout=6.0) as http_client:
        try:
            res = await http_client.post(
                f"https://api.telegram.org/bot{bot_token}/getChat",
                json={"chat_id": bot_target}
            )
            data = res.json()
            if data.get("ok"):
                result = data["result"]
                user_id = result["id"]
                username = result.get("username")
                first_name = result.get("first_name", "")
                last_name = result.get("last_name", "")
                full_name = f"{first_name} {last_name}".strip() or "Telegram User"

                photo_url = None
                if result.get("photo"):
                    try:
                        file_id = result["photo"].get("big_file_id") or result["photo"].get("small_file_id")
                        if file_id:
                            f_res = await http_client.post(
                                f"https://api.telegram.org/bot{bot_token}/getFile",
                                json={"file_id": file_id}
                            )
                            f_data = f_res.json()
                            if f_data.get("ok"):
                                file_path = f_data["result"]["file_path"]
                                img_dl = await http_client.get(f"https://api.telegram.org/file/bot{bot_token}/{file_path}")
                                if img_dl.status_code == 200:
                                    photo_path = os.path.join(photos_dir, f"{user_id}.jpg")
                                    with open(photo_path, "wb") as f:
                                        f.write(img_dl.content)
                                    photo_url = f"assets/user_photos/{user_id}.jpg"
                    except Exception as photo_err:
                        logger.warning(f"Failed to download Bot API profile photo: {photo_err}")

                return {
                    "exists": True,
                    "found": True,
                    "id": user_id,
                    "username": f"@{username}" if username else f"ID:{user_id}",
                    "first_name": first_name,
                    "last_name": last_name,
                    "full_name": full_name,
                    "photo_url": photo_url
                }
        except Exception as e:
            logger.warning(f"Bot API getChat check failed for {bot_target}: {e}")

    # 2. Try Hydrogram Userbot resolution (resolves any username or peer on Telegram MTProto)
    accounts = get_all_userbot_accounts()
    active_acc = next((a for a in accounts if a.get("active") and a.get("session_string")), None)

    if active_acc:
        try:
            from hydrogram import Client
            api_id = active_acc.get("api_id")
            api_hash = active_acc.get("api_hash")
            session_string = active_acc.get("session_string")

            async with Client(f"verify_user_{active_acc['id']}", api_id=api_id, api_hash=api_hash, session_string=session_string, in_memory=True) as ub_client:
                try:
                    user = await ub_client.get_users(target)
                except Exception as get_usr_err:
                    logger.warning(f"Hydrogram get_users failed for {target}: {get_usr_err}")
                    user = None

                if user:
                    user_id = user.id
                    first_name = user.first_name or ""
                    last_name = user.last_name or ""
                    full_name = f"{first_name} {last_name}".strip() or "Telegram User"
                    username = f"@{user.username}" if user.username else f"ID:{user_id}"

                    photo_url = None
                    if user.photo:
                        try:
                            photo_path = os.path.join(photos_dir, f"{user_id}.jpg")
                            if not os.path.exists(photo_path):
                                try:
                                    await ub_client.download_media(user.photo.big_file_id or user.photo.small_file_id, file_name=photo_path)
                                except Exception:
                                    await ub_client.download_media(user.photo, file_name=photo_path)
                            if os.path.exists(photo_path):
                                photo_url = f"assets/user_photos/{user_id}.jpg"
                        except Exception as p_err:
                            logger.warning(f"Failed downloading profile photo via Userbot for user {user_id}: {p_err}")

                    return {
                        "exists": True,
                        "found": True,
                        "id": user_id,
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                        "full_name": full_name,
                        "photo_url": photo_url
                    }
                else:
                    return {"exists": False, "found": False, "error": "User does not exist on Telegram"}

        except Exception as ub_err:
            logger.error(f"Userbot verify_telegram_user exception: {ub_err}")

    return {"exists": False, "found": False, "error": "User does not exist on Telegram"}


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
        async with Client(f"ub_send_{account.get('id', 1)}", api_id=api_id, api_hash=api_hash, session_string=session_string, in_memory=True) as client:
            sent = await client.send_message(chat_id=target, text=message_text)
            return {
                "success": True,
                "message_id": sent.id,
                "chat_id": sent.chat.id
            }
    except Exception as e:
        logger.error(f"userbot_send_message failed for account {account.get('id', 1)}: {e}")
        return {"success": False, "error": str(e)}


# ── Web-based Interactive Phone Login ─────────────────────────────────────────
_PENDING_CLIENTS = {}


def normalize_phone(phone: str) -> str:
    clean = re.sub(r'[^\d+]', '', phone.strip())
    if clean and not clean.startswith('+'):
        clean = '+' + clean
    return clean


async def get_userbot_stars_balance(client) -> int:
    try:
        from hydrogram.raw.functions.payments import GetStarsStatus
        from hydrogram.raw.types import InputPeerSelf
        status = await client.invoke(GetStarsStatus(peer=InputPeerSelf()))
        return getattr(status, "balance", 0)
    except Exception as e:
        logger.warning(f"Could not fetch stars balance: {e}")
        return 0


import time

PENDING_SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "pending_sessions")
os.makedirs(PENDING_SESSIONS_DIR, exist_ok=True)


async def request_userbot_phone_code(phone: str, api_id: int = None, api_hash: str = None, force: bool = False) -> dict:
    clean_phone = normalize_phone(phone)
    if not clean_phone or len(clean_phone) < 7:
        return {"success": False, "error": "Valid phone number with country code is required (e.g. +998901234567)"}

    from hydrogram import Client

    data = load_userbot_file_data()
    accounts = data.get("accounts", [])
    first_acc = accounts[0] if accounts else {}

    use_api_id = api_id or first_acc.get("api_id") or 35251724
    use_api_hash = api_hash or first_acc.get("api_hash") or "b11e753959873b1df047454a8d816604"

    client_id = clean_phone.replace('+', '')
    session_path = os.path.join(PENDING_SESSIONS_DIR, f"pending_{client_id}")

    old_pending = _PENDING_CLIENTS.get(clean_phone)
    now = time.time()

    # Reuse active OTP session if requested less than 45s ago and force is not set
    if not force and old_pending and old_pending.get("client") and old_pending.get("phone_code_hash"):
        time_diff = now - old_pending.get("created_at", 0)
        if time_diff < 45:
            logger.info(f"Reusing active OTP session for {clean_phone} (sent {int(time_diff)}s ago)")
            return {"success": True, "message": f"Verification code already sent to {clean_phone}. Check your Telegram app."}

    if old_pending and old_pending.get("client") and old_pending["client"].is_connected:
        client = old_pending["client"]
    else:
        if old_pending:
            _PENDING_CLIENTS.pop(clean_phone, None)
            try:
                await old_pending["client"].disconnect()
            except Exception:
                pass
        # Use disk-backed session file for instant MTProto socket reused auth keys
        client = Client(session_path, api_id=use_api_id, api_hash=use_api_hash, ipv6=False)
        await client.connect()

    try:
        code_info = await client.send_code(clean_phone)
        _PENDING_CLIENTS[clean_phone] = {
            "client": client,
            "session_path": session_path,
            "phone_code_hash": code_info.phone_code_hash,
            "api_id": use_api_id,
            "api_hash": use_api_hash,
            "created_at": now,
        }
        return {"success": True, "message": f"Verification code sent to {clean_phone}"}
    except Exception as e:
        logger.error(f"request_userbot_phone_code error: {e}")
        _PENDING_CLIENTS.pop(clean_phone, None)
        try:
            await client.disconnect()
        except Exception:
            pass
        return {"success": False, "error": str(e)}


async def confirm_userbot_phone_code(phone: str, code: str, password: str = None, owner_tg_id: int = None, min_stars: int = 55) -> dict:
    clean_phone = normalize_phone(phone)
    pending = _PENDING_CLIENTS.get(clean_phone)

    client_id = clean_phone.replace('+', '')
    session_path = os.path.join(PENDING_SESSIONS_DIR, f"pending_{client_id}")

    from hydrogram import Client
    from hydrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired

    if pending and pending.get("client"):
        client = pending["client"]
        phone_code_hash = pending.get("phone_code_hash")
        api_id = pending.get("api_id", 35251724)
        api_hash = pending.get("api_hash", "b11e753959873b1df047454a8d816604")
    elif os.path.exists(session_path + ".session"):
        data = load_userbot_file_data()
        accounts = data.get("accounts", [])
        first_acc = accounts[0] if accounts else {}
        api_id = first_acc.get("api_id") or 35251724
        api_hash = first_acc.get("api_hash") or "b11e753959873b1df047454a8d816604"
        client = Client(session_path, api_id=api_id, api_hash=api_hash, ipv6=False)
        phone_code_hash = None
    else:
        return {"success": False, "error": "No pending login session found for this phone number. Please request code first."}

    completed_successfully = False
    clean_code = re.sub(r'\D', '', code or '')

    try:
        if not client.is_connected:
            await client.connect()

        try:
            if phone_code_hash:
                await client.sign_in(clean_phone, phone_code_hash, clean_code)
            else:
                await client.sign_in(clean_phone, "", clean_code)
        except SessionPasswordNeeded:
            if not password:
                return {"success": False, "requires_password": True, "error": "2FA Password is required for this account"}
            await client.check_password(password.strip())

        me = await client.get_me()
        session_str = await client.export_session_string()
        stars_balance = await get_userbot_stars_balance(client)

        if stars_balance < min_stars:
            _PENDING_CLIENTS.pop(clean_phone, None)
            try:
                await client.disconnect()
            except Exception:
                pass
            if os.path.exists(session_path + ".session"):
                try:
                    os.remove(session_path + ".session")
                except Exception:
                    pass
            return {
                "success": False,
                "error": f"Account @{me.username or me.first_name} has only {stars_balance} ⭐ Telegram Stars. You need at least {min_stars} ⭐ Telegram Stars to connect your account and do payments."
            }

        data = load_userbot_file_data()
        accounts = data.get("accounts", [])

        existing = next((a for a in accounts if a.get("phone") == clean_phone), None)
        if existing:
            existing["session_string"] = session_str
            existing["api_id"] = api_id
            existing["api_hash"] = api_hash
            existing["first_name"] = me.first_name or ""
            existing["last_name"] = me.last_name or ""
            existing["username"] = me.username or ""
            existing["active"] = True
            existing["stars_balance"] = stars_balance
            if owner_tg_id:
                existing["owner_tg_id"] = owner_tg_id
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
                "active": True,
                "owner_tg_id": owner_tg_id,
                "stars_balance": stars_balance
            }
            accounts.append(new_acc)
            acc_result = new_acc

        data["accounts"] = accounts
        save_userbot_file_data(data)

        # Sync user_accounts.json to ensure identical behavior to generate_sessions.py
        try:
            with open(USER_ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        _PENDING_CLIENTS.pop(clean_phone, None)
        completed_successfully = True

        try:
            from backend.db import hash_userbot_id
        except ImportError:
            try:
                from db import hash_userbot_id
            except ImportError:
                hash_userbot_id = lambda x: str(x)

        hashed_id = hash_userbot_id(acc_result["id"])
        sanitized_account = {
            "id": hashed_id,
            "first_name": (me.first_name or "").strip().split(" ")[0] or "Userbot",
            "last_name": me.last_name or "",
            "username": me.username or "",
            "photo": acc_result.get("photo", ""),
            "active": True,
            "owner_tg_id": owner_tg_id,
            "stars_balance": stars_balance
        }

        return {
            "success": True,
            "account": sanitized_account,
            "stars_balance": stars_balance,
            "message": f"Successfully authenticated {me.first_name} (@{me.username or 'no_user'}) with {stars_balance} ⭐ Stars!"
        }
    except (PhoneCodeInvalid, PhoneCodeExpired) as code_err:
        logger.warning(f"Invalid or expired login code for {clean_phone}: {code_err}")
        return {"success": False, "error": f"Invalid or expired verification code ({code_err}). Please check the latest code sent to Telegram."}
    except Exception as e:
        logger.error(f"confirm_userbot_phone_code error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        if completed_successfully:
            try:
                await client.disconnect()
            except Exception:
                pass
            if os.path.exists(session_path + ".session"):
                try:
                    os.remove(session_path + ".session")
                except Exception:
                    pass


def delete_userbot_account(account_id: int, owner_tg_id: int = None) -> bool:
    """Deletes a userbot account from storage. If owner_tg_id is specified, verifies ownership."""
    data = load_userbot_file_data()
    accounts = data.get("accounts", [])
    acc = next((a for a in accounts if a.get("id") == account_id), None)
    if not acc:
        return False

    if owner_tg_id and acc.get("owner_tg_id") != owner_tg_id:
        return False

    new_accs = [a for a in accounts if a.get("id") != account_id]
    data["accounts"] = new_accs
    save_userbot_file_data(data)
    return True


async def get_userbot_chat_history(account_id: int, recipient: str, limit: int = 20) -> list:
    """Fetches recent chat messages for recipient using Hydrogram client session if available."""
    account = get_userbot_by_id(account_id)
    if not account or not account.get("session_string"):
        return []

    session_string = account.get("session_string")
    api_id = account.get("api_id", 35251724)
    api_hash = account.get("api_hash", "b11e753959873b1df047454a8d816604")
    clean_target = recipient.strip()
    target = int(clean_target) if clean_target.isdigit() else ("@" + clean_target.lstrip("@"))

    try:
        from hydrogram import Client
        messages_out = []
        async with Client(f"chat_hist_{account_id}", api_id=api_id, api_hash=api_hash, session_string=session_string, in_memory=True) as client:
            async for m in client.get_chat_history(target, limit=limit):
                messages_out.append({
                    "id": m.id,
                    "text": m.text or m.caption or "",
                    "out": getattr(m, "outgoing", False),
                    "sender_name": m.from_user.first_name if m.from_user else ("Me" if getattr(m, "outgoing", False) else "User"),
                    "date": m.date.strftime("%H:%M") if m.date else "",
                })
        return list(reversed(messages_out))
    except Exception as e:
        logger.warning(f"get_userbot_chat_history failed for account {account_id}: {e}")
        return []


async def get_userbot_contacts(account_id: int, limit: int = 30) -> list:
    """Fetches recent dialogs (chat contacts) for account using Hydrogram client session."""
    account = get_userbot_by_id(account_id)
    if not account or not account.get("session_string"):
        return []

    session_string = account.get("session_string")
    api_id = account.get("api_id", 35251724)
    api_hash = account.get("api_hash", "b11e753959873b1df047454a8d816604")

    try:
        from hydrogram import Client
        contacts = []
        async with Client(f"contacts_{account_id}", api_id=api_id, api_hash=api_hash, session_string=session_string, in_memory=True) as client:
            async for dialog in client.get_dialogs(limit=limit):
                chat = dialog.chat
                is_bot = getattr(chat, 'is_bot', False)
                title = ""
                peer = ""

                if hasattr(chat, 'first_name'):
                    title = f"{chat.first_name or ''} {chat.last_name or ''}".strip()
                elif hasattr(chat, 'title'):
                    title = chat.title or ""

                if chat.username:
                    peer = f"@{chat.username}"
                else:
                    peer = str(chat.id)

                last_msg = ""
                last_time = ""
                last_out = False
                if dialog.top_message:
                    last_msg = dialog.top_message.text or dialog.top_message.caption or ""
                    if len(last_msg) > 60:
                        last_msg = last_msg[:60] + "..."
                    if dialog.top_message.date:
                        last_time = dialog.top_message.date.strftime("%H:%M")
                    last_out = getattr(dialog.top_message, "outgoing", False)

                contacts.append({
                    "peer": peer,
                    "title": title or peer,
                    "is_bot": is_bot,
                    "photo": None,
                    "last_msg": last_msg,
                    "last_time": last_time,
                    "last_out": last_out,
                    "unread": dialog.unread_messages_count or 0,
                    "online": False,
                })
        return contacts
    except Exception as e:
        logger.warning(f"get_userbot_contacts failed for account {account_id}: {e}")
        return []
