=========================================

🚀 MOONLIGHT VPN BOT (FIXED & WORKING)

=========================================

import os
import uuid
import logging
import aiohttp
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiohttp import web

=========================

🔐 ENV

=========================

TOKEN = os.getenv("BOT_TOKEN")
PANEL_URL = os.getenv("PANEL_URL")
PANEL_LOGIN = os.getenv("PANEL_LOGIN")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD")
INBOUND_ID = int(os.getenv("INBOUND_ID", 1))

if not TOKEN:
raise Exception("❌ BOT_TOKEN не найден")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

=========================

💰 ТАРИФЫ

=========================

TARIFFS = {
"5": {"days": 5, "price": 19},
"14": {"days": 14, "price": 49},
"30": {"days": 30, "price": 99},
"60": {"days": 60, "price": 189},
"90": {"days": 90, "price": 249},
"180": {"days": 180, "price": 439},
"365": {"days": 365, "price": 799},
}

=========================

🧠 ПАМЯТЬ (потом заменишь на БД)

=========================

users_balance = {}
users_vpn = {}

=========================

🔌 ПАНЕЛЬ LOGIN

=========================

panel_cookie = None

async def panel_login():
global panel_cookie
async with aiohttp.ClientSession() as session:
async with session.post(
f"{PANEL_URL}/login",
data={"username": PANEL_LOGIN, "password": PANEL_PASSWORD}
) as resp:
panel_cookie = resp.cookies

=========================

⚡ СОЗДАНИЕ VPN

=========================

async def create_vpn(user_id):
global panel_cookie

if not panel_cookie:
    await panel_login()

client_id = str(uuid.uuid4())

payload = {
    "id": INBOUND_ID,
    "settings": {
        "clients": [
            {
                "id": client_id,
                "email": str(user_id),
                "limitIp": 2,
                "totalGB": 0,
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
            raise Exception("❌ Панель не приняла клиента")

return f"{PANEL_URL}/sub/{client_id}"

=========================

📌 МЕНЮ

=========================

def main_menu():
kb = InlineKeyboardMarkup(row_width=1)
kb.add(
InlineKeyboardButton("🚀 Мой VPN", callback_data="vpn"),
InlineKeyboardButton("💰 Купить", callback_data="pay"),
InlineKeyboardButton("📱 Устройства", callback_data="devices"),
InlineKeyboardButton("🆘 Помощь", callback_data="help"),
)
return kb

=========================

🚀 START

=========================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
uid = message.from_user.id
users_balance.setdefault(uid, 0)

await message.answer("🚀 Moonlight VPN", reply_markup=main_menu())

=========================

🔐 VPN

=========================

@dp.callback_query_handler(lambda c: c.data == "vpn")
async def vpn(call: types.CallbackQuery):
uid = call.from_user.id
balance = users_balance.get(uid, 0)

if uid not in users_vpn:
    text = f"❌ Нет VPN\nБаланс: {balance}₽"
else:
    vpn = users_vpn[uid]
    text = f"""💎 VPN активен

Баланс: {balance}₽
До: {vpn['expire'].strftime("%d.%m.%Y")}

🔐 {vpn['key']}"""

await call.message.answer(text, reply_markup=main_menu())

=========================

💰 ТАРИФЫ

=========================

@dp.callback_query_handler(lambda c: c.data == "pay")
async def pay(call: types.CallbackQuery):
kb = InlineKeyboardMarkup(row_width=1)

for key, t in TARIFFS.items():
    kb.add(
        InlineKeyboardButton(
            f"{t['days']} дней — {t['price']}₽",
            callback_data=f"buy_{key}"
        )
    )

await call.message.answer("💰 Выберите тариф:", reply_markup=kb)

=========================

🛒 ПОКУПКА

=========================

@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def buy(call: types.CallbackQuery):
uid = call.from_user.id
tariff_id = call.data.split("_")[1]

tariff = TARIFFS[tariff_id]
price = tariff["price"]
days = tariff["days"]

balance = users_balance.get(uid, 0)

if balance < price:
    await call.message.answer(
        f"❌ Недостаточно средств\n\nНужно: {price}₽\nУ вас: {balance}₽"
    )
    return

users_balance[uid] -= price

if uid not in users_vpn:
    vpn = await create_vpn(uid)
    users_vpn[uid] = {
        "key": vpn,
        "expire": datetime.now() + timedelta(days=days)
    }
else:
    users_vpn[uid]["expire"] += timedelta(days=days)

await call.message.answer(
    f"✅ Активировано {days} дней\n\n🔐 {users_vpn[uid]['key']}"
)

=========================

🌐 DONATION ALERTS

=========================

async def donate_webhook(request):
data = await request.json()

try:
    username = data["data"]["username"]
    amount = int(data["data"]["amount"])

    user_id = int(username)

    users_balance[user_id] = users_balance.get(user_id, 0) + amount

    await bot.send_message(
        user_id,
        f"💰 Пополнение: {amount}₽\nБаланс: {users_balance[user_id]}₽"
    )

except Exception as e:
    print("Webhook error:", e)

return web.Response(text="ok")

=========================

🚀 ЗАПУСК

=========================

if name == "main":
app = web.Application()
app.router.add_post("/donate", donate_webhook)

dp.loop.create_task(web._run_app(app, port=8080))
executor.start_polling(dp, skip_updates=True)
