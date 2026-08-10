import asyncio
import os
import sys

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

import db

async def test():
    # Make sure we use the postgres DB URL
    os.environ["DATABASE_URL"] = "postgresql://telegram_gift_user:uBhyBgNcCvvUBBp8hdnFtcB3SpkLxdgZ@dpg-d9q5nc6gekts73chn830-a.frankfurt-postgres.render.com/telegram_gift"
    await db.init_db()
    
    print("Default allowed admins:")
    admins = await db.get_allowed_admins()
    print(admins)
    
    # Try adding a new admin
    print("\nAdding admin 11111111...")
    new_list = admins + [11111111]
    await db.set_allowed_admins(new_list)
    
    print("New allowed admins:")
    print(await db.get_allowed_admins())
    
    # Clean up and reset
    print("\nResetting to original list...")
    await db.set_allowed_admins(admins)
    print(await db.get_allowed_admins())

if __name__ == "__main__":
    asyncio.run(test())
