import os
import asyncio
import sqlite3
import requests
import uuid
import time

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DA_TOKEN = os.getenv("DA_TOKEN")
DA_NICK = os.getenv("DA_NICK")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ================= DB =================

conn = sqlite3.connect("db.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    user_id INTEGER,
    amount INTEGER,
    status TEXT
)
""")

conn.commit()

# ================= DB FUNCS =================

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

def create_payment(user_id, amount):
    pid = str(uuid.uuid4())

    cur.execute(
        "INSERT INTO payments (id, user_id, amount, status) VALUES (?, ?, ?, ?)",
        (pid, user_id, amount, "pending")
    )
    conn.commit()

    return pid

def mark_paid(pid):
    cur.execute("UPDATE payments SET status='paid' WHERE id=?", (pid,))
    conn.commit()

def is_paid(pid):
    cur.execute("SELECT status FROM payments WHERE id=?", (pid,))
    row = cur.fetchone()
    return row and row[0] == "paid"

# ================= UI =================

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        InlineKeyboardButton("💳 Пополнить", callback_data="deposit")
    )
    return kb

# ================= START =================

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    get_balance(msg.from_user.id)

    await msg.answer(
        "🔐 Moonlight VPN\n\nВыберите действие:",
        reply_markup=main_menu()
    )

# ================= PROFILE =================

@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile(call: types.CallbackQuery):
    uid = call.from_user.id
    bal = get_balance(uid)

    await call.message.edit_text(
f"""👤 Профиль

Баланс: {bal}₽
Тариф: ❌ Нет активной подписки
ID: {uid}""",
        reply_markup=main_menu()
    )

# ================= CREATE PAYMENT =================

@dp.callback_query_handler(lambda c: c.data == "deposit")
async def deposit(call: types.CallbackQuery):

    uid = call.from_user.id
    amount = 100  # фикс или можешь менять

    pid = create_payment(uid, amount)

    # 🔥 УНИКАЛЬНАЯ ССЫЛКА
    link = f"https://www.donationalerts.com/r/{DA_NICK}?amount={amount}&message={pid}"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 Оплатить", url=link))
    kb.add(InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_{pid}"))

    await call.message.edit_text(
f"""💳 Оплата

Сумма: {amount}₽

Нажми кнопку ниже:""",
        reply_markup=kb
    )

# ================= CHECK PAYMENT =================

@dp.callback_query_handler(lambda c: c.data.startswith("check_"))
async def check_payment(call: types.CallbackQuery):

    pid = call.data.split("_")[1]

    if is_paid(pid):
        await call.answer("✅ Оплачено!", show_alert=True)
    else:
        await call.answer("❌ Пока нет оплаты", show_alert=True)

# ================= DONATIONS =================

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
                    pid = d["message"]

                    cur.execute("SELECT user_id, status FROM payments WHERE id=?", (pid,))
                    row = cur.fetchone()

                    if not row:
                        continue

                    user_id, status = row

                    # 🔒 защита от дубликатов
                    if status == "paid":
                        continue

                    mark_paid(pid)
                    add_balance(user_id, amount)

                    await bot.send_message(
                        user_id,
                        f"💰 Пополнение: +{amount}₽"
                    )

        except:
            pass

        await asyncio.sleep(10)

# ================= RUN =================

async def main():
    asyncio.create_task(check_donates())
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
