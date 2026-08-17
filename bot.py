import os
import logging
import asyncio
import requests

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DA_TOKEN = os.getenv("DA_TOKEN")
DA_NICK = os.getenv("DA_NICK")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ===== БАЗА (простая) =====
users = {}
processed_ids = set()

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {"balance": 0}
    return users[user_id]

# ===== REPLY =====
reply_kb = ReplyKeyboardMarkup(resize_keyboard=True)
reply_kb.add(KeyboardButton("🏠 Главное меню"))

# ===== INLINE =====
def main_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔐 Мой VPN", callback_data="vpn"))
    kb.add(InlineKeyboardButton("👤 Профиль", callback_data="profile"))
    kb.add(InlineKeyboardButton("💳 Пополнить", callback_data="pay"))
    kb.add(InlineKeyboardButton("🌍 Серверы", callback_data="servers"))
    return kb

def back():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🏠 В меню", callback_data="menu"))
    return kb

# ===== START =====
@dp.message_handler(commands=["start"])
@dp.message_handler(lambda m: m.text == "🏠 Главное меню")
async def start(msg: types.Message):
    get_user(msg.from_user.id)

    await msg.answer("🔐 Moonlight VPN", reply_markup=reply_kb)
    await msg.answer("👇 Меню:", reply_markup=main_menu())

# ===== CALLBACK =====
@dp.callback_query_handler(lambda c: True)
async def cb(call: types.CallbackQuery):

    if call.data == "menu":
        await call.message.edit_text("👇 Меню:", reply_markup=main_menu())

    elif call.data == "profile":
        u = get_user(call.from_user.id)

        await call.message.edit_text(
f"""👤 Профиль

Баланс: {u['balance']}₽
Тариф: ❌ Нет активной подписки
ID: {call.from_user.id}""",
            reply_markup=back()
        )

    elif call.data == "servers":
        await call.message.edit_text(
"""🌍 Серверы

⚡ Автовыбор (обычные VPN)

🇰🇿 Казахстан
🇷🇺 Россия
🇳🇱 Нидерланды

──────────────

⚡ Автовыбор (обход блокировок)

🇩🇪 Обход 1 — Германия
🇩🇪 Обход 2 — Германия
🇩🇪 Обход 3 — Германия
""",
            reply_markup=back()
        )

    elif call.data == "vpn":
        await call.message.edit_text(
            "🔐 VPN появится позже",
            reply_markup=back()
        )

    elif call.data == "pay":
        user_id = call.from_user.id

        # 🔥 ВАЖНО — автоматизация
        pay_url = f"https://www.donationalerts.com/r/{DA_NICK}?message={user_id}"

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("💳 Оплатить", url=pay_url))
        kb.add(InlineKeyboardButton("🏠 В меню", callback_data="menu"))

        await call.message.edit_text(
            "💳 Оплата\n\nНажмите кнопку ниже:",
            reply_markup=kb
        )

    await call.answer()

# ===== АВТО ДОНАТЫ =====
async def check_donates():
    while True:
        try:
            r = requests.get(
                "https://www.donationalerts.com/api/v1/alerts/donations",
                headers={"Authorization": f"Bearer {DA_TOKEN}"}
            ).json()

            for d in r["data"]:
                if d["id"] in processed_ids:
                    continue

                processed_ids.add(d["id"])

                try:
                    user_id = int(d["message"])  # 🔥 берём из message
                except:
                    continue

                amount = int(float(d["amount"]))

                u = get_user(user_id)
                u["balance"] += amount

                await bot.send_message(user_id, f"💰 +{amount}₽ зачислено")

        except Exception as e:
            print("Ошибка:", e)

        await asyncio.sleep(10)

# ===== RUN =====
async def on_startup(_):
    asyncio.create_task(check_donates())

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
