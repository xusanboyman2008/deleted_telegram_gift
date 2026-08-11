import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from userbot.userbot import get_userbot_stars_balance, get_running_client

async def main():
    print("Testing get_userbot_stars_balance for account 6:")
    try:
        client = await get_running_client(6)
        if not client:
            print("Failed to get running client.")
            return
        bal = await get_userbot_stars_balance(client)
        print(f"Stars balance returned: {bal}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
