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
from hydrogram.raw.types import TextWithEntities, InputUser
from hydrogram.parser.html import HTML
from userbot.userbot import get_running_client

class SendStarGift(TLObject):
    ID = 0x6574cf97
    QUALNAME = "functions.payments.SendStarGift"

    def __init__(self, *, user_id, gift_id: int, message: TextWithEntities = None, hide_name: bool = False):
        self.user_id = user_id
        self.gift_id = gift_id
        self.message = message
        self.hide_name = hide_name

    @staticmethod
    def read(b: BytesIO, *args) -> "SendStarGift":
        return TLObject.read(b)

    def write(self, *args) -> bytes:
        b = BytesIO()
        b.write(Int(self.ID, False))
        flags = 0
        if self.hide_name:
            flags |= (1 << 0)
        if self.message and getattr(self.message, 'text', None):
            flags |= (1 << 1)
        b.write(Int(flags))
        b.write(self.user_id.write())
        b.write(Long(self.gift_id))
        if self.message and getattr(self.message, 'text', None):
            if not isinstance(getattr(self.message, 'entities', None), list):
                self.message.entities = []
            b.write(self.message.write())
        return b.getvalue()

async def test():
    client = await get_running_client(6)
    
    # Resolve recipient peer @suats
    peer = await client.resolve_peer("@suats")
    input_user = InputUser(user_id=peer.user_id, access_hash=peer.access_hash)
    print(f"Resolved input user: {input_user}")
    
    # Try sending with message
    try:
        print("Testing SendStarGift with message Hello...")
        msg = TextWithEntities(text="Hello", entities=[])
        cmd = SendStarGift(user_id=input_user, gift_id=6026193266406327981, message=msg, hide_name=False)
        res = await client.invoke(cmd)
        print("SUCCESS with message:", res)
    except Exception as e:
        print("FAILED with message:", e)
        
    # Try sending without message
    try:
        print("Testing SendStarGift without message...")
        cmd = SendStarGift(user_id=input_user, gift_id=6026193266406327981, message=None, hide_name=False)
        res = await client.invoke(cmd)
        print("SUCCESS without message:", res)
    except Exception as e:
        print("FAILED without message:", e)

if __name__ == "__main__":
    asyncio.run(test())
