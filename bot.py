import os
import asyncio
import sqlite3
import requests
import uuid
import time

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
DA_TOKEN = os.getenv("DA_TOKEN")
DA_URL = os.getenv("DA_URL")

PANEL_URL = os.getenv("PANEL_URL")
PANEL_LOGIN = os.getenv("PANEL_LOGIN")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD")
INBOUND_ID = int(os.getenv("INBOUND_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ===== БАЗА =====
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

# ===== 3X-UI =====
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

# ===== КНОПКИ =====
menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(KeyboardButton("🔐 Мой VPN"))
menu.add(KeyboardButton("💰 Пополнить"), KeyboardButton("👤 Профиль"))

# ===== СТАРТ =====
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    get_balance(msg.from_user.id)

    await msg.answer(
"""🔐 Moonlight VPN

👋 Добро пожаловать!

👇 Выберите действие:""",
        reply_markup=menu
    )

# ===== ПРОФИЛЬ =====
@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile(msg: types.Message):
    bal = get_balance(msg.from_user.id)
    await msg.answer(f"💰 Баланс: {bal}₽")

# ===== ПОПОЛНЕНИЕ =====
@dp.message_handler(lambda m: m.text == "💰 Пополнить")
async def deposit(msg: types.Message):
    user_id = msg.from_user.id

    link = f"{DA_URL}?comment={user_id}"

    await msg.answer(
f"""💳 Пополнение

Перейди по ссылке и закинь любую сумму:

{link}

⚠️ ВАЖНО: не меняй комментарий!"""
    )

# ===== ПОКУПКА =====
@dp.message_handler(lambda m: m.text == "🔐 Мой VPN")
async def buy(msg: types.Message):
    user_id = msg.from_user.id
    bal = get_balance(user_id)

    if bal < 199:
        return await msg.answer("❌ Нужно минимум 199₽")

    add_balance(user_id, -199)

    vpn = create_vpn(user_id, 30)

    await msg.answer(f"✅ Готово!\n\n🔐 {vpn}")

# ===== ДОНАТЫ =====
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

                    if not d["message"]:
                        continue

                    user_id = int(d["message"])

                    add_balance(user_id, amount)

                    await bot.send_message(
                        user_id,
                        f"💰 +{amount}₽ зачислено"
                    )

        except Exception as e:
            print(e)

        await asyncio.sleep(10)

# ===== ЗАПУСК =====
async def main():
    asyncio.create_task(check_donates())
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
