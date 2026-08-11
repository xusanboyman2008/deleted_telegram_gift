import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

async def main():
    print("Testing backend import and database functions...")
    from backend import db
    userbots = await db.async_get_userbot_accounts(active_only=False, is_admin=True)
    print(f"Loaded {len(userbots)} userbots from database.")
    
    for ub in userbots:
        account_id = ub['id']
        hashed_id = db.hash_userbot_id(account_id)
        print(f"Userbot ID: {account_id} -> Hash: {hashed_id}")

    print("Checking main.py WebSocket ConnectionManager...")
    from backend.main import ws_manager
    print("ws_manager initialized successfully:", ws_manager)

if __name__ == '__main__':
    asyncio.run(main())
