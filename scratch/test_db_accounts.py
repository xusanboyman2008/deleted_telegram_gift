import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import init_db, async_get_userbot_accounts

async def main():
    await init_db()
    accounts = await async_get_userbot_accounts(active_only=False, is_admin=True)
    print("Database userbot accounts:")
    for acc in accounts:
        print(f"ID: {acc.get('id')}, Phone: {acc.get('phone')}, Username: {acc.get('username')}, Active: {acc.get('active')}, Owner: {acc.get('owner_tg_id')}, Stars: {acc.get('stars_balance')}")

if __name__ == "__main__":
    asyncio.run(main())
