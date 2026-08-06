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
from contextlib import asynccontextmanager
from urllib.parse import parse_qsl

user_last_invoice_time = {}

from fastapi import FastAPI, Request, HTTPException, Depends, Header
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
    web_url = f"{BASE_URL}/index.html?ngrok-skip-browser-warning=69420"
    keyboard = [
        [InlineKeyboardButton("🚀 Launch Mini App", web_app=WebAppInfo(url=web_url))],
        [
            InlineKeyboardButton("⚡ Buy in Bot", callback_data="bot_choose_gift"),
            InlineKeyboardButton("👤 Buy via Real User", url="https://t.me/xusanboyman200")
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
        row.append(InlineKeyboardButton(f"{g['emoji']} {name} ({price}⭐)", callback_data=f"gift_{g['id']}"))
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
        await update.message.reply_text(
            f"✅ Payment received! Sending {gift['emoji']} gift to <b>{order['recipient_id']}</b>…\n\n"
            "Your gift will be delivered shortly!",
            parse_mode="HTML",
        )
        if ADMIN_ID:
            await context.bot.send_message(
                ADMIN_ID,
                f"🔔 New Order #{order_id}\n"
                f"Buyer: @{order.get('buyer_username') or order['buyer_tg_id']}\n"
                f"Gift: {gift.get('display_name') or gift['emoji']} ({gift['date_label']})\n"
                f"Recipient: {order['recipient_id']}\n"
                f"Stars: {order['total_stars']} ⭐\n"
                f"Charge: {charge_id}",
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
        
    await update.message.reply_text(msg, parse_mode="HTML")


import re


async def user_message_or_admin_reply_handler(update: Update, context):
    msg = update.message
    if not msg or not msg.text:
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


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global ptb_app
    await db.init_db()
    ptb_app = Application.builder().token(BOT_TOKEN).updater(None).build()
    ptb_app.add_handler(CommandHandler("start", start_handler))
    ptb_app.add_handler(CommandHandler("gifts", start_handler))
    ptb_app.add_handler(CommandHandler("menu", start_handler))
    ptb_app.add_handler(CommandHandler("admin", admin_command_handler))
    ptb_app.add_handler(CommandHandler("stats", admin_command_handler))
    ptb_app.add_handler(CallbackQueryHandler(callback_handler))
    ptb_app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    ptb_app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
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

    yield
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


# ── Authenticated: create invoice ──────────────────────────────────────────────
class CreateInvoiceRequest(BaseModel):
    recipient_id: str
    gift_id: int


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

    total = gift["base_stars"] + gift["commission"]
    name = gift.get("display_name") or gift["emoji"]
    order_id = await db.create_order(
        buyer_tg_id=user["id"],
        buyer_username=user.get("username", ""),
        recipient_id=body.recipient_id,
        recipient_type="username",
        gift_id=body.gift_id,
        total_stars=total,
    )
    try:
        link = await ptb_app.bot.create_invoice_link(
            title=f"🎁 {name}",
            description=f"Rare deleted Telegram gift → {body.recipient_id}",
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
    emoji: str
    date_label: str
    gift_tg_id: str
    base_stars: int = 50
    commission: int = 10
    display_name: str = ""
    animation: str = ""


@app.post("/api/admin/gifts")
async def admin_add_gift(body: GiftPayload, admin=Depends(get_admin)):
    gid = await db.add_gift(
        body.emoji, body.date_label, body.gift_tg_id,
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
    await db.delete_gift(gift_id)
    return {"ok": True}


@app.get("/api/admin/orders")
async def admin_orders(admin=Depends(get_admin)):
    return await db.get_all_orders()


# ── Static files ───────────────────────────────────────────────────────────────
import os
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
