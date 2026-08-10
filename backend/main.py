"""
Main FastAPI — Deleted Gift Shop
- Telegram initData HMAC authentication
- /api/invoice  → createInvoiceLink → tg.openInvoice()
- /api/my-orders → user's own order history
- Serves Vue 3 frontend
"""

import time
import json
import hmac
import hashlib
import logging
import httpx
import asyncio
import traceback
from datetime import datetime
from typing import Any, Optional, Union, Dict, List
from contextlib import asynccontextmanager
from urllib.parse import parse_qsl

user_last_invoice_time = {}

from fastapi import FastAPI, Request, HTTPException, Depends, Header, BackgroundTasks, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    LabeledPrice, WebAppInfo, MenuButtonWebApp, BotCommand,
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    PreCheckoutQueryHandler, MessageHandler, filters,
)
from starlette.middleware.base import BaseHTTPMiddleware
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import db
    from config import BOT_TOKEN, BASE_URL, ADMIN_ID
except ImportError:
    from backend import db
    from backend.config import BOT_TOKEN, BASE_URL, ADMIN_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Telegram initData HMAC verification ───────────────────────────────────────
def verify_init_data(init_data: str) -> dict | None:
    """Verify Telegram WebApp initData HMAC. Returns user dict or None."""
    if not init_data:
        return None
    try:
        params = dict(parse_qsl(init_data, keep_blank_values=True))
        hash_val = params.pop("hash", None)
        if not hash_val:
            return None
        data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, hash_val):
            return None
        user_str = params.get("user")
        return json.loads(user_str) if user_str else {}
    except Exception as e:
        logger.warning(f"initData verify error: {e}")
        return None


# ── Auth dependency ────────────────────────────────────────────────────────────
async def get_user(
    x_init_data: str = Header(None, alias="X-Init-Data"),
) -> dict:
    user = verify_init_data(x_init_data) if x_init_data else None
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


async def get_admin(user: dict = Depends(get_user)) -> dict:
    if user.get("id") != ADMIN_ID:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


# ── Bot handlers ───────────────────────────────────────────────────────────────
ptb_app: Application = None


CUSTOM_EMOJI_MAP = {
    "5866352046986232958": "5289761157173775507",  # Bunny Bear
    "5893356958802511476": "5317000922096769303",  # Balloon Bear
    "5801108895304779062": "5224628072619216265",  # Rose Bear
    "5935895822435615975": "5359736160224586485",  # Worker Bear
    "6026193266406327981": "5447213743417105726",  # Football Bear
    "5922558454332916696": "5345935030143196497",  # Santa Teddy
    "5974210632977745012": "5397971251878732060",  # Gnome Bear
    "5800655655995968830": "5226661632259691727",  # I Love U
    "5956217000635139069": "5379850840691476775",  # Christmas Tree
    "5969796561943660080": "5393309541620291208", 
}
STAR_CUSTOM_EMOJI_ID = "5294182967738923878"
STAR_EMOJI_HTML = f'<tg-emoji emoji-id="{STAR_CUSTOM_EMOJI_ID}">⭐️</tg-emoji>'


def get_tg_emoji_html(gift: dict) -> str:
    tg_id = str(gift.get("gift_tg_id", ""))
    custom_id = CUSTOM_EMOJI_MAP.get(tg_id)
    emoji_char = gift.get("emoji", "🎁")
    if custom_id:
        return f'<tg-emoji emoji-id="{custom_id}">{emoji_char}</tg-emoji>'
    return emoji_char


GIFT_IMAGE_MAP = {
    "bunny_bear.json": "bunny_basket.png",
    "joker_bear.json": "balloon_bear.png",
    "pink_bear.json": "rose_bear.png",
    "plumber_bear.json": "worker_bear.png",
    "football_bear.json": "football_bear.png",
    "santa_bear.json": "santa_teddy.png",
    "gnome_bear.json": "gnome_bear.png",
    "hear.json": "iloveu_bear.png",
    "green_tree.json": "green_tree.png",
    "hug_bear.json": "hug_bear.png",
}


def get_gift_image_url(gift: dict) -> str:
    anim = gift.get("animation", "")
    img_name = GIFT_IMAGE_MAP.get(anim, "bot_photo.png")
    return f"{BASE_URL}/assets/{img_name}"


