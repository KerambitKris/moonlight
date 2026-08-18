import os
import uuid
import logging
import aiohttp
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

TOKEN = os.getenv("BOT_TOKEN")
PANEL_URL = os.getenv("PANEL_URL")
PANEL_LOGIN = os.getenv("PANEL_LOGIN")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD")
INBOUND_ID = int(os.getenv("INBOUND_ID", 1))

if not TOKEN:
raise Exception("BOT_TOKEN not found")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

TARIFFS = {
"5": {"days": 5, "price": 19},
"14": {"days": 14, "price": 49},
"30": {"days": 30, "price": 99},
"60": {"days": 60, "price": 189},
"90": {"days": 90, "price": 249},
"180": {"days": 180, "price": 439},
"365": {"days": 365, "price": 799},
}

👉 ТУТ ТЫ САМ ДОБАВЛЯЕШЬ ПРОМО

promo_codes = {
"MEOW": {"amount": 30, "uses": 1},
"VIP100": {"amount": 100, "uses": 5},
}

users_balance = {}
users_vpn = {}
waiting_promo = set()

panel_cookie = None

async def panel_login():
global panel_cookie
async with aiohttp.ClientSession() as session:
async with session.post(
f"{PANEL_URL}/login",
data={"username": PANEL_LOGIN, "password": PANEL_PASSWORD}
) as resp:
panel_cookie = resp.cookies

async def create_vpn(user_id, days):
global panel_cookie

if not panel_cookie:
    await panel_login()

client_id = str(uuid.uuid4())
expiry = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)

payload = {
    "id": INBOUND_ID,
    "settings": {
        "clients": [
            {
                "id": client_id,
                "email": str(user_id),
                "limitIp": 2,
                "totalGB": 0,
                "expiryTime": expiry,
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
            raise Exception("Panel error")

return f"{PANEL_URL}/sub/{client_id}"

def main_menu():
kb = InlineKeyboardMarkup(row_width=1)
kb.add(
InlineKeyboardButton("🚀 Мой VPN", callback_data="vpn"),
InlineKeyboardButton("💰 Купить", callback_data="buy"),
InlineKeyboardButton("🎁 Промокод", callback_data="promo"),
)
return kb

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
uid = msg.from_user.id
users_balance.setdefault(uid, 0)

await msg.answer(
    f"Баланс: {users_balance[uid]}₽",
    reply_markup=main_menu()  # 👉 кнопки под сообщением бота
)

@dp.callback_query_handler(lambda c: c.data == "vpn")
async def vpn(call: types.CallbackQuery):
uid = call.from_user.id

if uid in users_vpn:
    vpn = users_vpn[uid]
    text = f"VPN до {vpn['expire'].strftime('%d.%m.%Y')}\n{vpn['key']}"
else:
    text = "У вас нет VPN"

await call.message.answer(text, reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == "buy")
async def buy(call: types.CallbackQuery):
kb = InlineKeyboardMarkup(row_width=2)

for key, t in TARIFFS.items():
    kb.insert(
        InlineKeyboardButton(
            f"{t['days']}д - {t['price']}₽",
            callback_data=f"buy_{key}"
        )
    )

await call.message.answer("Выберите тариф:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def process_buy(call: types.CallbackQuery):
uid = call.from_user.id
plan = call.data.split("_")[1]
tariff = TARIFFS[plan]

if users_balance.get(uid, 0) < tariff["price"]:
    await call.message.answer("Недостаточно средств", reply_markup=main_menu())
    return

users_balance[uid] -= tariff["price"]

if uid not in users_vpn:
    link = await create_vpn(uid, tariff["days"])
    users_vpn[uid] = {
        "key": link,
        "expire": datetime.now() + timedelta(days=tariff["days"])
    }
else:
    users_vpn[uid]["expire"] += timedelta(days=tariff["days"])

await call.message.answer("VPN активирован", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == "promo")
async def promo(call: types.CallbackQuery):
waiting_promo.add(call.from_user.id)
await call.message.answer("Введи промокод:")

@dp.message_handler()
async def enter_promo(msg: types.Message):
uid = msg.from_user.id

if uid not in waiting_promo:
    return

waiting_promo.remove(uid)
code = msg.text.upper()

if code in promo_codes:
    promo = promo_codes[code]

    users_balance[uid] = users_balance.get(uid, 0) + promo["amount"]
    promo["uses"] -= 1

    await msg.answer(f"+{promo['amount']}₽ начислено", reply_markup=main_menu())

    if promo["uses"] <= 0:
        del promo_codes[code]
else:
    await msg.answer("Неверный промокод", reply_markup=main_menu())

if name == "main":
executor.start_polling(dp, skip_updates=True)
