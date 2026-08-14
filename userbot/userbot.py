import os
import json
import logging
import httpx
import re
import asyncio
from hydrogram.raw.core import TLObject
from hydrogram.raw.core.primitives import Int, Long
from hydrogram.raw.types import TextWithEntities
from hydrogram.parser.html import HTML

logger = logging.getLogger(__name__)

from io import BytesIO


class InputInvoiceStarGift(TLObject):
    """inputInvoiceStarGift#e8625e92 — Used to buy a Telegram Star Gift via payments flow.
    
    TL Schema (Layer 223):
      inputInvoiceStarGift#e8625e92 flags:# hide_name:flags.0?true include_upgrade:flags.2?true
          peer:InputPeer gift_id:long message:flags.1?TextWithEntities = InputInvoice;
    """
    ID = 0xe8625e92
    QUALNAME = "types.InputInvoiceStarGift"

    def __init__(self, *, peer, gift_id: int, message: TextWithEntities = None,
                 hide_name: bool = False, include_upgrade: bool = False):
        self.peer = peer
        self.gift_id = gift_id
        self.message = message
        self.hide_name = hide_name
        self.include_upgrade = include_upgrade

    @staticmethod
    def read(b: BytesIO, *args) -> "InputInvoiceStarGift":
        return TLObject.read(b)

    def write(self, *args) -> bytes:
        b = BytesIO()
        b.write(Int(self.ID, False))
        flags = 0
        if self.hide_name:
            flags |= (1 << 0)
        if self.message and getattr(self.message, 'text', None):
            flags |= (1 << 1)
        if self.include_upgrade:
            flags |= (1 << 2)
        b.write(Int(flags))
        b.write(self.peer.write())
        b.write(Long(self.gift_id))
        if self.message and getattr(self.message, 'text', None):
            if not isinstance(getattr(self.message, 'entities', None), list):
                self.message.entities = []
            b.write(self.message.write())
        return b.getvalue()

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
    if is_admin:
        return accounts
    if active_only:
        accounts = [acc for acc in accounts if acc.get("active", True)]
    
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
        client = await get_running_client(account_id)
        if client:
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


