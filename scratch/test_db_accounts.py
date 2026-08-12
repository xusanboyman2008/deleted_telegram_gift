import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import init_db, async_get_userbot_accounts
from userbot.userbot import get_running_client, get_userbot_stars_balance

async def main():
    await init_db()
    accounts = await async_get_userbot_accounts(active_only=False, is_admin=True)
    print("--- Userbot Accounts in Database ---")
    for acc in accounts:
        acc_id = acc.get('id')
        db_stars = acc.get('stars_balance')
        phone = acc.get('phone')
        username = acc.get('username')
        owner = acc.get('owner_tg_id')
        client = await get_running_client(acc_id)
        if client:
            live_stars = await get_userbot_stars_balance(client)
        else:
            live_stars = "Client failed to start"
        print(f"ID: {acc_id} | Username: @{username} | DB Stars: {db_stars} | Live Stars: {live_stars} | Owner: {owner}")

if __name__ == "__main__":
    asyncio.run(main())
