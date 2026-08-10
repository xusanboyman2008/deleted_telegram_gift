import asyncio
import logging
import sys
import os
import psycopg2
import struct
import base64
import ipaddress
from io import BytesIO

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set up logging to stdout
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.payments import GetPaymentFormRequest, SendStarsFormRequest, GetStarsStatusRequest
from telethon.tl.types import InputInvoiceStarGift, TextWithEntities

def hydrogram_to_telethon(hydrogram_session_string: str) -> str:
    padding = '=' * (4 - (len(hydrogram_session_string) % 4))
    decoded = base64.urlsafe_b64decode(hydrogram_session_string + padding)
    unpacked = struct.unpack('>BI?256sQ?', decoded)
    dc_id = unpacked[0]
    auth_key_bytes = unpacked[3]
    
    # Hardcoded IP for Telegram DCs (DC 2 is the standard for most European/CIS accounts)
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

async def test():
    # 1. Fetch credentials of account 6 from DB
    conn = psycopg2.connect("postgresql://telegram_gift_user:uBhyBgNcCvvUBBp8hdnFtcB3SpkLxdgZ@dpg-d9q5nc6gekts73chn830-a.frankfurt-postgres.render.com/telegram_gift")
    cur = conn.cursor()
    cur.execute("SELECT session_string, api_id, api_hash FROM userbot_accounts WHERE id = 6")
    session_string, api_id, api_hash = cur.fetchone()
    cur.close()
    conn.close()
    
    api_id = api_id or 35251724
    api_hash = api_hash or "b11e753959873b1df047454a8d816604"
    
    # Convert session to Telethon format
    telethon_session = hydrogram_to_telethon(session_string)
    print("Converted to Telethon Session String successfully.")
    
    # Initialize Telethon Client
    client = TelegramClient(StringSession(telethon_session), api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("Error: Client is not authorized with this session string!")
        await client.disconnect()
        return
        
    print("Telethon Client authorized and connected successfully!")
    
    try:
        # Check stars balance
        status = await client(GetStarsStatusRequest(peer="me"))
        print("Stars Status balance:", getattr(status, "balance", "N/A"))
        
        # Resolve recipient peer @suats
        peer = await client.get_input_entity("@suats")
        print(f"Resolved recipient input entity: {peer}")
        
        # Construct invoice (Football Bear, ID 6026193266406327981)
        invoice = InputInvoiceStarGift(peer=peer, gift_id=6026193266406327981, message=None, hide_name=False)
        
        print("1. Requesting payment form via Telethon (Layer 224)...")
        form_res = await client(GetPaymentFormRequest(invoice=invoice))
        print("SUCCESS! Form response:", form_res)
        
        form_id = getattr(form_res, "form_id", getattr(form_res, "id", None))
        print(f"Form ID obtained: {form_id}")
        
        if form_id:
            print("2. Finalizing payment via Telethon...")
            pay_res = await client(SendStarsFormRequest(form_id=form_id, invoice=invoice))
            print("SUCCESS PAYMENT:", pay_res)
        else:
            print("No Form ID found in response.")
            
    except Exception as e:
        import traceback
        print("FAILED:", e)
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test())