async def update_userbot_account(account_id: int, **fields) -> bool:
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
        try:
            from backend.db import update_userbot_account_db
            await update_userbot_account_db(account_id, **fields)
        except Exception as e:
            logger.error(f"Failed to sync userbot {account_id} update to database: {e}")
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
        client = await get_running_client(account.get("id"))
        if not client:
            return {
                "success": False,
                "error": "Failed to connect Userbot sender account."
            }

        stars = await get_userbot_stars_balance(client)
        await update_userbot_account(account.get("id"), stars_balance=stars)

        rec_target = recipient_id
        if isinstance(recipient_id, str):
            clean_str = recipient_id.strip()
            if clean_str.startswith('@'):
                rec_target = clean_str
            elif clean_str.replace('-', '').isdigit():
                rec_target = int(clean_str)

        user = None
        try:
            user = await client.get_users(rec_target)
        except Exception as ge:
            logger.warning(f"get_users failed for {rec_target}: {ge}")

        peer = None
        try:
            if user and hasattr(user, 'id'):
                peer = await client.resolve_peer(user.id)
            else:
                peer = await client.resolve_peer(rec_target)
        except Exception as pe:
            logger.warning(f"resolve_peer failed for {rec_target}: {pe}")
            try:
                peer = await client.resolve_peer(rec_target)
            except Exception:
                peer = None

        if not peer:
            return {
                "success": False,
                "error_type": "RECIPIENT_NOT_FOUND",
                "error": f"Target recipient {recipient_id} not found by userbot.",
                "warning": f"⚠️ Payment received! Target recipient {recipient_id} not found by userbot. Admin will send your gift manually!"
            }
        
        # Parse rich text and custom Telegram premium emojis into TextWithEntities
        formatted_message = None
        if gift_text:
            try:
                clean_text = re.sub(r'<tg-emoji\s+emoji-id=["\']?(\d+)["\']?>([^<]*)</tg-emoji>', r'<emoji id="\1">\2</emoji>', gift_text)
                parsed = await HTML(client).parse(clean_text)
                raw_entities = parsed.get("entities") if parsed else None
                formatted_message = TextWithEntities(
                    text=parsed.get("message", gift_text) if parsed else gift_text,
                    entities=raw_entities if isinstance(raw_entities, list) else []
                )
            except Exception as pe:
                logger.warning(f"Rich text parse failed, falling back to plain text: {pe}")
                formatted_message = TextWithEntities(text=gift_text, entities=[])

        from hydrogram.raw.functions.payments import GetPaymentForm, SendStarsForm

        real_gift_map = {
            1: 5922558454332916696,
            2: 5956217000635139069,
            3: 5801108895304779062,
            4: 5800655655995968830,
            5: 5866352046986232958,
            6: 5893356958802511476,
            7: 5935895822435615975,
            8: 5969796561943660080,
            9: 6026193266406327981,
            10: 5974210632977745012
        }
        gift_id_num = int(gift_tg_id) if (gift_tg_id and str(gift_tg_id).isdigit()) else 1
        gift_id_val = real_gift_map.get(gift_id_num, gift_id_num)

        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            from telethon.tl.functions.payments import GetPaymentFormRequest, SendStarsFormRequest
            from telethon.tl.types import InputInvoiceStarGift as TelethonInputInvoiceStarGift
            from telethon.tl.types import TextWithEntities as TelethonTextWithEntities
            from telethon.tl.types import InputPeerUser, InputPeerChannel, InputPeerChat
            import base64
            import struct
            import ipaddress

            api_id = account.get("api_id") or 35251724
            api_hash = account.get("api_hash") or "b11e753959873b1df047454a8d816604"

            # Convert Hydrogram session to Telethon session
            padding = '=' * (4 - (len(session_string) % 4))
            decoded = base64.urlsafe_b64decode(session_string + padding)
            unpacked = struct.unpack('>BI?256sQ?', decoded)
            dc_id = unpacked[0]
            auth_key_bytes = unpacked[3]
            
            dc_ips = {
                1: "149.154.175.50",
                2: "149.154.167.51",
                3: "149.154.175.100",
                4: "149.154.167.91",
                5: "91.108.56.130",
            }
            ip_str = dc_ips.get(dc_id, "149.154.167.51")
            ip_bytes = ipaddress.ip_address(ip_str).packed
            
            telethon_session_str = '1' + base64.urlsafe_b64encode(
                struct.pack(f'>B{len(ip_bytes)}sH256s', dc_id, ip_bytes, 443, auth_key_bytes)
            ).decode('ascii')

            tele_client = TelegramClient(StringSession(telethon_session_str), api_id, api_hash)
            await tele_client.connect()
            
            try:
                if not await tele_client.is_user_authorized():
                    raise Exception("Telethon user session is not authorized.")

                # Convert Hydrogram resolved peer to Telethon peer
                peer_class = peer.__class__.__name__
                if peer_class == "InputPeerUser":
                    tele_peer = InputPeerUser(user_id=peer.user_id, access_hash=peer.access_hash)
                elif peer_class == "InputPeerChannel":
                    tele_peer = InputPeerChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
                elif peer_class == "InputPeerChat":
                    tele_peer = InputPeerChat(chat_id=peer.chat_id)
                else:
                    tele_peer = await tele_client.get_input_entity(rec_target)

                # Format message for Telethon
                tele_message = None
                if gift_text:
                    tele_message = TelethonTextWithEntities(text=gift_text, entities=[])

                # Construct invoice
                tele_invoice = TelethonInputInvoiceStarGift(
                    peer=tele_peer,
                    gift_id=gift_id_val,
                    message=tele_message,
                    hide_name=False
                )

                # Request payment form
                form_res = await tele_client(GetPaymentFormRequest(invoice=tele_invoice))
                form_id = getattr(form_res, "form_id", getattr(form_res, "id", 0))

                # Finalize payment
                await tele_client(SendStarsFormRequest(form_id=form_id, invoice=tele_invoice))
                logger.info(f"Gift sent successfully via Telethon for account {account_id}")
            finally:
                await tele_client.disconnect()

        except Exception as invoke_err:
            import traceback
            logger.error(f"Gift send via Telethon userbot invoke error traceback:\n{traceback.format_exc()}")
            raise invoke_err

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
    target = int(clean_query) if is_id else ("@" + clean_query)
    bot_target = target if is_id else ("@" + clean_query)

    photos_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "assets", "user_photos"))
    os.makedirs(photos_dir, exist_ok=True)

    # 1. Try Telegram Bot API getChat first (fast for numeric IDs or bot-interacted users)
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

    # 2. Hydrogram Userbot resolution (resolves any Telegram username or peer on MTProto)
    accounts = get_all_userbot_accounts()
    active_accs = [a for a in accounts if a.get("active") and a.get("session_string")]

    for active_acc in active_accs:
        try:
            ub_client = await get_running_client(active_acc['id'])
            if not ub_client:
                continue

            user = None
            # Try getting user from active client
            try:
                user = await ub_client.get_users(target)
            except Exception as e:
                logger.warning(f"Active client get_users failed for {target}: {e}")
                if isinstance(target, str) and not target.startswith("@"):
                    try:
                        user = await ub_client.get_users("@" + target)
                    except Exception:
                        pass

            if not user:
                try:
                    user = await ub_client.get_chat(target)
                except Exception:
                    if isinstance(target, str) and not target.startswith("@"):
                        try:
                            user = await ub_client.get_chat("@" + target)
                        except Exception:
                            pass

            if user:
                user_id = user.id
                first_name = getattr(user, "first_name", "") or ""
                last_name = getattr(user, "last_name", "") or ""
                full_name = f"{first_name} {last_name}".strip() or getattr(user, "title", "Telegram User")
                username = f"@{user.username}" if getattr(user, "username", None) else f"ID:{user_id}"

                photo_url = None
                if getattr(user, "photo", None):
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
        except Exception as ub_err:
            logger.warning(f"Userbot verify failed for account {active_acc.get('id')}: {ub_err}")

    return {"exists": False, "found": False, "error": "User does not exist on Telegram"}


