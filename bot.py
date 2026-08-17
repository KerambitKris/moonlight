import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ================= МЕНЮ =================

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🔐 Мой VPN", callback_data="vpn")],
        [InlineKeyboardButton("🌍 Серверы", callback_data="servers")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("💰 Пополнить", callback_data="pay")]
    ])

# ================= START =================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "🔐 Moonlight VPN\n\nВыберите действие:",
        reply_markup=main_menu()
    )

# ================= ПРОФИЛЬ =================

@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile(call: types.CallbackQuery):
    await call.message.edit_text(
f"""👤 Профиль

Баланс: 0₽
Тариф: ❌ Нет активной подписки
ID: {call.from_user.id}""",
        reply_markup=main_menu()
    )

# ================= VPN =================

@dp.callback_query_handler(lambda c: c.data == "vpn")
async def vpn(call: types.CallbackQuery):
    await call.message.edit_text(
        "🔐 Здесь будет ваш VPN",
        reply_markup=main_menu()
    )

# ================= СЕРВЕРА =================

@dp.callback_query_handler(lambda c: c.data == "servers")
async def servers(call: types.CallbackQuery):
    await call.message.edit_text(
"""⚡ Автовыбор (обычные VPN)

🇰🇿 Казахстан
🇷🇺 Россия
🇳🇱 Нидерланды

⚡ Автовыбор (обход блокировок)

🇩🇪 Обход 1 — Германия
🇩🇪 Обход 2 — Германия
🇩🇪 Обход 3 — Германия""",
        reply_markup=main_menu()
    )

# ================= ПОПОЛНЕНИЕ =================

@dp.callback_query_handler(lambda c: c.data == "pay")
async def pay(call: types.CallbackQuery):
    await call.message.edit_text(
        "💰 Пополнение пока в разработке",
        reply_markup=main_menu()
    )

# ================= ЗАПУСК =================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
