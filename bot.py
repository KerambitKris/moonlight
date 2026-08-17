import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import os

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ======================
# REPLY КНОПКА (ТОЛЬКО МЕНЮ)
# ======================
main_reply = ReplyKeyboardMarkup(resize_keyboard=True)
main_reply.add(KeyboardButton("🏠 Главное меню"))

# ======================
# INLINE МЕНЮ
# ======================
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔐 Мой VPN", callback_data="vpn"),
        InlineKeyboardButton("🌍 Серверы", callback_data="servers"),
    )
    kb.add(
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        InlineKeyboardButton("💰 Пополнить", callback_data="pay"),
    )
    return kb

# ======================
# /start
# ======================
@dp.message_handler(commands=["start"])
@dp.message_handler(lambda m: m.text == "🏠 Главное меню")
async def start(message: types.Message):
    await message.answer(
        "🔐 Moonlight VPN\n\nВыберите действие:",
        reply_markup=main_menu()
    )

# ======================
# ПРОФИЛЬ
# ======================
@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile(call: types.CallbackQuery):
    text = (
        "👤 Профиль\n\n"
        f"Баланс: 0₽\n"
        f"Тариф: ❌ Нет активной подписки\n"
        f"ID: {call.from_user.id}"
    )
    await call.message.edit_text(text, reply_markup=main_menu())

# ======================
# VPN
# ======================
@dp.callback_query_handler(lambda c: c.data == "vpn")
async def vpn(call: types.CallbackQuery):
    await call.message.edit_text(
        "🔐 Ваш VPN будет тут",
        reply_markup=main_menu()
    )

# ======================
# СЕРВЕРЫ
# ======================
@dp.callback_query_handler(lambda c: c.data == "servers")
async def servers(call: types.CallbackQuery):
    text = (
        "⚡ Автовыбор (обычные VPN)\n\n"
        "🇰🇿 Казахстан\n"
        "🇷🇺 Россия\n"
        "🇳🇱 Нидерланды\n\n\n"
        "⚡ Автовыбор (обход блокировок)\n\n"
        "🇩🇪 Обход 1 — Германия\n"
        "🇩🇪 Обход 2 — Германия\n"
        "🇩🇪 Обход 3 — Германия"
    )
    await call.message.edit_text(text, reply_markup=main_menu())

# ======================
# ПОПОЛНЕНИЕ
# ======================
@dp.callback_query_handler(lambda c: c.data == "pay")
async def pay(call: types.CallbackQuery):
    await call.message.edit_text(
        "💰 Введите сумму пополнения:",
        reply_markup=main_menu()
    )

# ======================
# ЗАПУСК
# ======================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