async def userbot_send_message(account_id: int, recipient: str, message_text: str) -> dict:
    """Sends a message directly to a Telegram user by username or ID using the specified Hydrogram userbot session."""
    account = get_userbot_by_id(account_id)
    if not account:
        return {"success": False, "error": "Userbot account not found"}
    clean_target = recipient.strip()
    if clean_target.startswith('+'):
        target = clean_target
    elif clean_target.lstrip('-').isdigit():
        target = int(clean_target)
    else:
        target = "@" + clean_target.lstrip("@")


    try:
        client = await get_running_client(account_id)
        if not client:
            return {"success": False, "error": "Could not connect userbot client"}

        # Attempt sending directly; if peer is not cached in MTProto, resolve peer first via get_chat
        try:
            sent = await client.send_message(chat_id=target, text=message_text)
        except Exception as first_e:
            logger.info(f"Direct send_message failed ({first_e}), resolving peer {target}...")
            resolved_chat = await client.get_chat(target)
            if resolved_chat:
                sent = await client.send_message(chat_id=resolved_chat.id, text=message_text)
            else:
                raise first_e

        if _MESSAGE_CALLBACK:
            try:
                await _MESSAGE_CALLBACK(account_id, sent)
            except Exception as cb_err:
                logger.error(f"Error in message callback for outgoing userbot msg: {cb_err}")
        return {
            "success": True,
            "message_id": sent.id,
            "chat_id": sent.chat.id
        }
    except Exception as e:
        logger.error(f"userbot_send_message failed for account {account_id}: {e}")
        return {"success": False, "error": str(e)}


async def delete_userbot_chat_history(account_id: int, recipient: str) -> dict:
    """Deletes all messages in a chat for a userbot account on Telegram."""
    account = get_userbot_by_id(account_id)
    if not account:
        return {"success": False, "error": "Userbot account not found"}
    try:
        client = await get_running_client(account_id)
        if not client:
            return {"success": False, "error": "Could not connect userbot client"}
        
        clean_target = recipient.strip()
        if clean_target.lstrip('-').isdigit():
            target = int(clean_target)
        else:
            target = "@" + clean_target.lstrip("@")
            
        try:
            resolved_chat = await client.get_chat(target)
            target_id = resolved_chat.id
        except Exception:
            target_id = target
            
        await client.delete_chat_history(chat_id=target_id, revoke=True)
        return {"success": True}
    except Exception as e:
        logger.error(f"delete_userbot_chat_history failed: {e}")
        return {"success": False, "error": str(e)}


