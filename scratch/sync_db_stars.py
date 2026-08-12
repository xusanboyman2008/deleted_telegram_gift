import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import init_db, async_get_userbot_accounts
from userbot.userbot import get_running_client, get_userbot_stars_balance, update_userbot_account

async def main():
    await init_db()
    accounts = await async_get_userbot_accounts(active_only=False, is_admin=True)
    print("Syncing stars for userbot accounts...")
    for acc in accounts:
        acc_id = acc.get('id')
        client = await get_running_client(acc_id)
        if client:
            stars = await get_userbot_stars_balance(client)
            await update_userbot_account(acc_id, stars_balance=stars)
            print(f"Account {acc_id} (@{acc.get('username')}) updated to {stars} ⭐ Stars")
        else:
            await update_userbot_account(acc_id, stars_balance=0)
            print(f"Account {acc_id} (@{acc.get('username')}) updated to 0 ⭐ Stars (client unavailable)")

if __name__ == "__main__":
    asyncio.run(main())