async def build_main_keyboard():
    web_url = f"{BASE_URL}?ngrok-skip-browser-warning=ngrok-skip-browser-warning"
    keyboard = [
        [InlineKeyboardButton("🚀 Launch Mini App", web_app=WebAppInfo(url=web_url))],
        [
            InlineKeyboardButton("⚡ Buy in Bot", callback_data="bot_choose_gift"),
            InlineKeyboardButton("👤 Buy Direct", url="https://t.me/xusanboyman200")
        ],
        [
            InlineKeyboardButton("📜 My Orders", callback_data="bot_my_orders"),
            InlineKeyboardButton("ℹ️ Support", callback_data="bot_help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def build_gifts_keyboard():
    gifts = await db.get_all_gifts(active_only=True)
    keyboard = []
    row = []
    for g in gifts:
        name = g.get('display_name') or g['emoji']
        price = g['base_stars'] + g['commission']
        row.append(InlineKeyboardButton(f"{g['emoji']} {name} · {price}⭐", callback_data=f"gift_{g['id']}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    keyboard.append([InlineKeyboardButton("◀️ Back to Main Menu", callback_data="bot_catalog")])
    return InlineKeyboardMarkup(keyboard)


async def start_handler(update: Update, context):
    user = update.effective_user
    kb = await build_main_keyboard()
    caption = (
        f"✨ <b>PREMIUM DELETED GIFTS SHOP</b> ✨\n\n"
        f"👋 Welcome <b>{user.first_name}</b>!\n\n"
        f"Choose an option below to browse gifts, buy automatically with {STAR_EMOJI_HTML} <b>Telegram Stars</b>, or contact <b>@xusanboyman200</b> directly!\n\n"
        f"💬 <i>Need help? Type any message directly in this chat to contact support!</i>\n\n"
        f"👑 <b>Owner Contact:</b> <a href='https://t.me/xusanboyman200'>@xusanboyman200</a>"
    )
    banner_url = f"{BASE_URL}/assets/bot_photo.png"
    if update.callback_query:
        await edit_or_reply(update.callback_query, caption, photo_url=banner_url, reply_markup=kb)
    else:
        await update.message.reply_photo(
            photo=banner_url,
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb,
        )


async def edit_or_reply(query, text, photo_url=None, reply_markup=None, disable_web_page_preview=True):
    old_msg = query.message
    edited = False
    
    if photo_url:
        if old_msg.photo:
            try:
                from telegram import InputMediaPhoto
                await query.edit_message_media(
                    media=InputMediaPhoto(media=photo_url, caption=text, parse_mode="HTML"),
                    reply_markup=reply_markup
                )
                edited = True
            except Exception as e:
                logger.warning(f"edit_message_media failed: {e}")
        elif old_msg.caption or old_msg.text:
            pass
    else:
        if old_msg.photo or old_msg.caption:
            try:
                await query.edit_message_caption(caption=text, parse_mode="HTML", reply_markup=reply_markup)
                edited = True
            except Exception as e:
                logger.warning(f"edit_message_caption failed: {e}")
        else:
            try:
                await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)
                edited = True
            except Exception as e:
                logger.warning(f"edit_message_text failed: {e}")
                
    if not edited:
        # Send new message and delete old message cleanly!
        try:
            if photo_url:
                await old_msg.reply_photo(photo=photo_url, caption=text, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await old_msg.reply_text(text=text, parse_mode="HTML", reply_markup=reply_markup, disable_web_page_preview=disable_web_page_preview)
            
            try:
                await old_msg.delete()
            except Exception as del_err:
                logger.warning(f"Could not delete old message: {del_err}")
        except Exception as send_err:
            logger.error(f"Fallback send failed: {send_err}")


async def callback_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "bot_catalog":
        await start_handler(update, context)
        return

    if data == "bot_choose_gift":
        gifts_kb = await build_gifts_keyboard()
        text = f"🎁 <b>Select a Gift to Purchase:</b>\n\nTap any gift below to view details and proceed with {STAR_EMOJI_HTML} Telegram Stars payment!"
        await edit_or_reply(query, text, reply_markup=gifts_kb)
        return
        
    if data == "bot_help":
        help_text = (
            f"ℹ️ <b>Deleted Gifts Support</b>\n\n"
            f"💬 <b>How to Contact Support:</b>\n"
            f"Simply type your message or problem directly in this chat! It will be sent directly to <a href='https://t.me/xusanboyman200'>@xusanboyman200</a> who can reply to you right here.\n\n"
            f"• <b>Automatic Purchase:</b> Select any gift from the list and pay with {STAR_EMOJI_HTML} Telegram Stars.\n"
            f"• <b>Buy via Real User:</b> Contact <a href='https://t.me/xusanboyman200'>@xusanboyman200</a> directly for manual gift transfers!"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 Contact @xusanboyman200 Directly", url="https://t.me/xusanboyman200")],
            [InlineKeyboardButton("◀️ Back to Main Menu", callback_data="bot_catalog")]
        ])
        await edit_or_reply(query, help_text, reply_markup=kb, disable_web_page_preview=True)
        return

    if data == "bot_my_orders":
        user_id = query.from_user.id
        orders = await db.get_orders_by_user(user_id)
        if not orders:
            text = "📜 <b>My Orders</b>\n\nYou haven't placed any orders yet."
        else:
            text = f"📜 <b>My Orders ({len(orders)})</b>\n\n"
            for o in orders[:10]:
                emoji_html = get_tg_emoji_html(o)
                st = "✅ PAID" if o['status'] == 'paid' else "⏳ PENDING"
                text += f"• #{o['id']} {emoji_html} <b>{o.get('display_name','Gift')}</b> → <code>{o['recipient_id']}</code> ({o['total_stars']}{STAR_EMOJI_HTML}) [{st}]\n"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back to Main Menu", callback_data="bot_catalog")]])
        await edit_or_reply(query, text, reply_markup=kb)
        return

    if data == "admin_view_userbots":
        await userbots_command_handler(update, context)
        return

    if data.startswith("admin_toggle_ub_"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("Forbidden: Admin only", show_alert=True)
            return

        ub_id = int(data.split("_")[-1])
        try:
            from userbot.userbot import get_userbot_by_id, update_userbot_account
        except ImportError:
            from userbot import get_userbot_by_id, update_userbot_account

        acc = get_userbot_by_id(ub_id)
        if not acc:
            await query.answer("Userbot account not found", show_alert=True)
            return

        current_active = bool(acc.get("active", True))
        new_active = not current_active
        update_userbot_account(ub_id, active=new_active)
        await db.set_userbot_active_status(ub_id, new_active)

        action_word = "Re-enabled (Undone)" if new_active else "Disabled"
        await query.answer(f"✅ Userbot #{ub_id} has been {action_word}!", show_alert=True)
        await userbots_command_handler(update, context)
        return

    if data.startswith("gift_"):
        gift_id = int(data.split("_")[1])
        gift = await db.get_gift(gift_id)
        if not gift:
            await edit_or_reply(query, "Gift not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="bot_choose_gift")]]))
            return
            
        total = gift['base_stars'] + gift['commission']
        name = gift.get('display_name') or gift['emoji']
        emoji_html = get_tg_emoji_html(gift)
        photo_url = get_gift_image_url(gift)
        
        text = (
            f"🎁 {emoji_html} <b>{name}</b>\n\n"
            f"🗓 <b>Release Date:</b> {gift['date_label']}\n"
            f"{STAR_EMOJI_HTML} <b>Price:</b> {total} Stars ({gift['base_stars']} + {gift['commission']} fee)\n"
            f"🆔 <b>TG Gift ID:</b> <code>{gift['gift_tg_id']}</code>\n\n"
            f"👇 Choose how you want to purchase:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⚡ Buy with Bot ({total}⭐)", callback_data=f"buy_bot_{gift_id}")],
            [InlineKeyboardButton("👤 Buy via Real User (@xusanboyman200)", url="https://t.me/xusanboyman200")],
            [InlineKeyboardButton("◀️ Back to Gifts", callback_data="bot_choose_gift")]
        ])
        await edit_or_reply(query, text, photo_url=photo_url, reply_markup=kb)
        return

    if data.startswith("buy_bot_"):
        gift_id = int(data.split("_")[2])
        gift = await db.get_gift(gift_id)
        if not gift:
            return
        user = query.from_user
        total = gift['base_stars'] + gift['commission']
        name = gift.get('display_name') or gift['emoji']
        
        order_id = await db.create_order(
            buyer_tg_id=user.id,
            buyer_username=user.username or "",
            recipient_id=f"@{user.username}" if user.username else f"id{user.id}",
            recipient_type="username",
            gift_id=gift_id,
            total_stars=total
        )
        
        await context.bot.send_invoice(
            chat_id=user.id,
            title=f"🎁 {name}",
            description=f"Deleted Telegram Gift ({gift['date_label']})",
            payload=f"order_{order_id}",
            currency="XTR",
            prices=[LabeledPrice(label=name, amount=total)],
            start_parameter=f"gift_{gift_id}"
        )


async def pre_checkout_handler(update: Update, context):
    await update.pre_checkout_query.answer(ok=True)


async def deliver_gift_via_bot(bot, recipient_str: str, gift_tg_id: str, gift_text: str = None) -> bool:
    """Automated instant gift transfer via Telegram Bot API sendGift endpoint using gift_tg_id."""
    try:
        raw_id = recipient_str.strip()
        
        # 1. First try python-telegram-bot send_gift if supported natively
        if hasattr(bot, "send_gift"):
            try:
                target_user = int(raw_id) if raw_id.isdigit() else raw_id
                kwargs = {"user_id": target_user, "gift_id": gift_tg_id}
                if gift_text: kwargs["text"] = gift_text
                await bot.send_gift(**kwargs)
                logger.info(f"Successfully sent gift {gift_tg_id} to {recipient_str} via bot.send_gift")
                return True
            except Exception as e:
                logger.warning(f"bot.send_gift native call failed: {e}")

        # 2. Direct HTTP call to Telegram Bot API sendGift endpoint
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {"gift_id": gift_tg_id}
            if gift_text:
                payload["text"] = gift_text
            if raw_id.isdigit():
                payload["user_id"] = int(raw_id)
            else:
                payload["user_id"] = raw_id

            res = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendGift",
                json=payload
            )
            data = res.json()
            if data.get("ok"):
                logger.info(f"Successfully sent gift {gift_tg_id} to {recipient_str} via sendGift API")
                return True
            else:
                logger.warning(f"sendGift API call returned error: {data}")
                return False
    except Exception as e:
        logger.error(f"deliver_gift_via_bot error: {e}")
        return False


async def successful_payment_handler(update: Update, context):
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    charge_id = payment.telegram_payment_charge_id
    try:
        order_id = int(payload.replace("order_", ""))
        success = await db.update_order_status(order_id, "paid", charge_id)
        if not success:
            logger.warning(f"Order #{order_id} was already processed or missing. Skipping duplicate payment.")
            return

        order = await db.get_order(order_id)
        gift = await db.get_gift(order["gift_id"])
        gift_tg_id = gift.get("gift_tg_id")
        gift_text = order.get("gift_text")

        # Check sender selection (Main Bot or specific Userbot)
        sender_type = order.get("sender_type", "bot")
        userbot_id = order.get("userbot_id") or 1

        try:
            from userbot.userbot import attempt_send_gift_via_userbot
        except ImportError:
            from userbot import attempt_send_gift_via_userbot

        if sender_type in ("userbot", "myaccount"):
            res = await attempt_send_gift_via_userbot(userbot_id, order["recipient_id"], gift_tg_id, gift_text=gift_text)
            if not res.get("success"):
                logger.warning(f"Userbot delivery failed ({res.get('error')}). Attempting automatic fallback via Main Bot...")
                bot_delivered = await deliver_gift_via_bot(context.bot, order["recipient_id"], gift_tg_id, gift_text=gift_text)
                if bot_delivered:
                    res = {"success": True, "message": "🎁 Gift sent successfully via Main Shop Bot (automatic fallback)!"}
        else:
            bot_delivered = await deliver_gift_via_bot(context.bot, order["recipient_id"], gift_tg_id, gift_text=gift_text)
            if bot_delivered:
                res = {"success": True, "message": "🎁 Gift sent successfully via Main Shop Bot!"}
            else:
                res = await attempt_send_gift_via_userbot(userbot_id, order["recipient_id"], gift_tg_id, gift_text=gift_text)

        if res.get("success"):
            await db.update_order_status(order_id, "delivered", charge_id)
            await update.message.reply_text(
                f"🎉 <b>GIFT PURCHASED & DELIVERED INSTANTLY!</b>\n\n"
                f"{gift['emoji']} <b>{gift.get('display_name') or gift['emoji']}</b> has been sent to <b>{order['recipient_id']}</b>!\n\n"
                f"Thank you for buying via TgGifts Bot!",
                parse_mode="HTML",
            )
        else:
            warning_msg = res.get("warning") or (
                "⚠️ <b>Note: Your Stars payment was received successfully!</b>\n\n"
                "Automatic bot transfer had a limit/balance issue, but <b>do not worry — your gift will be sent manually by our team shortly!</b>"
            )
            await update.message.reply_text(
                f"✅ <b>Payment Received!</b>\n\n"
                f"Gift: {gift['emoji']} <b>{gift.get('display_name') or gift['emoji']}</b>\n"
                f"Recipient: <b>{order['recipient_id']}</b>\n\n"
                f"{warning_msg}",
                parse_mode="HTML",
            )

        if ADMIN_ID:
            err_type = res.get("error_type", "UNKNOWN")
            if res.get("success"):
                status_note = "✅ Delivered automatically!"
            elif err_type == "INSUFFICIENT_STARS":
                status_note = "🚨 URGENT: Userbot Stars balance insufficient!"
            else:
                status_note = "⚠️ Pending Manual Fulfill"
                
            note_str = f"\nMessage: {gift_text}" if gift_text else ""
            err_detail = f"\nError Detail: <code>{res.get('error','')}</code>" if not res.get("success") else ""
            await context.bot.send_message(
                ADMIN_ID,
                f"🔔 <b>Paid Order #{order_id}</b> ({status_note})\n\n"
                f"Buyer: @{order.get('buyer_username') or order['buyer_tg_id']}\n"
                f"Gift: {gift.get('display_name') or gift['emoji']} (TG ID: {gift_tg_id})\n"
                f"Recipient: <b>{order['recipient_id']}</b>{note_str}\n"
                f"Stars Paid: <b>{order['total_stars']} ⭐</b>\n"
                f"Charge ID: <code>{charge_id}</code>{err_detail}",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"payment handler error: {e}")


async def admin_command_handler(update: Update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    orders = await db.get_all_orders()
    total_stars = sum(o['total_stars'] for o in orders if o.get('status') == 'paid')
    paid_count = sum(1 for o in orders if o.get('status') == 'paid')
    
    msg = (
        f"⚙️ <b>Admin Dashboard & Stats</b>\n\n"
        f"💰 <b>Total Earned:</b> {total_stars} ⭐ Stars\n"
        f"📦 <b>Completed Orders:</b> {paid_count}\n"
        f"📋 <b>Total Requests:</b> {len(orders)}\n\n"
        f"<b>Recent Orders:</b>\n"
    )
    if not orders:
        msg += "<i>No orders recorded yet.</i>"
    else:
        for o in orders[:8]:
            buyer = f"@{o['buyer_username']}" if o.get('buyer_username') else f"ID:{o['buyer_tg_id']}"
            msg += f"• #{o['id']} {o.get('emoji','🎁')} → <b>{o['recipient_id']}</b> from {buyer} ({o['total_stars']}⭐) [{o['status']}]\n"
        
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Manage Userbots (Enable/Disable)", callback_data="admin_view_userbots")]
    ])
    if update.callback_query:
        await edit_or_reply(update.callback_query, msg, reply_markup=kb)
    else:
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=kb)