async def userbot_send_media(account_id: int, recipient: str, file_path: str, caption: str = "", media_type: str = "photo") -> dict:
    """Sends media (photo, video, audio, document) via userbot session."""
    account = get_userbot_by_id(account_id)
    if not account:
        return {"success": False, "error": "Userbot account not found"}
    clean_target = recipient.strip()
    if clean_target.startswith('+'):
        target = clean_target
    elif clean_target.lstrip('-').isdigit():
        target = int(clean_target)
    else:
        target = "@" + clean_target.lstrip("@")


    try:
        client = await get_running_client(account_id)
        if not client:
            return {"success": False, "error": "Could not connect userbot client"}

        # Ensure peer resolution
        chat_id = target
        try:
            resolved = await client.get_chat(target)
            if resolved:
                chat_id = resolved.id
        except Exception:
            pass

        if media_type == "photo":
            sent = await client.send_photo(chat_id=chat_id, photo=file_path, caption=caption or None)
        elif media_type == "video":
            sent = await client.send_video(chat_id=chat_id, video=file_path, caption=caption or None)
        elif media_type in ("audio", "voice", "music"):
            sent = await client.send_audio(chat_id=chat_id, audio=file_path, caption=caption or None)
        else:
            sent = await client.send_document(chat_id=chat_id, document=file_path, caption=caption or None)

        if _MESSAGE_CALLBACK:
            try:
                await _MESSAGE_CALLBACK(account_id, sent)
            except Exception:
                pass

        return {
            "success": True,
            "message_id": sent.id,
            "chat_id": sent.chat.id
        }
    except Exception as e:
        logger.error(f"userbot_send_media failed for account {account_id}: {e}")
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
        status = await asyncio.wait_for(client.invoke(GetStarsStatus(peer=InputPeerSelf())), timeout=6.0)
        raw_bal = getattr(status, "balance", 0)
        if hasattr(raw_bal, "amount"):
            return int(raw_bal.amount)
        return int(raw_bal)
    except Exception as e:
        logger.warning(f"Could not fetch stars balance: {e}")
        return None


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

        # Transfer active, connected client into global RUNNING cache for instant availability!
        try:
            from hydrogram.handlers import MessageHandler
            client.account_id = acc_result["id"]

            async def local_msg_handler(c, m):
                if _MESSAGE_CALLBACK:
                    try:
                        await _MESSAGE_CALLBACK(client.account_id, m)
                    except Exception as cb_err:
                        logger.error(f"Error in message callback for account {client.account_id}: {cb_err}")

            client.add_handler(MessageHandler(local_msg_handler))
            _RUNNING_USERBOTS[acc_result["id"]] = client
        except Exception as pre_err:
            logger.warning(f"Could not transition connected client to running cache: {pre_err}")

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


def delete_userbot_account(account_id, owner_tg_id: int = None) -> bool:
    """Deletes a userbot account from storage. Supports both raw integer ID and hashed string ID. If owner_tg_id is specified, verifies ownership."""
    data = load_userbot_file_data()
    accounts = data.get("accounts", [])
    
    acc = None
    str_id = str(account_id)
    try:
        from backend.db import hash_userbot_id
    except ImportError:
        try:
            from db import hash_userbot_id
        except ImportError:
            hash_userbot_id = lambda x: str(x)

    for a in accounts:
        if str(a.get("id")) == str_id or hash_userbot_id(a.get("id")) == str_id or str(a.get("phone")) == str_id:
            acc = a
            break

    if not acc:
        try:
            target_int = int(account_id)
            acc = next((a for a in accounts if a.get("id") == target_int), None)
        except (ValueError, TypeError):
            pass

    if not acc:
        return False

    if owner_tg_id and acc.get("owner_tg_id") != owner_tg_id:
        return False

    target_id = acc.get("id")

    if target_id in _RUNNING_USERBOTS:
        try:
            client = _RUNNING_USERBOTS.pop(target_id, None)
            if client:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(client.stop())
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Failed stopping client {target_id} on delete: {e}")

    new_accs = [a for a in accounts if a.get("id") != target_id]
    data["accounts"] = new_accs
    save_userbot_file_data(data)

    try:
        from backend.db import invalidate_userbot_accs_cache
        invalidate_userbot_accs_cache()
    except Exception:
        try:
            from db import invalidate_userbot_accs_cache
            invalidate_userbot_accs_cache()
        except Exception:
            pass

    return True


