#!/usr/bin/env python3
"""
Interactive Session String Generator for Hydrogram Userbots.
Generates session strings using phone numbers and updates userbot/account.json & userbot/user_accounts.json.
"""

import os
import json
import asyncio
import sys

# Ensure root dir is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "account.json")
USER_ACCOUNTS_FILE = os.path.join(os.path.dirname(__file__), "user_accounts.json")

DEFAULT_API_ID = 35251724
DEFAULT_API_HASH = "b11e753959873b1df047454a8d816604"


def load_file(filepath):
    if not os.path.exists(filepath):
        return {"enabled": True, "accounts": []}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return {"enabled": True, "accounts": []}


def save_file(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def sync_both_files(accounts):
    data_acc = load_file(ACCOUNT_FILE)
    data_acc["accounts"] = accounts
    save_file(ACCOUNT_FILE, data_acc)

    data_usr = load_file(USER_ACCOUNTS_FILE)
    data_usr["accounts"] = accounts
    save_file(USER_ACCOUNTS_FILE, data_usr)


async def generate_session_for_account(acc):
    phone = acc.get("phone", "").strip()
    if not phone:
        phone = input("📱 Enter phone number (with country code, e.g. +573023045559): ").strip()
        acc["phone"] = phone

    api_id = acc.get("api_id") or DEFAULT_API_ID
    api_hash = acc.get("api_hash") or DEFAULT_API_HASH
    acc["api_id"] = api_id
    acc["api_hash"] = api_hash

    from hydrogram import Client
    from hydrogram.errors import SessionPasswordNeeded

    print(f"\n🚀 Connecting to Telegram for {phone} (API_ID: {api_id})...")
    client = Client(f"session_gen_{acc.get('id', 'new')}", api_id=api_id, api_hash=api_hash, in_memory=True)

    await client.connect()
    try:
        code_info = await client.send_code(phone)
        phone_code_hash = code_info.phone_code_hash

        code = input(f"📩 Enter Telegram login code sent to {phone}: ").strip()
        try:
            await client.sign_in(phone, phone_code_hash, code)
        except SessionPasswordNeeded:
            pwd = input("🔐 Enter 2FA Password: ").strip()
            await client.check_password(pwd)

        me = await client.get_me()
        session_str = await client.export_session_string()

        acc["session_string"] = session_str
        acc["first_name"] = me.first_name or ""
        acc["last_name"] = me.last_name or ""
        acc["username"] = me.username or ""
        acc["active"] = True

        print(f"\n✅ Session generated successfully for {me.first_name} (@{me.username or 'no_user'})!")
        print(f"🔑 Session String: {session_str[:30]}...")

    finally:
        await client.disconnect()

    return acc


async def main():
    print("=" * 60)
    print("🤖 USERBOT SESSION STRING GENERATOR (Hydrogram)")
    print("=" * 60)

    acc_data = load_file(ACCOUNT_FILE)
    accounts = acc_data.get("accounts", [])

    print(f"\nFound {len(accounts)} accounts in account.json:\n")
    for i, a in enumerate(accounts):
        has_str = "✅ Active Session" if a.get("session_string") else "❌ No Session"
        print(f" [{i+1}] ID #{a.get('id')}: Phone {a.get('phone')} - {a.get('first_name','')} (@{a.get('username','')}) ({has_str})")

    print("\nOptions:")
    print(" 1. Generate session for existing account")
    print(" 2. Add NEW userbot by phone number only")
    print(" 3. Refresh all accounts missing session strings")
    choice = input("\nSelect option (1-3): ").strip()

    if choice == "1":
        idx = int(input("Enter account number to update (1-N): ")) - 1
        if 0 <= idx < len(accounts):
            accounts[idx] = await generate_session_for_account(accounts[idx])
            sync_both_files(accounts)
    elif choice == "2":
        phone = input("📱 Enter new phone number (e.g. +573023045559): ").strip()
        max_id = max([a.get("id", 0) for a in accounts], default=0)
        # Inherit API keys from first account if available
        first_acc = accounts[0] if accounts else {}
        new_acc = {
            "id": max_id + 1,
            "session": f"account_{max_id + 1}",
            "phone": phone,
            "session_string": "",
            "api_id": first_acc.get("api_id") or DEFAULT_API_ID,
            "api_hash": first_acc.get("api_hash") or DEFAULT_API_HASH,
            "first_name": "",
            "last_name": "",
            "username": "",
            "photo": "",
            "active": True
        }
        updated_acc = await generate_session_for_account(new_acc)
        accounts.append(updated_acc)
        sync_both_files(accounts)
    elif choice == "3":
        for i in range(len(accounts)):
            if not accounts[i].get("session_string"):
                print(f"\nProcessing Account #{accounts[i].get('id')} ({accounts[i].get('phone')})...")
                accounts[i] = await generate_session_for_account(accounts[i])
                sync_both_files(accounts)
        print("\nAll accounts updated!")

    print("\n🎉 Process complete! Both account.json and user_accounts.json are synced.")


if __name__ == "__main__":
    asyncio.run(main())