async def userbots_command_handler(update: Update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    try:
        from userbot.userbot import get_all_userbot_accounts
    except ImportError:
        from userbot import get_all_userbot_accounts

    accounts = get_all_userbot_accounts()
    if not accounts:
        msg = "🤖 <b>No userbot accounts found.</b>"
        if update.callback_query:
            await edit_or_reply(update.callback_query, msg)
        else:
            await update.message.reply_text(msg, parse_mode="HTML")
        return

    msg = "🤖 <b>Userbot Accounts & Status Management</b>\n\n<i>Tap a button below to Disable or Re-enable (Undo) a userbot account:</i>\n\n"
    keyboard = []
    for acc in accounts:
        acc_id = acc.get("id")
        name = acc.get("first_name") or f"Account #{acc_id}"
        un = f" (@{acc['username']})" if acc.get("username") else ""
        is_active = bool(acc.get("active", True))
        status_icon = "🟢 ACTIVE" if is_active else "🔴 DISABLED"
        
        msg += f"• <b>#{acc_id} {name}</b>{un} — [{status_icon}]\n"
        
        btn_text = f"🔴 Disable #{acc_id} ({name})" if is_active else f"↩️ Undo / Enable #{acc_id} ({name})"
        cb_data = f"admin_toggle_ub_{acc_id}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=cb_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await edit_or_reply(update.callback_query, msg, reply_markup=reply_markup)
    else:
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)


import re


async def user_message_or_admin_reply_handler(update: Update, context):
    msg = update.message
    if not msg or not msg.text:
        return

    if msg.text == "❌ Cancel":
        from telegram import ReplyKeyboardRemove
        await msg.reply_text("Keyboard removed.", reply_markup=ReplyKeyboardRemove())
        return
        
    user = msg.from_user
    user_id = user.id
    username = user.username or user.first_name

    # 1. ADMIN REPLIES TO A FORWARDED SUPPORT MESSAGE
    if ADMIN_ID and user_id == ADMIN_ID and msg.reply_to_message:
        reply_txt = msg.reply_to_message.text or msg.reply_to_message.caption or ""
        match = re.search(r"\[USER_ID:\s*(\d+)\]", reply_txt)
        if match:
            target_user_id = int(match.group(1))
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"💬 <b>Support Reply from @xusanboyman200:</b>\n\n{msg.text}",
                    parse_mode="HTML"
                )
                await msg.reply_text(f"✅ Reply delivered to user <code>{target_user_id}</code>!", parse_mode="HTML")
                return
            except Exception as e:
                await msg.reply_text(f"❌ Failed to send reply: {e}")
                return

    # 2. USER SENDS A TEXT MESSAGE TO BOT -> FORWARD TO ADMIN AS SUPPORT
    if ADMIN_ID and user_id != ADMIN_ID:
        try:
            admin_notice = (
                f"📩 <b>Support Inquiry from @{username}</b> [USER_ID: {user_id}]:\n\n"
                f"{msg.text}\n\n"
                f"<i>(💡 Reply directly to this message to answer the user!)</i>"
            )
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_notice,
                parse_mode="HTML"
            )
            await msg.reply_text(
                "📬 <b>Your support message has been sent to @xusanboyman200!</b>\n\n"
                "The owner will respond to you right here shortly.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Support forward error: {e}")


class ConnectionManager:
    def __init__(self):
        self.active_connections = {}
        self.global_connections = []

    async def connect(self, websocket: WebSocket, account_id: str, recipient: str):
        key = (str(account_id), str(recipient).lower().replace("@", ""))
        if key not in self.active_connections:
            self.active_connections[key] = []
        self.active_connections[key].append(websocket)

    def disconnect(self, websocket: WebSocket, account_id: str, recipient: str):
        key = (str(account_id), str(recipient).lower().replace("@", ""))
        if key in self.active_connections:
            if websocket in self.active_connections[key]:
                self.active_connections[key].remove(websocket)
            if not self.active_connections[key]:
                del self.active_connections[key]

    async def connect_global(self, websocket: WebSocket):
        if websocket not in self.global_connections:
            self.global_connections.append(websocket)

    def disconnect_global(self, websocket: WebSocket):
        if websocket in self.global_connections:
            self.global_connections.remove(websocket)

    async def broadcast_to_chat(self, account_id: str, recipient: str, payload: dict):
        clean_recipient = str(recipient).lower().replace("@", "")
        key = (str(account_id), clean_recipient)
        sockets = self.active_connections.get(key, [])
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                pass

    async def broadcast_global(self, payload: dict):
        for ws in list(self.global_connections):
            try:
                await ws.send_json(payload)
            except Exception:
                pass