_RUNNING_USERBOTS = {}
_MESSAGE_CALLBACK = None

def set_message_callback(callback):
    global _MESSAGE_CALLBACK
    _MESSAGE_CALLBACK = callback

async def get_running_client(account_id: int):
    account_id = int(account_id)
    client = _RUNNING_USERBOTS.get(account_id)
    if client:
        if client.is_connected:
            client.last_used_time = time.time()
            return client
        else:
            try:
                await client.stop()
            except Exception:
                pass
            _RUNNING_USERBOTS.pop(account_id, None)

    account = get_userbot_by_id(account_id)
    if not account or not account.get("session_string"):
        return None

    session_string = account.get("session_string")
    api_id = account.get("api_id") or 35251724
    api_hash = account.get("api_hash") or "b11e753959873b1df047454a8d816604"

    from hydrogram import Client
    from hydrogram.handlers import MessageHandler

    client = Client(
        f"userbot_run_{account_id}",
        api_id=api_id,
        api_hash=api_hash,
        session_string=session_string,
        in_memory=True
    )
    client.account_id = account_id

    async def local_msg_handler(c, m):
        # Update last used time on incoming activity
        client.last_used_time = time.time()
        if _MESSAGE_CALLBACK:
            try:
                await _MESSAGE_CALLBACK(account_id, m)
            except Exception as cb_err:
                logger.error(f"Error in message callback for account {account_id}: {cb_err}")

    client.add_handler(MessageHandler(local_msg_handler))

    try:
        await asyncio.wait_for(client.start(), timeout=8.0)
        client.last_used_time = time.time()
        _RUNNING_USERBOTS[account_id] = client

        # Auto-fetch profile photo if missing in non-blocking task
        if account and not account.get("photo"):
            async def _bg_fetch_photo():
                try:
                    me = await client.get_me()
                    if me and me.photo:
                        p_file = await client.download_media(me.photo.small_file_id)
                        if p_file and os.path.exists(p_file):
                            with open(p_file, "rb") as f:
                                import base64
                                b64 = base64.b64encode(f.read()).decode("utf-8")
                                photo_data = f"data:image/jpeg;base64,{b64}"
                                account["photo"] = photo_data
                                await update_userbot_account(account_id, photo=photo_data)
                except Exception as pe:
                    logger.warning(f"Could not fetch profile photo for account {account_id}: {pe}")
            asyncio.create_task(_bg_fetch_photo())

        return client
    except Exception as e:
        logger.error(f"Failed to start running client for account {account_id}: {e}")
        return None

async def stop_all_running_userbots():
    for account_id, client in list(_RUNNING_USERBOTS.items()):
        try:
            await client.stop()
        except Exception:
            pass
    _RUNNING_USERBOTS.clear()

async def idle_userbots_cleanup_loop():
    import asyncio
    import gc
    import time
    # Wait initially for startup to settle
    await asyncio.sleep(60)
    logger.info("Starting background Idle Userbots RAM Cleanup Loop...")
    while True:
        try:
            now = time.time()
            to_stop = []
            for account_id, client in list(_RUNNING_USERBOTS.items()):
                # Auto-stop and unload userbots idle for more than 10 minutes (600s)
                last_used = getattr(client, "last_used_time", 0)
                if now - last_used > 600:
                    to_stop.append((account_id, client))

            for account_id, client in to_stop:
                logger.info(f"Reclaiming RAM: Stopping idle userbot {account_id}")
                _RUNNING_USERBOTS.pop(account_id, None)
                try:
                    await client.stop()
                except Exception as stop_err:
                    logger.warning(f"Error stopping userbot {account_id} during cleanup: {stop_err}")

            if to_stop:
                gc.collect()
        except Exception as loop_err:
            logger.warning(f"Error in idle_userbots_cleanup_loop: {loop_err}")
        # Check every 2 minutes
        await asyncio.sleep(120)

