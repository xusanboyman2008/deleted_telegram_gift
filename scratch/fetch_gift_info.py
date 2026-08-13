import asyncio
import logging
import sys
import os
import psycopg2
import struct
import base64
import ipaddress

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.payments import GetStarGiftsRequest, GetUniqueStarGiftRequest, GetResaleStarGiftsRequest

def hydrogram_to_telethon(hydrogram_session_string: str) -> str:
    padding = '=' * (4 - (len(hydrogram_session_string) % 4))
    decoded = base64.urlsafe_b64decode(hydrogram_session_string + padding)
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
    port = 443
    
    ip_bytes = ipaddress.ip_address(ip_str).packed
    ip_len = len(ip_bytes)
    
    telethon_packed = struct.pack(f'>B{ip_len}sH256s', dc_id, ip_bytes, port, auth_key_bytes)
    return '1' + base64.urlsafe_b64encode(telethon_packed).decode('ascii')

async def main():
    conn = psycopg2.connect("postgresql://telegram_gift_user:uBhyBgNcCvvUBBp8hdnFtcB3SpkLxdgZ@dpg-d9q5nc6gekts73chn830-a.frankfurt-postgres.render.com/telegram_gift")
    cur = conn.cursor()
    cur.execute("SELECT id, phone, session_string, api_id, api_hash FROM userbot_accounts WHERE session_string IS NOT NULL")
    accounts = cur.fetchall()
    cur.close()
    conn.close()
    
    client = None
    for acc in accounts:
        acc_id, phone, session_string, api_id, api_hash = acc
        api_id = api_id or 35251724
        api_hash = api_hash or "b11e753959873b1df047454a8d816604"
        
        try:
            if session_string.startswith("1"):
                telethon_session = session_string
            else:
                telethon_session = hydrogram_to_telethon(session_string)
                
            c = TelegramClient(StringSession(telethon_session), api_id, api_hash)
            await c.connect()
            if await c.is_user_authorized():
                client = c
                print(f"Using account {acc_id}")
                break
            else:
                await c.disconnect()
        except Exception:
            pass

    if not client:
        print("No connected client")
        return

    target_id = 6046499901846586791
    try:
        res = await client(GetStarGiftsRequest(hash=0))
        gifts = getattr(res, "gifts", [])
        
        print("--- SEARCHING STANDARD GIFTS ---")
        found = False
        for g in gifts:
            g_id = getattr(g, "id", None)
            if g_id == target_id:
                found = True
                print("FOUND EXACT MATCH IN GetStarGiftsRequest!")
                print(f"ID: {g.id}")
                print(f"Stars: {getattr(g, 'stars', None)}")
                print(f"Convert Stars: {getattr(g, 'convert_stars', None)}")
                print(f"Limited: {getattr(g, 'limited', False)}")
                print(f"Sold Out: {getattr(g, 'sold_out', False)}")
                print(f"Availability Remains: {getattr(g, 'availability_remains', None)} / {getattr(g, 'availability_total', None)}")
                print(f"Full details: {g}")
                break
        
        if not found:
            print(f"ID {target_id} not in standard gifts list. Total gifts checked: {len(gifts)}")
            print("Summary of all standard gifts in Telegram:")
            for g in gifts:
                emoji = ""
                if hasattr(g, 'sticker') and hasattr(g.sticker, 'attributes'):
                    for attr in g.sticker.attributes:
                        if hasattr(attr, 'alt'):
                            emoji = attr.alt
                print(f"Gift ID: {g.id} | Emoji: {emoji} | Stars: {g.stars} | SoldOut: {getattr(g, 'sold_out', False)} | Total: {getattr(g, 'availability_total', 'Unlimited')}")

    except Exception as e:
        print(f"Error querying Telethon: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
