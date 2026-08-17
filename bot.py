import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

TOKEN = "ТВОЙ_BOT_TOKEN"
DONATE_URL = "https://www.donationalerts.com/r/smertelobed0"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# -------------------------
# 📌 ГЛАВНОЕ МЕНЮ (INLINE)
# -------------------------
def main_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🔐 Мой VPN", callback_data="vpn"),
        InlineKeyboardButton("🌍 Серверы", callback_data="servers"),
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        InlineKeyboardButton("💰 Пополнить", callback_data="pay"),
    )
    return kb

# -------------------------
# 📌 КНОПКА НАЗАД (REPLY)
# -------------------------
def back_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🏠 В меню"))
    return kb

# -------------------------
# 🚀 START
# -------------------------
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer(
        "🔐 Moonlight VPN\n\nВыберите действие:",
        reply_markup=main_menu()
    )

# -------------------------
# 🏠 В МЕНЮ
# -------------------------
@dp.message_handler(lambda msg: msg.text == "🏠 В меню")
async def back(msg: types.Message):
    await msg.answer(
        "🏠 Главное меню:",
        reply_markup=main_menu()
    )

# -------------------------
# 👤 ПРОФИЛЬ
# -------------------------
@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile(call: types.CallbackQuery):
    await call.message.answer(
        f"👤 Профиль\n\n"
        f"Баланс: 0₽\n"
        f"Тариф: ❌ Нет активной подписки\n"
        f"ID: {call.from_user.id}",
        reply_markup=back_menu()
    )

# -------------------------
# 💰 ОПЛАТА
# -------------------------
@dp.callback_query_handler(lambda c: c.data == "pay")
async def pay(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("💳 Оплатить", url=DONATE_URL)
    )

    await call.message.answer(
        "💰 Пополнение баланса\n\n"
        "Нажми кнопку ниже для оплаты:",
        reply_markup=kb
    )

# -------------------------
# 🌍 СЕРВЕРЫ
# -------------------------
@dp.callback_query_handler(lambda c: c.data == "servers")
async def servers(call: types.CallbackQuery):
    text = """⚡ Автовыбор (обычные VPN)

🇰🇿 Казахстан
🇷🇺 Россия
🇳🇱 Нидерланды

⚡ Автовыбор (обход блокировок)

🇩🇪 Обход 1 — Германия
🇩🇪 Обход 2 — Германия
🇩🇪 Обход 3 — Германия
"""
    await call.message.answer(text, reply_markup=back_menu())

# -------------------------
# 🔐 МОЙ VPN
# -------------------------
@dp.callback_query_handler(lambda c: c.data == "vpn")
async def vpn(call: types.CallbackQuery):
    await call.message.answer(
        "🔐 У тебя нет активного VPN.\n\nПополни баланс для покупки.",
        reply_markup=back_menu()
    )

# -------------------------
# 🚀 ЗАПУСК
# -------------------------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