async def _download_media_to_disk_bg(client, file_id: str, subfolder: str, filename: str):
    """Downloads media in background to frontend asset directory."""
    import asyncio, os
    try:
        rel_dir = os.path.join("assets", subfolder)
        abs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", rel_dir))
        os.makedirs(abs_dir, exist_ok=True)
        abs_path = os.path.join(abs_dir, filename)
        if os.path.exists(abs_path) and os.path.getsize(abs_path) > 0:
            return f"{rel_dir}/{filename}"

        file_path = await asyncio.wait_for(client.download_media(file_id, file_name=abs_path), timeout=4.0)
        if file_path and os.path.exists(file_path):
            return f"{rel_dir}/{filename}"
    except Exception as ex:
        logger.warning(f"Background media download skipped for {filename}: {ex}")
    return None


async def get_userbot_chat_history(account_id: int, recipient: str, limit: int = 20) -> list:
    """Fetches recent chat messages for recipient using Hydrogram client session if available."""
    clean_target = recipient.strip()
    if clean_target.startswith('+'):
        target = clean_target
    elif clean_target.lstrip('-').isdigit():
        target = int(clean_target)
    else:
        target = "@" + clean_target.lstrip("@")

    try:
        client = await get_running_client(account_id)
        if not client:
            return []
        messages_out = []
        async for m in client.get_chat_history(target, limit=limit):
            buttons = []
            if m.reply_markup and hasattr(m.reply_markup, "inline_keyboard"):
                for row in m.reply_markup.inline_keyboard:
                    row_btns = []
                    for b in row:
                        row_btns.append({
                            "text": getattr(b, "text", ""),
                            "url": getattr(b, "url", None),
                            "callback_data": getattr(b, "callback_data", None)
                        })
                    if row_btns:
                        buttons.append(row_btns)

            photo_url = None
            if getattr(m, "photo", None):
                small_id = getattr(m.photo, "file_id", None)
                if small_id:
                    clean_id = re.sub(r'[^a-zA-Z0-9_-]', '', str(small_id))[:32]
                    fname = f"msg_photo_{clean_id}.jpg"
                    rel_p = f"assets/chat_media/{fname}"
                    abs_p = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", rel_p))
                    if os.path.exists(abs_p) and os.path.getsize(abs_p) > 0:
                        photo_url = rel_p
                    else:
                        asyncio.create_task(_download_media_to_disk_bg(client, small_id, "chat_media", fname))

            voice_url = None
            if getattr(m, "voice", None) or getattr(m, "audio", None):
                media_obj = getattr(m, "voice", None) or getattr(m, "audio", None)
                if media_obj and getattr(media_obj, "file_id", None):
                    clean_id = re.sub(r'[^a-zA-Z0-9_-]', '', str(media_obj.file_id))[:32]
                    fname = f"msg_voice_{clean_id}.ogg"
                    rel_v = f"assets/chat_media/{fname}"
                    abs_v = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", rel_v))
                    if os.path.exists(abs_v) and os.path.getsize(abs_v) > 0:
                        voice_url = rel_v
                    else:
                        asyncio.create_task(_download_media_to_disk_bg(client, media_obj.file_id, "chat_media", fname))

            messages_out.append({
                "id": m.id,
                "text": m.text or m.caption or "",
                "caption": m.caption or "",
                "photo": photo_url,
                "voice": voice_url,
                "out": getattr(m, "outgoing", False),
                "sender_name": m.from_user.first_name if m.from_user else ("Me" if getattr(m, "outgoing", False) else "User"),
                "date": m.date.strftime("%H:%M") if m.date else "",
                "buttons": buttons if buttons else None
            })
        return list(reversed(messages_out))
    except Exception as e:
        logger.warning(f"get_userbot_chat_history failed for account {account_id}: {e}")
        return []

