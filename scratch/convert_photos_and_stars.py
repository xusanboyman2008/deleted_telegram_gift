import json
import base64
import os
import sys
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import init_db, update_userbot_account_db, db_save_userbot_accounts
from userbot.userbot import load_userbot_file_data, save_userbot_file_data

async def main():
    await init_db()
    data = load_userbot_file_data()
    accounts = data.get("accounts", [])
    photos_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "assets", "user_photos"))
    os.makedirs(photos_dir, exist_ok=True)

    for acc in accounts:
        acc_id = acc.get("id")
        photo_val = acc.get("photo", "")
        if photo_val and photo_val.startswith("data:image/"):
            try:
                header, b64_str = photo_val.split(",", 1)
                img_data = base64.b64decode(b64_str)
                file_name = f"ub_{acc_id}.jpg"
                full_path = os.path.join(photos_dir, file_name)
                with open(full_path, "wb") as f:
                    f.write(img_data)
                rel_path = f"assets/user_photos/{file_name}"
                acc["photo"] = rel_path
                print(f"Account #{acc_id}: converted base64 photo to file {rel_path} ({len(img_data)} bytes)")
            except Exception as e:
                print(f"Error converting photo for account #{acc_id}: {e}")

        # Update star balance fix
        if acc_id == 6:
            acc["stars_balance"] = 49
        elif acc_id == 5:
            acc["stars_balance"] = 0 # client unregistered/inactive
        else:
            acc["stars_balance"] = 0

    # Save to JSON and DB
    save_userbot_file_data({"enabled": True, "accounts": accounts})
    for acc in accounts:
        await update_userbot_account_db(
            acc["id"],
            photo=acc.get("photo", ""),
            stars_balance=acc.get("stars_balance", 0)
        )
    print("Done converting photos and updating DB!")

if __name__ == "__main__":
    asyncio.run(main())
