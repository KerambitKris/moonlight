import os
import uuid
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

# =========================
# 🔐 ENV
# =========================
TOKEN = os.getenv("BOT_TOKEN")
PANEL_URL = os.getenv("PANEL_URL")
PANEL_LOGIN = os.getenv("PANEL_LOGIN")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD")
INBOUND_ID = int(os.getenv("INBOUND_ID", 1))

if not TOKEN:
    raise Exception("❌ BOT_TOKEN НЕ НАЙДЕН")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# =========================
# 🧠 ПАМЯТЬ
# =========================
users_vpn = {}
panel_cookie = None

# =========================
# 🔌 ЛОГИН В ПАНЕЛЬ
# =========================
async def panel_login():
    global panel_cookie

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{PANEL_URL}/login",
            data={"username": PANEL_LOGIN, "password": PANEL_PASSWORD}
        ) as resp:
            panel_cookie = resp.cookies

# =========================
# ⚡ СОЗДАНИЕ VPN
# =========================
async def create_vpn(user_id):
    global panel_cookie

    if not panel_cookie:
        await panel_login()

    client_id = str(uuid.uuid4())
    email = str(user_id)

    payload = {
        "id": INBOUND_ID,
        "settings": {
            "clients": [
                {
                    "id": client_id,
                    "email": email,
                    "limitIp": 2,
                    "totalGB": 50,
                    "expiryTime": 0,
                    "enable": True
                }
            ]
        }
    }

    async with aiohttp.ClientSession(cookies=panel_cookie) as session:
        async with session.post(
            f"{PANEL_URL}/panel/api/inbounds/addClient",
            json=payload
        ) as resp:
            data = await resp.json()

            if not data.get("success"):
                raise Exception("❌ Ошибка панели")

    # формируем ссылку (пример)
    vpn_link = f"{PANEL_URL}/sub/{client_id}"

    return vpn_link

# =========================
# 📌 МЕНЮ
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
    await message.answer(
        "🚀 Moonlight VPN\n\nВыберите действие:",
        reply_markup=main_menu()
    )

# =========================
# 🔐 VPN
# =========================
@dp.callback_query_handler(lambda c: c.data == "vpn")
async def vpn(call: types.CallbackQuery):
    uid = call.from_user.id

    if uid not in users_vpn:
        await call.message.answer(
            "❌ У вас нет VPN\nКупите подписку",
            reply_markup=back_menu()
        )
    else:
        await call.message.answer(
            f"🔐 Ваш VPN:\n{users_vpn[uid]}",
            reply_markup=back_menu()
        )

# =========================
# 💰 ОПЛАТА (тест выдачи)
# =========================
@dp.callback_query_handler(lambda c: c.data == "pay")
async def pay(call: types.CallbackQuery):
    uid = call.from_user.id

    vpn = await create_vpn(uid)
    users_vpn[uid] = vpn

    await call.message.answer(
        f"✅ VPN выдан:\n{vpn}",
        reply_markup=back_menu()
    )

# =========================
# 📱 УСТРОЙСТВА
# =========================
@dp.callback_query_handler(lambda c: c.data == "devices")
async def devices(call: types.CallbackQuery):
    await call.message.answer("📱 Скоро...", reply_markup=back_menu())

# =========================
# 👥 РЕФЕРАЛЫ
# =========================
@dp.callback_query_handler(lambda c: c.data == "ref")
async def ref(call: types.CallbackQuery):
    link = f"https://t.me/your_bot?start={call.from_user.id}"
    await call.message.answer(link, reply_markup=back_menu())

# =========================
# 🆘 ПОМОЩЬ
# =========================
@dp.callback_query_handler(lambda c: c.data == "help")
async def help_cmd(call: types.CallbackQuery):
    await call.message.answer("🆘 Поддержка: @your_support", reply_markup=back_menu())

# =========================
# 🚀 ЗАПУСК
# =========================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