ws_manager = ConnectionManager()

async def ws_bot_message_callback(bot_token: str, user_id: int, msg_data: dict):
    payload = {
        "event": "bot_message",
        "bot_token": bot_token,
        "user_id": user_id,
        "message": msg_data
    }
    await ws_manager.broadcast_global(payload)
    await ws_manager.broadcast_to_chat(bot_token, str(user_id), payload)

async def ws_new_message_callback(account_id: int, message):
    chat_id = str(message.chat.id)
    username = str(message.chat.username or "").lower()
    
    buttons = []
    if message.reply_markup and hasattr(message.reply_markup, "inline_keyboard"):
        for row in message.reply_markup.inline_keyboard:
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
    if getattr(message, "photo", None):
        try:
            from userbot.userbot import get_running_client
            client = await get_running_client(account_id)
            if client:
                file_path = await client.download_media(message.photo.file_id)
                if file_path and os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                        photo_url = f"data:image/jpeg;base64,{b64}"
                    try: os.remove(file_path)
                    except: pass
        except Exception:
            pass

    voice_url = None
    if getattr(message, "voice", None) or getattr(message, "audio", None):
        try:
            from userbot.userbot import get_running_client
            client = await get_running_client(account_id)
            if client:
                media_obj = getattr(message, "voice", None) or getattr(message, "audio", None)
                file_path = await client.download_media(media_obj.file_id)
                if file_path and os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                        voice_url = f"data:audio/ogg;base64,{b64}"
                    try: os.remove(file_path)
                    except: pass
        except Exception:
            pass

    payload = {
        "event": "message",
        "account_id": account_id,
        "peer": username or chat_id,
        "message": {
            "id": message.id,
            "text": message.text or message.caption or "",
            "caption": message.caption or "",
            "photo": photo_url,
            "voice": voice_url,
            "out": getattr(message, "outgoing", False),
            "sender_name": message.from_user.first_name if message.from_user else ("Me" if getattr(message, "outgoing", False) else "User"),
            "date": message.date.strftime("%H:%M") if message.date else "",
            "buttons": buttons if buttons else None
        }
    }
    
    await ws_manager.broadcast_to_chat(str(account_id), chat_id, payload)
    if username:
        await ws_manager.broadcast_to_chat(str(account_id), username, payload)
    await ws_manager.broadcast_global(payload)


async def uptime_pinger():
    import asyncio
    import httpx
    # Wait initially for startup to settle
    await asyncio.sleep(15)
    logger.info("Starting background Uptime Pinger...")
    url = f"{BASE_URL.rstrip('/')}/"
    async with httpx.AsyncClient(verify=False) as client:
        while True:
            try:
                # Ping itself to keep server awake
                r = await client.get(url, timeout=15.0)
                logger.info(f"Uptime Pinger: pinged {url}, status code: {r.status_code}")
            except Exception as e:
                logger.warning(f"Uptime Pinger failed to ping {url}: {e}")
            # sleep between 30 and 50 seconds (average 40s)
            await asyncio.sleep(40)


async def select_command_handler(update: Update, context):
    from telegram import ReplyKeyboardMarkup, KeyboardButtonRequestUsers, KeyboardButtonRequestChat, KeyboardButton
    
    keyboard = [
        [
            KeyboardButton("👤 Select User", request_users=KeyboardButtonRequestUsers(request_id=1, user_is_bot=False)),
            KeyboardButton("💬 Select Chat", request_chat=KeyboardButtonRequestChat(request_id=2, chat_is_channel=False))
        ],
        [
            KeyboardButton("❌ Cancel")
        ]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Please select a user or chat below to retrieve their ID:",
        reply_markup=reply_markup
    )

async def shared_user_handler(update: Update, context):
    shared = update.message.user_shared
    user_id = shared.user_id
    req_id = shared.request_id
    await update.message.reply_text(
        f"✅ <b>User Shared Successfully!</b>\n\n"
        f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
        f"🔢 <b>Request ID:</b> <code>{req_id}</code>\n\n"
        f"You can copy this User ID and paste it in the Gift Shop Mini App recipient input!",
        parse_mode="HTML"
    )

async def shared_chat_handler(update: Update, context):
    shared = update.message.chat_shared
    chat_id = shared.chat_id
    req_id = shared.request_id
    await update.message.reply_text(
        f"✅ <b>Chat Shared Successfully!</b>\n\n"
        f"💬 <b>Chat ID:</b> <code>{chat_id}</code>\n"
        f"🔢 <b>Request ID:</b> <code>{req_id}</code>\n\n"
        f"You can copy this Chat ID and paste it in the Gift Shop Mini App recipient input!",
        parse_mode="HTML"
    )


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global ptb_app
    import asyncio
    asyncio.create_task(uptime_pinger())
    try:
        from userbot.userbot import idle_userbots_cleanup_loop
        asyncio.create_task(idle_userbots_cleanup_loop())
    except Exception as e:
        logger.warning(f"Could not start idle_userbots_cleanup_loop: {e}")
    await db.init_db()
    ptb_app = Application.builder().token(BOT_TOKEN).updater(None).build()
    ptb_app.add_handler(CommandHandler("start", start_handler))
    ptb_app.add_handler(CommandHandler("gifts", start_handler))
    ptb_app.add_handler(CommandHandler("menu", start_handler))
    ptb_app.add_handler(CommandHandler("admin", admin_command_handler))
    ptb_app.add_handler(CommandHandler("stats", admin_command_handler))
    ptb_app.add_handler(CommandHandler("userbots", userbots_command_handler))
    ptb_app.add_handler(CommandHandler("select", select_command_handler))
    ptb_app.add_handler(CommandHandler("share", select_command_handler))
    ptb_app.add_handler(CallbackQueryHandler(callback_handler))
    ptb_app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    user_shared_filter = getattr(filters.StatusUpdate, "USERS_SHARED", getattr(filters.StatusUpdate, "USER_SHARED", None))
    if user_shared_filter:
        ptb_app.add_handler(MessageHandler(user_shared_filter, shared_user_handler))

    chat_shared_filter = getattr(filters.StatusUpdate, "CHAT_SHARED", None)
    if chat_shared_filter:
        ptb_app.add_handler(MessageHandler(chat_shared_filter, shared_chat_handler))
    ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_message_or_admin_reply_handler))
    await ptb_app.initialize()
    await ptb_app.start()

    webhook_url = f"{BASE_URL}/webhook"
    try:
        await ptb_app.bot.set_webhook(webhook_url, drop_pending_updates=True)
        logger.info(f"Webhook: {webhook_url}")
    except Exception as e:
        logger.warning(f"Failed to set webhook ({e}), continuing...")

    mini_app_url = f"{BASE_URL}/index.html?ngrok-skip-browser-warning=69420"
    try:
        await ptb_app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="🎁 Open Shop", web_app=WebAppInfo(url=mini_app_url))
        )
    except Exception as e:
        logger.warning(f"Menu button: {e}")
    try:
        await ptb_app.bot.set_my_commands([
            BotCommand("start", "Open the Gift Shop"),
        ])
    except Exception as e:
        logger.warning(f"Commands: {e}")

    # Set message callback for WebSockets
    try:
        from userbot.userbot import set_message_callback
        set_message_callback(ws_new_message_callback)
    except Exception as e:
        logger.warning(f"Could not set message callback: {e}")

    try:
        from bot_manager import set_bot_ws_broadcast_callback, sync_all_managed_bots
        set_bot_ws_broadcast_callback(ws_bot_message_callback)
        await sync_all_managed_bots()
    except Exception as e:
        logger.warning(f"Managed bots startup sync: {e}")

    yield
    # Shutdown all active running userbots
    try:
        from userbot.userbot import stop_all_running_userbots
        await stop_all_running_userbots()
    except Exception as e:
        logger.warning(f"Error stopping userbots: {e}")

    await ptb_app.stop()
    await ptb_app.shutdown()


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(lifespan=lifespan, title="Deleted Gifts Bot")


class NgrokMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["ngrok-skip-browser-warning"] = "69420"
        return response

app.add_middleware(NgrokMiddleware)


# ── Automatic Admin Error Reporting ──────────────────────────────────────────

async def notify_admin_error(
    action: str,
    error: Exception | str,
    user_info: dict | str = None,
    details: dict | str = None
):
    """Sends a clear, detailed error report directly to @xusanboyman200 (ADMIN_ID: 6588631008) via Telegram bot."""
    if not ptb_app or not ptb_app.bot:
        logger.error(f"Cannot send error notification: ptb_app not ready. Action: {action}, Error: {error}")
        return

    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        user_str = "Unknown / Guest"
        if isinstance(user_info, dict):
            username = user_info.get("username")
            uid = user_info.get("id") or user_info.get("user_id")
            first_name = user_info.get("first_name", "")
            user_str = f"{first_name} (@{username})" if username else f"{first_name} (ID: {uid})"
        elif user_info:
            user_str = str(user_info)

        err_msg = str(error)
        tb_str = ""
        if isinstance(error, Exception):
            tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            if len(tb_str) > 400:
                tb_str = tb_str[-400:]

        det_str = ""
        if isinstance(details, dict):
            det_str = json.dumps(details, indent=2, ensure_ascii=False)
        elif details:
            det_str = str(details)

        message_text = (
            f"🚨 <b>SYSTEM ERROR REPORT</b>\n\n"
            f"👤 <b>User:</b> <code>{user_str}</code>\n"
            f"🎯 <b>Action:</b> {action}\n"
            f"⏰ <b>Time:</b> {now_str}\n"
            f"⚠️ <b>Error:</b>\n<code>{err_msg}</code>\n"
        )
        if det_str:
            if len(det_str) > 300:
                det_str = det_str[:300] + "..."
            message_text += f"\n📝 <b>Details / Context:</b>\n<pre>{det_str}</pre>\n"

        if tb_str:
            message_text += f"\n🔍 <b>Traceback Snippet:</b>\n<pre>{tb_str}</pre>"

        await ptb_app.bot.send_message(
            chat_id=ADMIN_ID,
            text=message_text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to send admin error report to {ADMIN_ID}: {e}")


@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {exc}", exc_info=exc)
    
    init_data = request.headers.get("X-Init-Data") or request.query_params.get("init_data")
    user_info = verify_init_data(init_data) if init_data else None
    
    details = {
        "method": request.method,
        "path": str(request.url.path),
        "client_ip": request.client.host if request.client else "unknown",
        "query_params": dict(request.query_params)
    }
    
    asyncio.create_task(notify_admin_error(
        action=f"HTTP {request.method} {request.url.path}",
        error=exc,
        user_info=user_info,
        details=details
    ))
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Support has been notified."}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    init_data = request.headers.get("X-Init-Data") or request.query_params.get("init_data")
    user_info = verify_init_data(init_data) if init_data else None
    
    details = {
        "method": request.method,
        "path": str(request.url.path),
        "errors": exc.errors()
    }
    
    asyncio.create_task(notify_admin_error(
        action=f"Validation Error on {request.method} {request.url.path}",
        error=str(exc),
        user_info=user_info,
        details=details
    ))
    
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )


