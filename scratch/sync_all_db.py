import sys
import os
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import init_db, db_save_userbot_accounts, update_userbot_account_db
from userbot.userbot import load_userbot_file_data, save_userbot_file_data

async def main():
    await init_db()
    data = load_userbot_file_data()
    accs = data.get("accounts", [])
    for a in accs:
        if a.get("id") == 6:
            a["stars_balance"] = 49
        else:
            a["stars_balance"] = 0
    save_userbot_file_data(data)
    db_save_userbot_accounts(accs)
    for a in accs:
        await update_userbot_account_db(a["id"], stars_balance=a.get("stars_balance", 0), photo=a.get("photo", ""))
    print("Synced both Postgres & SQLite databases successfully!")

if __name__ == "__main__":
    asyncio.run(main())
