import os
from telethon import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest
from dotenv import load_dotenv
from db import save_account_metadata

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_DIR = "session_data"

os.makedirs(SESSION_DIR, exist_ok=True)

async def login_user():
    phone = input("📲 Enter your phone number (with country code): ")
    session_name = f"{SESSION_DIR}/{phone.replace('+', '')}"

    async with TelegramClient(session_name, API_ID, API_HASH) as client:
        await client.connect()

        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            code = input("🔐 Enter the code you received: ")
            try:
                await client.sign_in(phone, code)
            except Exception as e:
                print("❌ Login failed:", e)
                return
        
        # ✅ Update profile name and bio
        try:
            me = await client.get_me()
            updated_name = f"{me.first_name} via — @SpinifyAdsBot"
            await client(UpdateProfileRequest(
                first_name=updated_name[:64],
                about="#1 Free Ads Bot — Join @PhiloBots"
            ))
            print(f"✅ Profile updated: {updated_name}")
        except Exception as e:
            print("⚠️ Failed to update profile info:", e)

        # ✅ Save metadata to TinyDB
        try:
            save_account_metadata(
                user_id=me.id,
                phone=phone,
                session_name=session_name,
                account_name=me.first_name,
                username=me.username or None
            )
        except Exception as e:
            print("❌ Failed to save to DB:", e)

        print("🎉 Login successful! You can now return to the main bot.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(login_user())