@app.websocket("/api/ws/global")
async def websocket_global_endpoint(websocket: WebSocket, init_data: str = None):
    await websocket.accept()
    await ws_manager.connect_global(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            if raw == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_manager.disconnect_global(websocket)


@app.websocket("/api/ws/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    account_id: str,
    recipient: str,
    init_data: str = None
):
    await websocket.accept()
    
    user = verify_init_data(init_data) if init_data else None

    # Resolve real account_id
    real_id = account_id
    try:
        ub_obj = await db.get_userbot_by_id_or_hash(account_id)
        if ub_obj:
            real_id = ub_obj["id"]
        else:
            try:
                real_id = int(account_id)
            except ValueError:
                real_id = 1
    except Exception:
        try:
            real_id = int(account_id)
        except ValueError:
            real_id = 1

    # Start the userbot client so it can receive messages
    try:
        from userbot.userbot import get_running_client
        await get_running_client(real_id)
    except Exception as e:
        logger.error(f"WS failed to start userbot client {account_id}: {e}")

    # Register connection for the recipient peer
    await ws_manager.connect(websocket, account_id, recipient)

    # Also try to resolve the numeric chat_id for this peer and register that too
    extra_key = None
    try:
        from userbot.userbot import get_running_client as grc2
        client = await grc2(real_id)
        if client:
            chat = await client.get_chat(recipient)
            if chat:
                extra_key = str(chat.id)
                await ws_manager.connect(websocket, account_id, extra_key)
                # Also register by username if available
                if chat.username:
                    await ws_manager.connect(websocket, account_id, chat.username)
    except Exception:
        pass

    try:
        while True:
            raw = await websocket.receive_text()
            if raw == "ping":
                await websocket.send_text("pong")
                continue

            # Handle send message through WebSocket
            try:
                payload = json.loads(raw)
                if payload.get("action") == "send" and payload.get("text"):
                    from userbot.userbot import userbot_send_message
                    result = await userbot_send_message(real_id, recipient, payload["text"])
                    await websocket.send_json({"event": "send_ack", "success": result.get("success", False), "message_id": result.get("message_id"), "error": result.get("error")})
            except json.JSONDecodeError:
                pass
            except Exception as send_err:
                logger.error(f"WS send error: {send_err}")
                await websocket.send_json({"event": "send_ack", "success": False, "error": str(send_err)})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_manager.disconnect(websocket, account_id, recipient)
        if extra_key:
            ws_manager.disconnect(websocket, account_id, extra_key)


# ── Managed Bots Admin APIs ────────────────────────────────────────────────

@app.get("/api/admin/managed-bots")
async def get_managed_bots_endpoint(request: Request):
    user = verify_request_auth(request)
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")
    bots = await db.get_all_managed_bots()
    return {"success": True, "bots": bots}

@app.post("/api/admin/managed-bots")
async def add_managed_bot_endpoint(request: Request, body: dict = Body(...)):
    user = verify_request_auth(request)
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")
    token = (body.get("token") or "").strip()
    if not token:
        return {"success": False, "error": "Bot Token is required"}

    from bot_manager import validate_bot_token, start_bot_instance
    val = await validate_bot_token(token)
    if not val.get("success"):
        return {"success": False, "error": val.get("error", "Invalid Bot Token")}

    bot = await db.add_managed_bot(
        token=token,
        bot_username=val.get("bot_username", ""),
        bot_name=val.get("bot_name", ""),
        bot_id=val.get("bot_id", 0)
    )
    if bot:
        await start_bot_instance(bot)
    return {"success": True, "bot": bot}

@app.post("/api/admin/managed-bots/{bot_id}/toggle")
async def toggle_managed_bot_endpoint(bot_id: int, request: Request, body: dict = Body(...)):
    user = verify_request_auth(request)
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")
    active = 1 if body.get("active", True) else 0
    await db.toggle_managed_bot_status(bot_id, active)
    from bot_manager import start_bot_instance, stop_bot_instance
    bot = await db.get_managed_bot_by_id(bot_id)
    if bot:
        if active:
            await start_bot_instance(bot)
        else:
            await stop_bot_instance(bot_id)
    return {"success": True, "active": active}

@app.delete("/api/admin/managed-bots/{bot_id}")
async def delete_managed_bot_endpoint(bot_id: int, request: Request):
    user = verify_request_auth(request)
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")
    from bot_manager import stop_bot_instance
    await stop_bot_instance(bot_id)
    await db.delete_managed_bot(bot_id)
    return {"success": True}

@app.post("/api/admin/managed-bots/{bot_id}/commands")
async def update_managed_bot_commands_endpoint(bot_id: int, request: Request, body: dict = Body(...)):
    user = verify_request_auth(request)
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")
    commands_json = json.dumps(body.get("commands", []))
    scripts_json = json.dumps(body.get("scripts", {}))
    await db.update_managed_bot_commands(bot_id, commands_json, scripts_json)
    return {"success": True}

@app.get("/api/admin/managed-bots/{bot_id}/contacts")
async def get_managed_bot_contacts_endpoint(bot_id: int, request: Request):
    user = verify_request_auth(request)
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")
    bot = await db.get_managed_bot_by_id(bot_id)
    if not bot:
        return {"success": False, "error": "Bot not found"}
    contacts = await db.get_bot_chat_contacts(bot["token"])
    return {"success": True, "contacts": contacts}

@app.get("/api/admin/managed-bots/{bot_id}/history/{user_id}")
async def get_managed_bot_history_endpoint(bot_id: int, user_id: int, request: Request):
    user = verify_request_auth(request)
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")
    bot = await db.get_managed_bot_by_id(bot_id)
    if not bot:
        return {"success": False, "error": "Bot not found"}
    messages = await db.get_bot_user_chat_history(bot["token"], user_id)
    return {"success": True, "messages": messages}

@app.post("/api/admin/managed-bots/{bot_id}/send")
async def send_managed_bot_message_endpoint(bot_id: int, request: Request, body: dict = Body(...)):
    user = verify_request_auth(request)
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")
    bot = await db.get_managed_bot_by_id(bot_id)
    if not bot:
        return {"success": False, "error": "Bot not found"}
    user_id = int(body.get("user_id", 0))
    text = (body.get("text") or "").strip()
    if not user_id or not text:
        return {"success": False, "error": "user_id and text required"}

    from bot_manager import send_bot_api_message
    res = await send_bot_api_message(bot["token"], user_id, text)
    if res.get("ok"):
        date_str = datetime.now().strftime("%H:%M")
        saved = await db.save_bot_user_message(
            bot["token"], user_id, body.get("user_username", ""), body.get("user_first_name", "User"),
            res["result"].get("message_id", 0), text, out=1, date_str=date_str
        )
        await ws_bot_message_callback(bot["token"], user_id, saved)
        return {"success": True, "message": saved}
    else:
        return {"success": False, "error": res.get("description", "Failed to send message")}


@app.get("/api/userbot/chat/profile")
async def get_user_profile_endpoint(account_id: str, recipient: str):
    try:
        from userbot.userbot import get_running_client
        real_id = account_id
        ub_obj = await db.get_userbot_by_id_or_hash(account_id)
        if ub_obj:
            real_id = ub_obj["id"]
        else:
            try:
                real_id = int(account_id)
            except ValueError:
                real_id = 1

        client = await get_running_client(real_id)
        chat = await client.get_chat(recipient)
        
        user_obj = None
        try:
            user_obj = await client.get_users(recipient)
        except Exception:
            pass
            
        bio = getattr(chat, "bio", "") or getattr(chat, "description", "") or "No bio available."
        phone = getattr(user_obj, "phone_number", "") or getattr(chat, "phone_number", "") or ""
        if phone and not phone.startswith("+"):
            phone = "+" + phone

        status_str = "last seen recently"
        if user_obj and hasattr(user_obj, "status"):
            st = str(user_obj.status).lower()
            if "online" in st:
                status_str = "online"
            elif "recently" in st:
                status_str = "last seen recently"
            elif "week" in st:
                status_str = "last seen within a week"
            else:
                status_str = "last seen recently"

        photo_url = None
        if chat.photo:
            try:
                photo_path = await client.download_media(chat.photo.big_file_id or chat.photo.small_file_id)
                if photo_path and os.path.exists(photo_path):
                    with open(photo_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                        photo_url = f"data:image/jpeg;base64,{b64}"
                    try: os.remove(photo_path)
                    except: pass
            except Exception:
                pass
                
        return {
            "success": True,
            "id": chat.id,
            "title": f"{chat.first_name or ''} {chat.last_name or ''}".strip() or chat.title or str(chat.id),
            "first_name": chat.first_name or "",
            "last_name": chat.last_name or "",
            "username": chat.username or "",
            "phone": phone,
            "status": status_str,
            "bio": bio,
            "photo": photo_url,
            "type": str(chat.type)
        }
    except Exception as e:
        logger.error(f"get_user_profile error: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/userbot/chat/read")
async def read_chat_history_endpoint(request: Request):
    try:
        data = await request.json()
        account_id = data.get("account_id")
        recipient = data.get("recipient")
        if not account_id or not recipient:
            return {"success": False, "error": "Missing params"}
            
        from userbot.userbot import get_running_client
        real_id = account_id
        ub_obj = await db.get_userbot_by_id_or_hash(account_id)
        if ub_obj:
            real_id = ub_obj["id"]
        else:
            try:
                real_id = int(account_id)
            except ValueError:
                real_id = 1

        client = await get_running_client(real_id)
        await client.read_chat_history(recipient)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Webhook ────────────────────────────────────────────────────────────────────
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, ptb_app.bot)
    await ptb_app.process_update(update)
    return JSONResponse({"ok": True})


# ── Public: config (no auth) ───────────────────────────────────────────────────
@app.get("/api/config")
async def get_config():
    return {"admin_id": ADMIN_ID}


# ── Public: gifts list (no auth needed to browse) ─────────────────────────────
@app.get("/api/gifts")
async def list_gifts():
    return await db.get_all_gifts(active_only=True)


@app.get("/api/gifts/{gift_id}")
async def get_gift(gift_id: int):
    gift = await db.get_gift(gift_id)
    if not gift:
        raise HTTPException(status_code=404, detail="Not found")
    return gift


# ── Recipient Verification & Userbot Accounts ──────────────────────────────────
@app.get("/api/check-user")
async def check_user(query: str):
    try:
        from userbot.userbot import verify_telegram_user
    except ImportError:
        from userbot import verify_telegram_user
    res = await verify_telegram_user(BOT_TOKEN, query)
    return res


async def get_optional_user(
    x_init_data: str = Header(None, alias="X-Init-Data"),
) -> dict:
    if x_init_data:
        return verify_init_data(x_init_data)
    return None


@app.get("/api/pricing")
async def get_public_pricing():
    return await db.get_pricing_settings()


@app.get("/api/admin/pricing")
async def admin_get_pricing(admin=Depends(get_admin)):
    return await db.get_pricing_settings()


class AdminPricingUpdatePayload(BaseModel):
    bot_stars: int = 53
    userbot_stars: int = 55
    myaccount_stars: int = 51


@app.post("/api/admin/pricing")
async def admin_update_pricing(body: AdminPricingUpdatePayload, admin=Depends(get_admin)):
    success = await db.set_pricing_settings(body.model_dump())
    return {"ok": success}


@app.get("/api/userbot-accounts")
async def get_userbot_accounts(user: dict = Depends(get_optional_user)):
    user_id = user.get("id") if user else None
    is_admin = (user_id == ADMIN_ID) if user_id else False
    
    # Load userbots directly from Database
    raw_accs = await db.async_get_userbot_accounts(active_only=True, user_tg_id=user_id, is_admin=is_admin)
        
    # Strictly sanitize public data for non-admin users & public app callers
    # (NO session_string, NO phone, NO api keys, HASHED ID for control)
    sanitized = []
    for acc in raw_accs:
        fname = acc.get("first_name", "") or ""
        lname = acc.get("last_name", "") or ""
        first_name_only = fname.strip().split(" ")[0] if fname.strip() else (lname.strip().split(" ")[0] if lname.strip() else "Userbot")
        sanitized.append({
            "id": db.hash_userbot_id(acc["id"]),
            "first_name": first_name_only,
            "username": acc.get("username", ""),
            "photo": acc.get("photo", ""),
            "active": bool(acc.get("active", True)),
            "owner_tg_id": acc.get("owner_tg_id"),
            "stars_balance": acc.get("stars_balance", 0)
        })
    return sanitized


class UserRequestCodePayload(BaseModel):
    phone: str
    force: bool = False


@app.post("/api/user/userbot/request-code")
async def user_request_phone_code(body: UserRequestCodePayload, user: dict = Depends(get_optional_user)):
    try:
        from userbot.userbot import request_userbot_phone_code
    except ImportError:
        from userbot import request_userbot_phone_code
    res = await request_userbot_phone_code(body.phone, force=body.force)
    if not res.get("success"):
        return {
            "success": False,
            "error": res.get("error", "Failed to send verification code"),
            "support_contact": "@xusanboyman200",
            "support_message": res.get("error") or "Something went wrong! Please contact support: @xusanboyman200"
        }
    return res


class UserConfirmCodePayload(BaseModel):
    phone: str
    code: str
    password: str | None = None


@app.post("/api/user/userbot/confirm-code")
async def user_confirm_phone_code(body: UserConfirmCodePayload, user: dict = Depends(get_optional_user)):
    try:
        from userbot.userbot import confirm_userbot_phone_code
    except ImportError:
        from userbot import confirm_userbot_phone_code
    owner_id = user.get("id") if user else None
    res = await confirm_userbot_phone_code(body.phone, body.code, body.password, owner_tg_id=owner_id)
    if not res.get("success"):
        return {
            "success": False,
            "requires_password": res.get("requires_password", False),
            "error": res.get("error", "Failed to confirm code"),
            "support_contact": "@xusanboyman200",
            "support_message": res.get("error") or "Something went wrong! Please contact support: @xusanboyman200"
        }
    return res


@app.delete("/api/user/userbot/account/{account_id}")
async def user_delete_account(account_id: int, user: dict = Depends(get_optional_user)):
    try:
        from userbot.userbot import delete_userbot_account
    except ImportError:
        from userbot import delete_userbot_account
    user_id = user.get("id") if user else None
    is_admin = user_id == ADMIN_ID
    success = delete_userbot_account(account_id, owner_tg_id=None if is_admin else user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Account not found or access denied")
    return {"ok": True}


# ── Authenticated: create invoice ──────────────────────────────────────────────
class CreateInvoiceRequest(BaseModel):
    recipient_id: str
    gift_id: int
    gift_text: str = None
    sender_type: str = "bot"
    userbot_id: Any = None


@app.post("/api/invoice")
async def create_invoice(body: CreateInvoiceRequest, user: dict = Depends(get_user)):
    user_id = user["id"]
    now = time.time()
    last = user_last_invoice_time.get(user_id, 0)
    if now - last < 2.0:
        raise HTTPException(status_code=429, detail="Too many request attempts. Please wait 2 seconds.")
    user_last_invoice_time[user_id] = now

    gift = await db.get_gift(body.gift_id)
    if not gift or not gift["active"]:
        raise HTTPException(status_code=404, detail="Gift not available")

    pricing = await db.get_pricing_settings()
    if body.sender_type == "myaccount":
        total = pricing.get("myaccount_stars", 51)
        # Verify user has connected account with at least 50 stars
        raw_accs = await db.async_get_userbot_accounts(active_only=True, user_tg_id=user_id, is_admin=False)
        user_acc = next((a for a in raw_accs if a.get("owner_tg_id") == user_id), None)
        if not user_acc:
            raise HTTPException(status_code=400, detail="Please connect your Telegram account first to use 'My Account' sender option.")
        stars = user_acc.get("stars_balance", 0)
        if stars > 0 and stars < 50:
            raise HTTPException(status_code=400, detail=f"Your connected account has only {stars} ⭐ Telegram Stars. Minimum 50 ⭐ Stars balance required to purchase gifts (+ 1 ⭐ bot fee).")
    elif body.sender_type == "userbot":
        total = pricing.get("userbot_stars", 55)
    else:
        total = pricing.get("bot_stars", gift["base_stars"] + gift["commission"])

    target_ub_id = None
    if body.userbot_id:
        ub_obj = await db.get_userbot_by_id_or_hash(body.userbot_id)
        if ub_obj:
            target_ub_id = ub_obj.get("id")

    name = gift.get("display_name") or gift["emoji"]
    order_id = await db.create_order(
        buyer_tg_id=user["id"],
        buyer_username=user.get("username", ""),
        recipient_id=body.recipient_id,
        recipient_type="username",
        gift_id=body.gift_id,
        total_stars=total,
        gift_text=body.gift_text,
        sender_type=body.sender_type or "bot",
        userbot_id=target_ub_id
    )
    try:
        desc = f"Rare deleted Telegram gift → {body.recipient_id}"
        if body.gift_text:
            desc += f" (Message: {body.gift_text})"
        link = await ptb_app.bot.create_invoice_link(
            title=f"🎁 {name}",
            description=desc,
            payload=f"order_{order_id}",
            currency="XTR",
            prices=[LabeledPrice(label=name, amount=total)],
        )
        return {"link": link, "order_id": order_id}
    except Exception as e:
        logger.error(f"create_invoice_link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Authenticated: user's own order history ────────────────────────────────────
@app.get("/api/my-orders")
async def my_orders(user: dict = Depends(get_user)):
    return await db.get_orders_by_user(user["id"])


# ── Admin API ──────────────────────────────────────────────────────────────────
@app.get("/api/admin/gifts")
async def admin_list_gifts(admin=Depends(get_admin)):
    return await db.get_all_gifts(active_only=False)


class GiftPayload(BaseModel):
    emoji: str = "🧸"
    date_label: str
    gift_tg_id: str
    base_stars: int = 50
    commission: int = 10
    display_name: str = ""
    animation: str = ""


@app.post("/api/admin/gifts")
async def admin_add_gift(body: GiftPayload, admin=Depends(get_admin)):
    emoji_val = body.emoji if body.emoji else "🧸"
    gid = await db.add_gift(
        emoji_val, body.date_label, body.gift_tg_id,
        body.base_stars, body.commission, body.animation or None
    )
    if body.display_name:
        await db.update_gift(gid, display_name=body.display_name)
    return {"id": gid}


class GiftUpdate(BaseModel):
    emoji: str = None
    date_label: str = None
    gift_tg_id: str = None
    base_stars: int = None
    commission: int = None
    active: int = None
    display_name: str = None
    animation: str = None


@app.patch("/api/admin/gifts/{gift_id}")
async def admin_update_gift(gift_id: int, body: GiftUpdate, admin=Depends(get_admin)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    await db.update_gift(gift_id, **fields)
    return {"ok": True}


@app.delete("/api/admin/gifts/{gift_id}")
async def admin_delete_gift(gift_id: int, admin=Depends(get_admin)):
    await db.hard_delete_gift(gift_id)
    return {"ok": True}


@app.post("/api/admin/upload-animation")
async def admin_upload_animation(file: UploadFile = File(...), admin=Depends(get_admin)):
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are allowed")
    filename = os.path.basename(file.filename)
    assets_dir = os.path.join(ROOT, "frontend", "assets")
    os.makedirs(assets_dir, exist_ok=True)
    file_path = os.path.join(assets_dir, filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return {"ok": True, "filename": filename}


@app.get("/api/admin/orders")
async def admin_orders(admin=Depends(get_admin)):
    return await db.get_all_orders()


@app.get("/api/admin/users")
async def admin_users(admin=Depends(get_admin)):
    return await db.get_all_users()


class BroadcastRequest(BaseModel):
    message: str


@app.post("/api/admin/bot/restart")
async def restart_bot_endpoint(admin=Depends(get_admin)):
    global ptb_app
    try:
        await ptb_app.stop()
        await ptb_app.shutdown()
        await ptb_app.initialize()
        await ptb_app.start()
        return {"success": True, "message": "Bot restarted successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/admin/bot/sync-webhook")
async def sync_webhook_endpoint(admin=Depends(get_admin)):
    global ptb_app
    try:
        from config import BASE_URL
    except ImportError:
        from backend.config import BASE_URL
    if not BASE_URL:
        return {"success": False, "error": "BASE_URL is not set"}
    webhook_url = f"{BASE_URL}/webhook"
    try:
        await ptb_app.bot.set_webhook(webhook_url, drop_pending_updates=True)
        return {"success": True, "message": f"Webhook updated to {webhook_url}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/admin/bot/broadcast")
async def broadcast_endpoint(body: BroadcastRequest, admin=Depends(get_admin)):
    global ptb_app
    users = await db.get_all_users()
    sent_count = 0
    failed_count = 0
    for u in users:
        buyer_id = u["buyer_tg_id"]
        try:
            await ptb_app.bot.send_message(chat_id=buyer_id, text=body.message)
            sent_count += 1
        except Exception as e:
            logger.warning(f"Failed to send broadcast to {buyer_id}: {e}")
            failed_count += 1
    return {"success": True, "sent": sent_count, "failed": failed_count}


class SetCommandsRequest(BaseModel):
    commands: list


@app.get("/api/admin/bot/commands")
async def get_bot_commands(admin=Depends(get_admin)):
    global ptb_app
    try:
        cmds = await ptb_app.bot.get_my_commands()
        return {"success": True, "commands": [{"command": c.command, "description": c.description} for c in cmds]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/admin/bot/commands")
async def set_bot_commands_endpoint(body: SetCommandsRequest, admin=Depends(get_admin)):
    global ptb_app
    try:
        from telegram import BotCommand
        t_cmds = []
        for c in body.commands:
            cmd = c.get("command", "").strip().lower().lstrip("/")
            desc = c.get("description", "").strip()
            if cmd and desc:
                t_cmds.append(BotCommand(cmd, desc))
        await ptb_app.bot.set_my_commands(t_cmds)
        return {"success": True, "message": "Bot commands updated successfully on Telegram!"}
    except Exception as e:
        return {"success": False, "error": str(e)}




# ── Admin Userbot Management ──────────────────────────────────────────────────
@app.get("/api/admin/userbots")
async def admin_get_userbots(admin=Depends(get_admin)):
    try:
        from userbot.userbot import get_all_userbot_accounts
    except ImportError:
        from userbot import get_all_userbot_accounts
    return get_all_userbot_accounts()


class UserbotCreate(BaseModel):
    phone: str = ""
    session_string: str = ""
    api_id: int = 0
    api_hash: str = ""
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    bio: str = ""
    photo: str = ""
    active: bool = True


@app.post("/api/admin/userbots")
async def admin_create_userbot(body: UserbotCreate, background_tasks: BackgroundTasks, admin=Depends(get_admin)):
    try:
        from userbot.userbot import create_userbot_account, sync_userbot_telegram_profile
    except ImportError:
        from userbot import create_userbot_account, sync_userbot_telegram_profile
    new_acc = create_userbot_account(body.model_dump())
    if new_acc.get("session_string"):
        background_tasks.add_task(sync_userbot_telegram_profile, new_acc)
    return new_acc


class UserbotUpdate(BaseModel):
    first_name: str = None
    last_name: str = None
    username: str = None
    bio: str = None
    photo: str = None
    active: bool = None
    phone: str = None
    session_string: str = None
    api_id: int = None
    api_hash: str = None


@app.patch("/api/admin/userbots/{account_id}")
async def admin_update_userbot(account_id: int, body: UserbotUpdate, background_tasks: BackgroundTasks, admin=Depends(get_admin)):
    try:
        from userbot.userbot import update_userbot_account, get_userbot_by_id, sync_userbot_telegram_profile
    except ImportError:
        from userbot import update_userbot_account, get_userbot_by_id, sync_userbot_telegram_profile
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    success = update_userbot_account(account_id, **fields)
    if not success:
        raise HTTPException(status_code=404, detail="Userbot account not found")
    if "active" in fields:
        await db.set_userbot_active_status(account_id, bool(fields["active"]))
    acc = get_userbot_by_id(account_id)
    if acc and acc.get("session_string"):
        background_tasks.add_task(sync_userbot_telegram_profile, acc)
    return {"ok": True}


@app.post("/api/admin/userbots/{account_id}/toggle-active")
@app.patch("/api/admin/userbots/{account_id}/toggle-active")
async def admin_toggle_userbot_active(account_id: int, admin=Depends(get_admin)):
    try:
        from userbot.userbot import get_userbot_by_id, update_userbot_account
    except ImportError:
        from userbot import get_userbot_by_id, update_userbot_account

    acc = get_userbot_by_id(account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Userbot account not found")

    current_active = bool(acc.get("active", True))
    new_active = not current_active
    success = update_userbot_account(account_id, active=new_active)
    await db.set_userbot_active_status(account_id, new_active)

    status_str = "re-enabled (undone)" if new_active else "disabled"
    return {
        "ok": True,
        "account_id": account_id,
        "active": new_active,
        "message": f"Userbot #{account_id} has been {status_str} by admin."
    }


class UserbotSendMessageRequest(BaseModel):
    account_id: int | str
    recipient: str
    message: str


@app.post("/api/userbot/chat/send")
@app.post("/api/admin/userbot/send-message")
async def userbot_send_message_endpoint(body: UserbotSendMessageRequest):
    try:
        from userbot.userbot import userbot_send_message
    except ImportError:
        from userbot import userbot_send_message
    
    # Resolve account_id if hashed string or int
    account_id = body.account_id
    if isinstance(account_id, str):
        ub_obj = await db.get_userbot_by_id_or_hash(account_id)
        if ub_obj:
            account_id = ub_obj["id"]
        else:
            try:
                account_id = int(account_id)
            except ValueError:
                account_id = 1

    res = await userbot_send_message(account_id, body.recipient, body.message)
    if not res.get("success"):
        return {"success": False, "error": res.get("error", "Failed to send message via userbot")}
    return res


@app.get("/api/userbot/chat/history")
async def userbot_chat_history_endpoint(account_id: str, recipient: str):
    try:
        from userbot.userbot import get_userbot_chat_history
    except ImportError:
        from userbot import get_userbot_chat_history

    real_id = account_id
    ub_obj = await db.get_userbot_by_id_or_hash(account_id)
    if ub_obj:
        real_id = ub_obj["id"]
    else:
        try:
            real_id = int(account_id)
        except ValueError:
            real_id = 1

    history = await get_userbot_chat_history(real_id, recipient)
    return {"success": True, "messages": history}


@app.get("/api/userbot/chat/contacts")
async def userbot_chat_contacts_endpoint(account_id: str, limit: int = 30):
    try:
        from userbot.userbot import get_userbot_contacts
    except ImportError:
        from userbot import get_userbot_contacts

    real_id = account_id
    ub_obj = await db.get_userbot_by_id_or_hash(account_id)
    if ub_obj:
        real_id = ub_obj["id"]
    else:
        try:
            real_id = int(account_id)
        except ValueError:
            real_id = 1

    contacts = await get_userbot_contacts(real_id, limit=limit)
    return {"success": True, "contacts": contacts}


class ChatSendRequest(BaseModel):
    account_id: str
    recipient: str
    message: str

@app.post("/api/userbot/chat/send")
async def userbot_chat_send_endpoint(req: ChatSendRequest):
    try:
        from userbot.userbot import userbot_send_message
    except ImportError:
        from userbot import userbot_send_message

    real_id = req.account_id
    ub_obj = await db.get_userbot_by_id_or_hash(req.account_id)
    if ub_obj:
        real_id = ub_obj["id"]
    else:
        try:
            real_id = int(req.account_id)
        except ValueError:
            real_id = 1

    result = await userbot_send_message(real_id, req.recipient, req.message)
    return result


class RequestPhoneCodeRequest(BaseModel):
    phone: str
    api_id: int = None
    api_hash: str = None


@app.post("/api/admin/userbot/request-code")
async def admin_request_phone_code(body: RequestPhoneCodeRequest, admin=Depends(get_admin)):
    try:
        from userbot.userbot import request_userbot_phone_code
    except ImportError:
        from userbot import request_userbot_phone_code
    res = await request_userbot_phone_code(body.phone, body.api_id, body.api_hash)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to send verification code"))
    return res


class ConfirmPhoneCodeRequest(BaseModel):
    phone: str
    code: str
    password: str = None


@app.post("/api/admin/userbot/confirm-code")
async def admin_confirm_phone_code(body: ConfirmPhoneCodeRequest, admin=Depends(get_admin)):
    try:
        from userbot.userbot import confirm_userbot_phone_code
    except ImportError:
        from userbot import confirm_userbot_phone_code
    res = await confirm_userbot_phone_code(body.phone, body.code, body.password)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to confirm code"))
    return res


# ── Static files ───────────────────────────────────────────────────────────────
import os
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
