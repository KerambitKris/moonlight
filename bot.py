import os
import uuid
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

================= ENV =================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
raise Exception("BOT_TOKEN not found")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

================= ТАРИФЫ =================

TARIFFS = {
"5": {"days": 5, "price": 19},
"14": {"days": 14, "price": 49},
"30": {"days": 30, "price": 99},
"60": {"days": 60, "price": 189},
"90": {"days": 90, "price": 249},
"180": {"days": 180, "price": 439},
"365": {"days": 365, "price": 799},
}

================= ДАННЫЕ =================

users_balance = {}
users_vpn = {}

================= ПРОМОКОДЫ =================

promo_codes = {
"FREE30": {"amount": 30, "uses": 1},
"VIP100": {"amount": 100, "uses": 3},
}

used_promos = {}  # чтобы 1 человек не юзал 100 раз

================= МЕНЮ =================

def main_menu():
kb = InlineKeyboardMarkup(row_width=1)
kb.add(
InlineKeyboardButton("🚀 Мой VPN", callback_data="vpn"),
InlineKeyboardButton("💰 Купить", callback_data="buy"),
InlineKeyboardButton("🎁 Промокод", callback_data="promo"),
)
return kb

================= СТАРТ =================

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
uid = msg.from_user.id
users_balance.setdefault(uid, 0)

await msg.answer(
    f"👋 Добро пожаловать\nБаланс: {users_balance[uid]}₽",
    reply_markup=main_menu()
)

================= VPN =================

@dp.callback_query_handler(lambda c: c.data == "vpn")
async def vpn(call: types.CallbackQuery):
uid = call.from_user.id

if uid in users_vpn:
    await call.message.answer(f"🔐 Ваш VPN:\n{users_vpn[uid]}")
else:
    await call.message.answer("❌ У вас нет VPN")

================= ТАРИФЫ =================

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

await call.message.answer("💰 Выберите тариф:", reply_markup=kb)

================= ПОКУПКА =================

@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def process_buy(call: types.CallbackQuery):
uid = call.from_user.id
plan = call.data.split("_")[1]

tariff = TARIFFS[plan]

if users_balance.get(uid, 0) < tariff["price"]:
    await call.message.answer("❌ Недостаточно средств")
    return

users_balance[uid] -= tariff["price"]

# выдача VPN (заглушка)
vpn_link = f"https://vpn.example.com/{uuid.uuid4()}"
users_vpn[uid] = vpn_link

await call.message.answer(f"✅ VPN выдан:\n{vpn_link}")

================= ПРОМО =================

@dp.callback_query_handler(lambda c: c.data == "promo")
async def promo(call: types.CallbackQuery):
await call.message.answer("🎁 Введите промокод:")

================= ВВОД ПРОМО =================

@dp.message_handler()
async def enter_promo(msg: types.Message):
uid = msg.from_user.id
code = msg.text.upper()

if code not in promo_codes:
    return

# защита от повторного использования
if uid in used_promos and code in used_promos[uid]:
    await msg.answer("❌ Ты уже использовал этот промокод")
    return

promo = promo_codes[code]

users_balance[uid] = users_balance.get(uid, 0) + promo["amount"]

promo["uses"] -= 1

used_promos.setdefault(uid, set()).add(code)

await msg.answer(f"🎁 +{promo['amount']}₽ начислено
