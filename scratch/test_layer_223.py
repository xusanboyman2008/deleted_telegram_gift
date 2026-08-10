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
from hydrogram.raw.functions import InvokeWithLayer
from hydrogram.raw.types import TextWithEntities
from userbot.userbot import get_running_client, InputInvoiceStarGift

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
    client = await get_running_client(6)
    
    # Resolve recipient peer @suats
    peer = await client.resolve_peer("@suats")
    print(f"Resolved peer: {peer}")
    
    # Construct invoice (Football Bear, ID 6026193266406327981)
    invoice = InputInvoiceStarGift(peer=peer, gift_id=6026193266406327981, message=None, hide_name=False)
    
    try:
        print("1. Requesting payment form using Layer 223...")
        query = GetPaymentFormLayer223(invoice=invoice)
        wrapped_query = InvokeWithLayer(layer=223, query=query)
        form_res = await client.invoke(wrapped_query)
        print("SUCCESS! Form response:", form_res)
        
        form_id = getattr(form_res, "form_id", getattr(form_res, "id", None))
        print(f"Form ID obtained: {form_id}")
        
        if form_id:
            print("2. Finalizing payment using SendStarsForm Layer 223...")
            pay_query = SendStarsFormLayer223(form_id=form_id, invoice=invoice)
            pay_wrapped = InvokeWithLayer(layer=223, query=pay_query)
            pay_res = await client.invoke(pay_wrapped)
            print("SUCCESS PAYMENT:", pay_res)
        else:
            print("No Form ID found in response.")
            
    except Exception as e:
        import traceback
        print("FAILED:", e)
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
