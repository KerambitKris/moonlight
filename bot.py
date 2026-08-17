import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.utils import executor

# =========================
# 🔐 ПЕРЕМЕННЫЕ (RAILWAY)
# =========================
TOKEN = os.getenv("BOT_TOKEN")
DONATE_URL = os.getenv("DA_URL")

if not TOKEN:
    raise Exception("❌ BOT_TOKEN не найден в переменных")

if not DONATE_URL:
    raise Exception("❌ DA_URL не найден в переменных")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# =========================
# 📌 INLINE МЕНЮ
# =========================
def main_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🔐 Мой VPN", callback_data="vpn"),
        InlineKeyboardButton("🌍 Серверы", callback_data="servers"),
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        InlineKeyboardButton("💰 Пополнить", callback_data="pay"),
    )
    return kb


# =========================
# 📌 НИЖНЯЯ КНОПКА
# =========================
def back_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🏠 В меню"))
    return kb


# =========================
# 🚀 START
# =========================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "🔐 Moonlight VPN\n\nВыберите действие:",
        reply_markup=main_menu()
    )


# =========================
# 🏠 В МЕНЮ
# =========================
@dp.message_handler(lambda m: m.text == "🏠 В меню")
async def back_to_menu(message: types.Message):
    await message.answer(
        "🏠 Главное меню:",
        reply_markup=main_menu()
    )


# =========================
# 👤 ПРОФИЛЬ
# =========================
@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile(call: types.CallbackQuery):
    text = (
        "👤 Профиль\n\n"
        "Баланс: 0₽\n"
        "Тариф: ❌ Нет активной подписки\n"
        f"ID: {call.from_user.id}"
    )

    await call.message.answer(text, reply_markup=back_menu())
    await call.answer()


# =========================
# 💰 ОПЛАТА
# =========================
@dp.callback_query_handler(lambda c: c.data == "pay")
async def pay(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💳 Оплатить", url=DONATE_URL)
    )

    await call.message.answer(
        "💰 Пополнение баланса\n\nПерейдите по кнопке:",
        reply_markup=kb
    )
    await call.answer()


# =========================
# 🌍 СЕРВЕРЫ
# =========================
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
    await call.answer()


# =========================
# 🔐 МОЙ VPN
# =========================
@dp.callback_query_handler(lambda c: c.data == "vpn")
async def vpn(call: types.CallbackQuery):
    await call.message.answer(
        "🔐 У вас нет активного VPN.\n\nПополните баланс.",
        reply_markup=back_menu()
    )
    await call.answer()


# =========================
# 🚀 ЗАПУСК
# =========================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
