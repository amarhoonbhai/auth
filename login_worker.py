import os
import time
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest
from db import dequeue_login, save_account_metadata
from dotenv import load_dotenv

load_dotenv()
SESSION_DIR = os.getenv("API_SESSION_DIR", "session_data")
os.makedirs(SESSION_DIR, exist_ok=True)

POLL_INTERVAL = 3  # seconds

def make_session_path(phone):
    safe = phone.replace("+", "").replace(" ", "").replace(":", "")
    return os.path.join(SESSION_DIR, f"{safe}.session")

def export_session_string(client):
    return StringSession.save(client.session)

async def process_login_request(req):
    api_id = int(req["api_id"])
    api_hash = req["api_hash"]
    phone = req["phone"]
    otp = req.get("otp")
    chat_id = req.get("chat_id")
    session_path = make_session_path(phone)

    print(f"[worker] Processing login for {phone}")
    client = TelegramClient(session_path, api_id, api_hash)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            try:
                await client.sign_in(phone=phone, code=otp)
            except errors.SessionPasswordNeededError:
                await client.disconnect()
                return False, "2FA enabled. Manual intervention required."
            except errors.PhoneCodeExpiredError:
                await client.disconnect()
                return False, "OTP expired."
            except errors.PhoneCodeInvalidError:
                await client.disconnect()
                return False, "Invalid OTP."
            except Exception as e:
                await client.disconnect()
                return False, f"Sign in failed: {e}"

        me = await client.get_me()
        try:
            updated_name = (me.first_name or "") + " via — @SpinifyAdsBot"
            await client(UpdateProfileRequest(
                first_name=updated_name[:64],
                about="#1 Free Ads Bot — Join @PhiloBots"
            ))
        except Exception as e:
            print("[worker] Failed to update profile:", e)

        session_str = export_session_string(client)

        save_account_metadata(
            user_id=me.id,
            phone=phone,
            session_name=session_path,
            account_name=me.first_name or "",
            username=me.username or "",
            session_string=session_str
        )

        await client.disconnect()
        print(f"[worker] Login successful for {phone} (user_id={me.id})")
        return True, f"Login success for {phone}"
    except Exception as e:
        try:
            await client.disconnect()
        except:
            pass
        return False, str(e)

async def worker_loop():
    import asyncio
    while True:
        req = dequeue_login()
        if req:
            ok, msg = await process_login_request(req)
            print("[worker] Result:", ok, msg)
        else:
            await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    import asyncio
    asyncio.run(worker_loop())
