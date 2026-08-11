import asyncio
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from userbot.userbot import get_userbot_contacts, get_running_client, get_all_userbot_accounts

async def main():
    print("Testing get_userbot_contacts(6):")
    try:
        contacts = await get_userbot_contacts(6, limit=10)
        print(f"Success! Contacts count: {len(contacts)}")
        for c in contacts[:5]:
            print(f"- {c['title']} ({c['peer']}) last_msg: {c['last_msg']}")
    except Exception as e:
        print(f"Error calling get_userbot_contacts: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
