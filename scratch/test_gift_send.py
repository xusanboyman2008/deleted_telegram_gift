import asyncio
import logging
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set up logging to stdout
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

async def test():
    try:
        from userbot.userbot import attempt_send_gift_via_userbot
    except ImportError:
        from userbot import attempt_send_gift_via_userbot
        
    # We will attempt to send gift 5 (Football Bear, ID 6026193266406327981) via userbot account 6 to @suats
    # We use recipient '@suats' and gift_tg_id '5' (which maps to 6026193266406327981 in real_gift_map or passes it through)
    # Wait, real_gift_map has:
    # 5: 5866352046986232958 (Bunny Basket)
    # Wait, let's check the map in userbot.py:
    # 5: 5866352046986232958
    # 6: 5893356958802511476
    # 7: 5935895822435615975
    # 8: 5969796561943660080
    # 9: 6026193266406327981 (Football Bear)
    # 10: 5974210632977745012
    # So gift_tg_id in DB is probably '5'. Let's check how attempt_send_gift_via_userbot maps gift_id.
    
    print("Testing attempt_send_gift_via_userbot...")
    res = await attempt_send_gift_via_userbot(
        account_id=6,
        recipient_id="@suats",
        gift_tg_id="5",
        gift_text="this is a test gift send from script"
    )
    print("RESULT:", res)

if __name__ == "__main__":
    asyncio.run(test())
