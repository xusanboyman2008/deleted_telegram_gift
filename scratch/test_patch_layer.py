import asyncio
import logging
import sys
import os
import psycopg2
from io import BytesIO

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set up logging to stdout
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Monkeypatch hydrogram layer to 223
import hydrogram.session.session
hydrogram.session.session.layer = 223
print("MONKEYPATCHED hydrogram.session.session.layer to:", hydrogram.session.session.layer)

from hydrogram.raw.core import TLObject
from hydrogram.raw.core.primitives import Int, Long, String
from hydrogram.raw.functions import InvokeWithLayer
from hydrogram.raw.types import TextWithEntities
from hydrogram import Client
from userbot.userbot import InputInvoiceStarGift

class GetPaymentFormLayer223(TLObject):
    ID = 0x376c8c36
    QUALNAME = "functions.payments.GetPaymentForm"

    def __init__(self, *, invoice: TLObject, theme_params: TLObject = None):
        self.invoice = invoice
        self.theme_params = theme_params

    @staticmethod
    def read(b: BytesIO, *args) -> "GetPaymentFormLayer223":
        return TLObject.read(b)

    def write(self, *args) -> bytes:
        b = BytesIO()
        b.write(Int(self.ID, False))
        flags = 0
        if self.theme_params is not None:
            flags |= (1 << 0)
        b.write(Int(flags))
        b.write(self.invoice.write())
        if self.theme_params is not None:
            b.write(self.theme_params.write())
        return b.getvalue()

class SendStarsFormLayer223(TLObject):
    ID = 0x7998c914
    QUALNAME = "functions.payments.SendStarsForm"

    def __init__(self, *, form_id: int, invoice: TLObject):
        self.form_id = form_id
        self.invoice = invoice

    @staticmethod
    def read(b: BytesIO, *args) -> "SendStarsFormLayer223":
        return TLObject.read(b)

    def write(self, *args) -> bytes:
        b = BytesIO()
        b.write(Int(self.ID, False))
        b.write(Long(self.form_id))
        b.write(self.invoice.write())
        return b.getvalue()

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
    
    # 2. Stop running userbots for 6 if any are active
    from userbot.userbot import _RUNNING_USERBOTS
    if 6 in _RUNNING_USERBOTS:
        try:
            print("Stopping running userbot 6...")
            await _RUNNING_USERBOTS[6].stop()
            del _RUNNING_USERBOTS[6]
        except Exception as e:
            print("Stop failed:", e)
            
    # 3. Create client
    client = Client(
        "patched_client_6",
        api_id=api_id,
        api_hash=api_hash,
        session_string=session_string,
        in_memory=True
    )
    
    await client.start()
    print("Client started with layer:", client.session.layer if hasattr(client, "session") else "unknown")
    
    try:
        # Resolve recipient peer @suats
        peer = await client.resolve_peer("@suats")
        print(f"Resolved peer: {peer}")
        
        # Construct invoice (Football Bear, ID 6026193266406327981)
        invoice = InputInvoiceStarGift(peer=peer, gift_id=6026193266406327981, message=None, hide_name=False)
        
        print("4. Requesting payment form...")
        query = GetPaymentFormLayer223(invoice=invoice)
        form_res = await client.invoke(query)
        print("SUCCESS! Form response:", form_res)
        
        form_id = getattr(form_res, "form_id", getattr(form_res, "id", None))
        print(f"Form ID obtained: {form_id}")
        
        if form_id:
            print("5. Finalizing payment...")
            pay_query = SendStarsFormLayer223(form_id=form_id, invoice=invoice)
            pay_res = await client.invoke(pay_query)
            print("SUCCESS PAYMENT:", pay_res)
        else:
            print("No Form ID found in response.")
            
    except Exception as e:
        import traceback
        print("FAILED:", e)
        traceback.print_exc()
    finally:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(test())
