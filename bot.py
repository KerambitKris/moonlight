import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

from flask import Flask, request

# =========================
# 🔐 ENV
# =========================
TOKEN = os.getenv("BOT_TOKEN")
DONATE_SECRET = os.getenv("DONATE_SECRET")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

app = Flask(__name__)

# =========================
# 💾 ФЕЙК БД (потом заменим)
# =========================
users_balance = {}
users_vpn = {}

# =========================
# 🔘 МЕНЮ
# =========================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row(
        KeyboardButton("💳 Купить/Продлить"),
        KeyboardButton("📱 Мои устройства")
    )
    kb.row(
        KeyboardButton("🔗 Рефералы")
    )
    kb.row(
        KeyboardButton("🚀 Подключиться к VPN")
    )
    kb.row(
        KeyboardButton("🆘 Помощь")
    )

    return kb


# =========================
# 🚀 START
# =========================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    uid = message.from_user.id

    if uid not in users_balance:
        users_balance[uid] = 0

    await message.answer(
        f"🔐 Moonlight VPN\n\n"
        f"💰 Баланс: {users_balance[uid]}₽",
        reply_markup=main_menu()
    )


# =========================
# 💳 ПОКУПКА
# =========================
@dp.message_handler(lambda m: m.text == "💳 Купить/Продлить")
async def buy(message: types.Message):
    uid = message.from_user.id

    link = f"https://www.donationalerts.com/r/smertelobed0?comment={uid}"

    await message.answer(
        f"💳 Оплата\n\n"
        f"⚠️ ВАЖНО: не меняй комментарий!\n\n"
        f"{link}",
        reply_markup=main_menu()
    )


# =========================
# 🚀 VPN
# =========================
@dp.message_handler(lambda m: m.text == "🚀 Подключиться к VPN")
async def vpn(message: types.Message):
    uid = message.from_user.id

    if uid not in users_vpn:
        await message.answer("❌ Нет подписки", reply_markup=main_menu())
        return

    await message.answer(
        f"🔑 Твой VPN:\n{users_vpn[uid]}",
        reply_markup=main_menu()
    )


# =========================
# 📱 УСТРОЙСТВА
# =========================
@dp.message_handler(lambda m: m.text == "📱 Мои устройства")
async def devices(message: types.Message):
    await message.answer("📱 Пока пусто", reply_markup=main_menu())


# =========================
# 🔗 РЕФЕРАЛЫ
# =========================
@dp.message_handler(lambda m: m.text == "🔗 Рефералы")
async def refs(message: types.Message):
    link = f"https://t.me/{(await bot.get_me()).username}?start={message.from_user.id}"

    await message.answer(
        f"🔗 Твоя ссылка:\n{link}",
        reply_markup=main_menu()
    )


# =========================
# 🆘 ПОМОЩЬ
# =========================
@dp.message_handler(lambda m: m.text == "🆘 Помощь")
async def help_cmd(message: types.Message):
    await message.answer("🆘 @support", reply_markup=main_menu())


# =========================
# 💸 WEBHOOK (СЕРДЦЕ СИСТЕМЫ)
# =========================
@app.route("/donate", methods=["POST"])
def donate():
    data = request.json

    if not data:
        return "no data", 400

    # защита
    if data.get("token") != DONATE_SECRET:
        return "bad token", 403

    amount = int(data["amount"])
    comment = data.get("message", "")

    try:
        user_id = int(comment)
    except:
        return "no user id", 400

    # начисляем баланс
    users_balance[user_id] = users_balance.get(user_id, 0) + amount

    # выдаём VPN (фейк)
    users_vpn[user_id] = f"https://vpn-link/{user_id}"

    # уведомляем пользователя
    import asyncio
    asyncio.run(send_payment(user_id, amount))

    return "ok"


async def send_payment(user_id, amount):
    try:
        await bot.send_message(
            user_id,
            f"✅ Оплата получена: {amount}₽\n\n🔑 VPN выдан"
        )
    except:
        pass


# =========================
# 🚀 ЗАПУСК
# =========================
if __name__ == "__main__":
    import threading

    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()
    executor.start_polling(dp, skip_updates=True)