_PHOTO_CACHE = {}
_CONTACTS_CACHE = {}

async def _download_and_cache_photo(client, file_id: str) -> str:
    import asyncio, os, re
    if not file_id:
        return None
    if file_id in _PHOTO_CACHE:
        return _PHOTO_CACHE[file_id]

    clean_id = re.sub(r'[^a-zA-Z0-9_-]', '', str(file_id))[:32]
    rel_path = f"assets/user_photos/thumb_{clean_id}.jpg"
    abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", rel_path))

    if os.path.exists(abs_path) and os.path.getsize(abs_path) > 0:
        _PHOTO_CACHE[file_id] = rel_path
        return rel_path

    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        bio = await asyncio.wait_for(client.download_media(file_id, in_memory=True), timeout=2.0)
        if bio and hasattr(bio, "getbuffer"):
            data = bio.getbuffer()
            if len(data) > 0:
                def _write_photo():
                    with open(abs_path, "wb") as f:
                        f.write(data)
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, _write_photo)
                _PHOTO_CACHE[file_id] = rel_path
                return rel_path
    except Exception:
        pass
    return None

async def get_userbot_contacts(account_id: int, limit: int = 30, offset: int = 0) -> list:
    """Fetches recent dialogs (chat contacts) with pagination and fast photo resolution for account."""
    import asyncio, time, os, re
    account_id = int(account_id)
    now = time.time()

    # Fast Return from Memory Cache (TTL 15 seconds for initial page)
    if offset == 0 and account_id in _CONTACTS_CACHE:
        cached_time, cached_list = _CONTACTS_CACHE[account_id]
        if now - cached_time < 15.0 and cached_list:
            return cached_list[:limit]

    account = get_userbot_by_id(account_id)
    if not account or not account.get("session_string"):
        return []

    try:
        client = await get_running_client(account_id)
        if not client:
            return _CONTACTS_CACHE.get(account_id, (0, []))[1][:limit]
        
        dialogs = []
        try:
            fetch_limit = min(offset + limit, 50)
            async def _fetch_dialogs_list():
                d_list = []
                cnt = 0
                async for dialog in client.get_dialogs(limit=fetch_limit):
                    if cnt >= offset:
                        d_list.append(dialog)
                        if len(d_list) >= limit:
                            break
                    cnt += 1
                return d_list

            dialogs = await asyncio.wait_for(_fetch_dialogs_list(), timeout=8.0)
        except Exception as d_err:
            logger.warning(f"get_dialogs fetch error for account {account_id}: {d_err}")
            if account_id in _CONTACTS_CACHE:
                return _CONTACTS_CACHE[account_id][1][:limit]

        contacts = []
        
        for dialog in dialogs:
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

            photo_url = None
            if chat.photo:
                small_id = getattr(chat.photo, 'small_file_id', None)
                if small_id:
                    if small_id in _PHOTO_CACHE:
                        photo_url = _PHOTO_CACHE[small_id]
                    else:
                        clean_id = re.sub(r'[^a-zA-Z0-9_-]', '', str(small_id))[:32]
                        rel_path = f"assets/user_photos/thumb_{clean_id}.jpg"
                        abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", rel_path))
                        if os.path.exists(abs_path) and os.path.getsize(abs_path) > 0:
                            _PHOTO_CACHE[small_id] = rel_path
                            photo_url = rel_path
                        else:
                            # Schedule non-blocking background avatar download
                            asyncio.create_task(_download_and_cache_photo(client, small_id))

            contact_data = {
                "peer": peer,
                "title": title or peer,
                "is_bot": is_bot,
                "photo": photo_url,
                "last_msg": last_msg,
                "last_time": last_time,
                "last_out": last_out,
                "unread": dialog.unread_messages_count or 0,
                "online": False,
            }
            contacts.append(contact_data)

        if contacts and offset == 0:
            _CONTACTS_CACHE[account_id] = (now, contacts)

        return contacts
    except Exception as e:
        logger.warning(f"get_userbot_contacts failed for account {account_id}: {e}")
        if account_id in _CONTACTS_CACHE:
            return _CONTACTS_CACHE[account_id][1][:limit]
        return []

