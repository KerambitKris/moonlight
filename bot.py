import os
import uuid
import logging
import aiohttp
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

# ===== НАСТРОЙКИ =====
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

# ===== ТАРИФЫ =====
TARIFFS = {
    "5": {"days": 5, "price": 19},
    "14": {"days": 14, "price": 49},
    "30": {"days": 30, "price": 99},
}

# ===== ПРОМОКОДЫ (РЕДАКТИРУЕШЬ ТУТ) =====
promo_codes = {
    "FREE30": {"amount": 30, "uses": 5},
    "VIP100": {"amount": 100, "uses": 2},
}

# ===== ДАННЫЕ =====
users_balance = {}
users_vpn = {}
waiting_promo = set()

panel_cookie = None

# ===== МЕНЮ (КАК У KYRA) =====
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row(KeyboardButton("🚀 Подключиться"))
    kb.row(
        KeyboardButton("💳 Купить/Продлить"),
        KeyboardButton("📱 Мои устройства")
    )
    kb.row(
        KeyboardButton("🎁 Промокод"),
        KeyboardButton("💰 Баланс")
    )
    kb.row(KeyboardButton("🆘 Помощь"))

    return kb

# ===== ПАНЕЛЬ =====
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

# ===== КОМАНДЫ =====
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    uid = msg.from_user.id
    users_balance.setdefault(uid, 0)

    await msg.answer(
        "Добро пожаловать в VPN\n\n💰 Баланс: {} ₽".format(users_balance[uid]),
        reply_markup=main_menu()
    )

# ===== КНОПКИ =====
@dp.message_handler(lambda m: m.text == "💰 Баланс")
async def balance(msg: types.Message):
    uid = msg.from_user.id
    await msg.answer(f"Баланс: {users_balance.get(uid, 0)} ₽")

@dp.message_handler(lambda m: m.text == "🎁 Промокод")
async def promo(msg: types.Message):
    waiting_promo.add(msg.from_user.id)
    await msg.answer("Введи промокод:")

@dp.message_handler(lambda m: m.text == "🚀 Подключиться")
async def connect(msg: types.Message):
    uid = msg.from_user.id

    if uid not in users_vpn:
        await msg.answer("У тебя нет VPN")
        return

    vpn = users_vpn[uid]
    await msg.answer(f"Твой ключ:\n{vpn['key']}")

@dp.message_handler(lambda m: m.text == "💳 Купить/Продлить")
async def buy(msg: types.Message):
    text = "Выбери тариф:\n\n"
    for k, t in TARIFFS.items():
        text += f"{t['days']} дней - {t['price']} ₽\n"

    await msg.answer(text)
    await msg.answer("Напиши число дней (например 30)")

@dp.message_handler(lambda m: m.text.isdigit())
async def process_buy(msg: types.Message):
    uid = msg.from_user.id
    plan = msg.text

    if plan not in TARIFFS:
        return

    tariff = TARIFFS[plan]

    if users_balance.get(uid, 0) < tariff["price"]:
        await msg.answer("Недостаточно средств")
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

    await msg.answer("VPN активирован")

@dp.message_handler(lambda m: m.text == "📱 Мои устройства")
async def devices(msg: types.Message):
    await msg.answer("Функция пока не реализована")

@dp.message_handler(lambda m: m.text == "🆘 Помощь")
async def help_cmd(msg: types.Message):
    await msg.answer("Напиши администратору")

# ===== ВВОД ПРОМО =====
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

        await msg.answer(f"+{promo['amount']} ₽ начислено")

        if promo["uses"] <= 0:
            del promo_codes[code]
    else:
        await msg.answer("Неверный промокод")

# ===== ЗАПУСК =====
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
