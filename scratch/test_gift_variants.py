import asyncio
import logging
import sys
import os
from io import BytesIO

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set up logging to stdout
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

from hydrogram.raw.core import TLObject
from hydrogram.raw.core.primitives import Int, Long, String
from hydrogram.raw.functions.payments import GetPaymentForm
from hydrogram.raw.types import TextWithEntities
from userbot.userbot import get_running_client, InputInvoiceStarGift

async def test():
    client = await get_running_client(6)
    
    # Resolve recipient peer @suats
    peer = await client.resolve_peer("@suats")
    print(f"Resolved peer: {peer}")
    
    # Gift ID for Football Bear: 6026193266406327981
    gift_id = 6026193266406327981
    
    variants = [
        ("None message", None),
        ("TextWithEntities empty text", TextWithEntities(text="", entities=[])),
        ("TextWithEntities plain text", TextWithEntities(text="Hello", entities=[])),
    ]
    
    for name, msg in variants:
        try:
            print(f"\n--- Testing with {name} ---")
            invoice = InputInvoiceStarGift(peer=peer, gift_id=gift_id, message=msg, hide_name=False)
            res = await client.invoke(GetPaymentForm(invoice=invoice))
            print("SUCCESS:", res)
        except Exception as e:
            print("FAILED:", e)

if __name__ == "__main__":
    asyncio.run(test())
