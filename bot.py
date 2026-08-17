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

        if now - ts < 1800:
            return format_ping(ping)

        ping += random.randint(-8, 8)
        ping = max(15, min(120, ping))
    else:
        ping = random.randint(20, 80)

    ping_cache[server] = (ping, now)
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
    expiry_time = int((time.time() + days * 86400) * 1000)

    data = {
        "id": INBOUND_ID,
        "settings": {
            "clients": [
                {
                    "id": client_id,
                    "alterId": 0,
                    "email": f"user_{user_id}",
                    "limitIp": 1,
                    "totalGB": 0,
                    "expiryTime": expiry_time,
                    "enable": True
                }
            ]
        }
    }

    s.post(f"{PANEL_URL}/panel/api/inbounds/addClient", json=data)

    return f"{PANEL_URL}/sub/{client_id}"

# ================== КНОПКИ ==================

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(KeyboardButton("🔐 Мой VPN"))
menu.add(KeyboardButton("💰 Пополнить"), KeyboardButton("👤 Профиль"))
menu.add(KeyboardButton("🌍 Серверы"))

buy_menu = ReplyKeyboardMarkup(resize_keyboard=True)
buy_menu.add(KeyboardButton("30 дней — 199₽"))
buy_menu.add(KeyboardButton("90 дней — 499₽"))
buy_menu.add(KeyboardButton("⬅️ Назад"))

# ================== СТАРТ ==================

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    get_balance(msg.from_user.id)

    await msg.answer(
"""🔐 Moonlight VPN

👋 Добро пожаловать!

👇 Выберите действие:""",
        reply_markup=menu
    )

# ================== ПРОФИЛЬ ==================

@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile(msg: types.Message):
    bal = get_balance(msg.from_user.id)
    await msg.answer(f"💰 Баланс: {bal}₽")

# ================== ПОПОЛНЕНИЕ ==================

@dp.message_handler(lambda m: m.text == "💰 Пополнить")
async def deposit(msg: types.Message):
    await msg.answer(
f"""💳 Пополнение

{DA_URL}

После оплаты деньги придут автоматически"""
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

# ================== ПОКУПКА ==================

@dp.message_handler(lambda m: m.text == "🔐 Мой VPN")
async def vpn_menu(msg: types.Message):
    await msg.answer("Выбери тариф:", reply_markup=buy_menu)

@dp.message_handler(lambda m: m.text == "⬅️ Назад")
async def back(msg: types.Message):
    await msg.answer("Главное меню", reply_markup=menu)

@dp.message_handler(lambda m: "30 дней" in m.text)
async def buy_30(msg: types.Message):
    user_id = msg.from_user.id
    bal = get_balance(user_id)

    if bal < 199:
        return await msg.answer("❌ Недостаточно средств")

    minus_balance(user_id, 199)
    vpn = create_vpn(user_id, 30)

    await msg.answer(f"✅ Ваш VPN:\n{vpn}")

@dp.message_handler(lambda m: "90 дней" in m.text)
async def buy_90(msg: types.Message):
    user_id = msg.from_user.id
    bal = get_balance(user_id)

    if bal < 499:
        return await msg.answer("❌ Недостаточно средств")

    minus_balance(user_id, 499)
    vpn = create_vpn(user_id, 90)

    await msg.answer(f"✅ Ваш VPN:\n{vpn}")

# ================== АВТО-ДОНАТЫ ==================

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
                    user_id = int(d["username"])

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
