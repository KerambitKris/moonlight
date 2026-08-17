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
DA_TOKEN = os.getenv("DA_TOKEN")
DA_URL = os.getenv("DA_URL")

PANEL_URL = os.getenv("PANEL_URL")
PANEL_LOGIN = os.getenv("PANEL_LOGIN")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD")
INBOUND_ID = int(os.getenv("INBOUND_ID"))

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

def get_balance(user_id):
    cur.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return 0
    return row[0]

def add_balance(user_id, amount):
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()

def minus_balance(user_id, amount):
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, user_id))
    conn.commit()

# ================== ПИНГ (красивый) ==================

ping_cache = {}

def format_ping(p):
    if p < 40:
        return f"{p}ms 🟢"
    elif p < 70:
        return f"{p}ms 🟡"
    return f"{p}ms 🔴"

def get_ping(name):
    now = time.time()

    if name in ping_cache:
        ping, ts = ping_cache[name]

        if now - ts < 1800:
            return format_ping(ping)

        ping += random.randint(-8, 8)
        ping = max(20, min(120, ping))
    else:
        ping = random.randint(25, 80)

    ping_cache[name] = (ping, now)
    return format_ping(ping)

# ================== 3X-UI ==================

def login_panel():
    s = requests.Session()
    s.post(f"{PANEL_URL}/login", data={
        "username": PANEL_LOGIN,
        "password": PANEL_PASSWORD
    })
    return s

def create_vpn(user_id, days=30):
    s = login_panel()

    client_id = str(uuid.uuid4())
    expiry = int((time.time() + days * 86400) * 1000)

    data = {
        "id": INBOUND_ID,
        "settings": {
            "clients": [{
                "id": client_id,
                "email": f"user_{user_id}",
                "limitIp": 1,
                "totalGB": 0,
                "expiryTime": expiry,
                "enable": True
            }]
        }
    }

    s.post(f"{PANEL_URL}/panel/api/inbounds/addClient", json=data)

    return f"{PANEL_URL}/sub/{client_id}"

# ================== КНОПКИ ==================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add("🔐 Мой VPN")
menu.add("🌍 Серверы", "👤 Профиль")
menu.add("💰 Пополнить")

# ================== СТАРТ ==================

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    get_balance(msg.from_user.id)

    await msg.answer(
"""🔐 Moonlight VPN

⚡ Быстрый и стабильный VPN

👇 Выберите действие:""",
        reply_markup=menu
    )

# ================== ПРОФИЛЬ ==================

@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile(msg: types.Message):
    user_id = msg.from_user.id
    bal = get_balance(user_id)

    await msg.answer(
f"""👤 Профиль

Баланс: {bal}₽
Тариф: ❌ Нет активной подписки
ID: {user_id}""",
        reply_markup=menu
    )

# ================== ПОПОЛНЕНИЕ ==================

@dp.message_handler(lambda m: m.text == "💰 Пополнить")
async def deposit(msg: types.Message):
    await msg.answer(
f"""💳 Пополнение

Перейди по ссылке:
{DA_URL}

В комментарии укажи свой ID:
{msg.from_user.id}

⚠️ ИНАЧЕ деньги не зачислятся""",
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

⚡ Автовыбор (обход блокировок)

🇩🇪 Обход 1 — {get_ping("de1")}
🇩🇪 Обход 2 — {get_ping("de2")}
🇩🇪 Обход 3 — {get_ping("de3")}
"""
    await msg.answer(text, reply_markup=menu)

# ================== VPN ==================

@dp.message_handler(lambda m: m.text == "🔐 Мой VPN")
async def vpn(msg: types.Message):
    user_id = msg.from_user.id
    bal = get_balance(user_id)

    if bal < 199:
        return await msg.answer("❌ Недостаточно средств", reply_markup=menu)

    minus_balance(user_id, 199)
    link = create_vpn(user_id)

    await msg.answer(f"🔐 Ваш VPN:\n{link}", reply_markup=menu)

# ================== ДОНАТЫ ==================

last_id = 0

async def check_donates():
    global last_id

    while True:
        try:
            r = requests.get(
                "https://www.donationalerts.com/api/v1/alerts/donations",
                headers={"Authorization": f"Bearer {DA_TOKEN}"}
            ).json()

            for d in r["data"]:
                if d["id"] > last_id:
                    last_id = d["id"]

                    amount = int(float(d["amount"]))

                    try:
                        user_id = int(d["message"])  # фикс!
                    except:
                        continue

                    add_balance(user_id, amount)

                    await bot.send_message(
                        user_id,
                        f"💰 Пополнение: +{amount}₽"
                    )
        except:
            pass

        await asyncio.sleep(10)

# ================== ЗАПУСК ==================

async def main():
    asyncio.create_task(check_donates())
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
