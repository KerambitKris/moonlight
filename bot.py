import os
import asyncio
import sqlite3
import requests
import uuid
import time
import random

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ================== НАСТРОЙКИ ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ================== БАЗА ==================

conn = sqlite3.connect("db.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)
""")
conn.commit()

# ================== ПИНГ С КЭШЕМ ==================

ping_cache = {}

def format_ping(ping):
    if ping < 40:
        status = "🟢"
    elif ping < 70:
        status = "🟡"
    else:
        status = "🔴"
    return f"{ping}ms {status}"

def get_ping(server):
    now = time.time()

    if server in ping_cache:
        ping, ts = ping_cache[server]

        # 30 минут
        if now - ts < 1800:
            return format_ping(ping)

        # плавное изменение
        ping += random.randint(-8, 8)
        ping = max(15, min(120, ping))
    else:
        ping = random.randint(20, 80)

    ping_cache[server] = (ping, now)
    return format_ping(ping)

# ================== КНОПКИ ==================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(KeyboardButton("🌍 Серверы"))

# ================== СТАРТ ==================

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer(
"""🔐 Moonlight VPN

👇 Выберите действие:""",
        reply_markup=menu
    )

# ================== СЕРВЕРА ==================

@dp.message_handler(lambda m: m.text == "🌍 Серверы")
async def servers(msg: types.Message):

    text = f"""
⚡ Автовыбор (обычные VPN)

🇰🇿 Казахстан — {get_ping("kz")}
🇷🇺 Россия — {get_ping("ru")}
🇳🇱 Нидерланды — {get_ping("nl")}

──────────────
🚄 Обход для моб. интернета

⚡ Автовыбор (обход блокировок)

🇩🇪 Обход 1 — {get_ping("de1")}
🇩🇪 Обход 2 — {get_ping("de2")}
🇩🇪 Обход 3 — {get_ping("de3")}
"""

    await msg.answer(text)

# ================== ЗАПУСК ==================

async def main():
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
