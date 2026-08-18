import os
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiohttp import web

# =========================
# 🔐 ENV
# =========================
TOKEN = os.getenv("BOT_TOKEN")
DONATE_URL = os.getenv("DONATE_URL")
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot")

if not TOKEN:
    raise Exception("❌ BOT_TOKEN не найден")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# =========================
# 🧠 "БАЗА" (в памяти)
# =========================
users = {}

# структура:
# users[user_id] = {
#   balance: int,
#   vpn_key: str,
#   expire: datetime,
#   devices: []
# }

# =========================
# 📌 МЕНЮ (КАК У КУРЫ)
# =========================
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Купить/Продлить", callback_data="buy"),
        InlineKeyboardButton("📱 Мои устройства", callback_data="devices"),
    )
    kb.add(
        InlineKeyboardButton("👥 Рефералы", callback_data="ref"),
        InlineKeyboardButton("🆘 Помощь", callback_data="help"),
    )
    return kb


def vpn_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🚀 Подключиться к VPN", callback_data="connect"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="menu"),
    )
    return kb


# =========================
# 🚀 СТАРТ
# =========================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    uid = message.from_user.id

    if uid not in users:
        users[uid] = {
            "balance": 0,
            "vpn_key": None,
            "expire": None,
            "devices": []
        }

    await show_profile(message.chat.id, uid)


# =========================
# 👤 ПРОФИЛЬ (КАК У КУРЫ)
# =========================
async def show_profile(chat_id, uid):
    user = users[uid]

    if user["vpn_key"]:
        text = f"""💰 Баланс: {user['balance']}₽
💎 Тариф: VPN активен
⏳ До: {user['expire'].strftime("%d.%m.%Y")}

📱 Устройств: {len(user['devices'])}

🔗 Ключ:
{user['vpn_key']}
"""
    else:
        text = f"""💰 Баланс: {user['balance']}₽
❌ VPN не активен
"""

    await bot.send_message(chat_id, text, reply_markup=vpn_menu())
    await bot.send_message(chat_id, "📌 Меню:", reply_markup=main_menu())


# =========================
# 💰 КУПИТЬ
# =========================
@dp.callback_query_handler(lambda c: c.data == "buy")
async def buy(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 Оплатить", url=DONATE_URL))

    await call.message.answer(
        "💰 Оплата\n\nПосле оплаты VPN выдаётся автоматически",
        reply_markup=kb
    )


# =========================
# 🚀 ПОДКЛЮЧИТЬСЯ
# =========================
@dp.callback_query_handler(lambda c: c.data == "connect")
async def connect(call: types.CallbackQuery):
    uid = call.from_user.id
    user = users[uid]

    if not user["vpn_key"]:
        await call.message.answer("❌ У вас нет VPN")
        return

    await call.message.answer(
        f"🚀 Ваш ключ:\n{user['vpn_key']}"
    )


# =========================
# 📱 УСТРОЙСТВА
# =========================
@dp.callback_query_handler(lambda c: c.data == "devices")
async def devices(call: types.CallbackQuery):
    uid = call.from_user.id
    user = users[uid]

    if not user["devices"]:
        await call.message.answer("📱 Устройств нет")
        return

    text = "📱 Ваши устройства:\n\n"
    for i, d in enumerate(user["devices"], 1):
        text += f"{i}. {d}\n"

    await call.message.answer(text)


# =========================
# 👥 РЕФЕРАЛЫ
# =========================
@dp.callback_query_handler(lambda c: c.data == "ref")
async def ref(call: types.CallbackQuery):
    uid = call.from_user.id

    link = f"https://t.me/{BOT_USERNAME}?start={uid}"

    await call.message.answer(
        f"""👥 Реферальная программа

Ваша ссылка:
{link}

Зарабатывайте % с оплат друзей
"""
    )


# =========================
# 🆘 ПОМОЩЬ
# =========================
@dp.callback_query_handler(lambda c: c.data == "help")
async def help_cmd(call: types.CallbackQuery):
    await call.message.answer("🆘 Поддержка: @your_support")


# =========================
# ⚡ ВЫДАЧА VPN
# =========================
def generate_vpn(user_id):
    return f"https://vpn.example.com/key_{user_id}"


def give_vpn(user_id):
    user = users[user_id]

    user["vpn_key"] = generate_vpn(user_id)
    user["expire"] = datetime.now() + timedelta(days=30)

    # добавим устройство
    user["devices"].append("Android")


# =========================
# 🌐 DONATION ALERTS WEBHOOK
# =========================
async def donate_webhook(request):
    data = await request.json()

    try:
        amount = int(data["data"]["amount"])
        username = data["data"]["username"]

        user_id = int(username)

        if user_id not in users:
            return web.Response(text="no user")

        users[user_id]["balance"] += amount

        # тариф: 100₽ = 30 дней
        if users[user_id]["balance"] >= 100:
            give_vpn(user_id)

        await bot.send_message(
            user_id,
            f"✅ Оплата: {amount}₽\nБаланс: {users[user_id]['balance']}₽"
        )

    except Exception as e:
        print("Webhook error:", e)

    return web.Response(text="ok")


# =========================
# 🚀 ЗАПУСК
# =========================
if __name__ == "__main__":
    app = web.Application()
    app.router.add_post("/donate", donate_webhook)

    dp.loop.create_task(web._run_app(app, port=8080))

    executor.start_polling(dp, skip_updates=True)
