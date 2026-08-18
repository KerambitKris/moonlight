import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.utils import executor
from aiohttp import web

# =========================
# 🔐 ENV
# =========================
TOKEN = os.getenv("BOT_TOKEN")
DONATE_URL = os.getenv("DONATE_URL")

if not TOKEN:
    raise Exception("❌ BOT_TOKEN не найден в ENV")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# =========================
# 🧠 ПАМЯТЬ (временно)
# =========================
users_balance = {}
users_vpn = {}

# =========================
# 📌 МЕНЮ (БОЛЬШИЕ КНОПКИ)
# =========================
def main_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🚀 Подключиться к VPN", callback_data="vpn"),
        InlineKeyboardButton("💰 Купить / Продлить", callback_data="pay"),
        InlineKeyboardButton("📱 Мои устройства", callback_data="devices"),
        InlineKeyboardButton("👥 Рефералы", callback_data="ref"),
        InlineKeyboardButton("🆘 Помощь", callback_data="help"),
    )
    return kb

def back_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🏠 Главное меню"))
    return kb

# =========================
# 🚀 СТАРТ
# =========================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    uid = message.from_user.id
    users_balance.setdefault(uid, 0)

    await message.answer(
        "🚀 Moonlight VPN\n\nВыберите действие:",
        reply_markup=main_menu()
    )

# =========================
# 🏠 В МЕНЮ
# =========================
@dp.message_handler(lambda m: m.text == "🏠 Главное меню")
async def back(message: types.Message):
    await message.answer("🏠 Главное меню:", reply_markup=main_menu())

# =========================
# 🔐 VPN
# =========================
@dp.callback_query_handler(lambda c: c.data == "vpn")
async def vpn(call: types.CallbackQuery):
    uid = call.from_user.id
    balance = users_balance.get(uid, 0)

    if uid in users_vpn:
        text = f"""💎 VPN активен

Баланс: {balance}₽
Ключ:
{users_vpn[uid]}
"""
    else:
        text = f"""❌ VPN нет

Баланс: {balance}₽
Пополните баланс"""

    await call.message.answer(text, reply_markup=back_menu())

# =========================
# 💰 ОПЛАТА
# =========================
@dp.callback_query_handler(lambda c: c.data == "pay")
async def pay(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 Оплатить", url=DONATE_URL))

    await call.message.answer(
        "💰 Пополнение\n\nПосле оплаты баланс начислится автоматически",
        reply_markup=kb
    )

# =========================
# 📱 УСТРОЙСТВА
# =========================
@dp.callback_query_handler(lambda c: c.data == "devices")
async def devices(call: types.CallbackQuery):
    await call.message.answer(
        "📱 Устройств пока нет",
        reply_markup=back_menu()
    )

# =========================
# 👥 РЕФЕРАЛЫ
# =========================
@dp.callback_query_handler(lambda c: c.data == "ref")
async def ref(call: types.CallbackQuery):
    uid = call.from_user.id
    link = f"https://t.me/YOUR_BOT?start={uid}"

    await call.message.answer(
        f"👥 Ваша ссылка:\n{link}",
        reply_markup=back_menu()
    )

# =========================
# 🆘 ПОМОЩЬ
# =========================
@dp.callback_query_handler(lambda c: c.data == "help")
async def help_cmd(call: types.CallbackQuery):
    await call.message.answer(
        "🆘 Поддержка: @your_support",
        reply_markup=back_menu()
    )

# =========================
# ⚡ VPN ВЫДАЧА
# =========================
def generate_vpn(user_id):
    return f"https://vpn.example.com/key_{user_id}"

def give_vpn(user_id):
    users_vpn[user_id] = generate_vpn(user_id)

# =========================
# 🌐 WEBHOOK (DonationAlerts)
# =========================
async def donate_webhook(request):
    data = await request.json()

    try:
        amount = int(data["data"]["amount"])
        username = data["data"]["username"]

        user_id = int(username)

        users_balance[user_id] = users_balance.get(user_id, 0) + amount

        if users_balance[user_id] >= 100 and user_id not in users_vpn:
            give_vpn(user_id)

        await bot.send_message(
            user_id,
            f"✅ Оплата: {amount}₽\nБаланс: {users_balance[user_id]}₽"
        )

    except Exception as e:
        print("Webhook error:", e)

    return web.Response(text="ok")

# =========================
# 🚀 ЗАПУСК (ВАЖНО)
# =========================
if __name__ == "__main__":
    app = web.Application()
    app.router.add_post("/donate", donate_webhook)

    dp.loop.create_task(web._run_app(app, port=8080))

    executor.start_polling(dp, skip_updates=True)
