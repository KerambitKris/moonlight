import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.utils import executor

# ===== ЛОГИ =====
logging.basicConfig(level=logging.INFO)

# ===== ENV =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
DA_URL = os.getenv("DA_URL")

if not BOT_TOKEN:
    raise Exception("❌ BOT_TOKEN не задан")

if not DA_URL:
    DA_URL = "https://www.donationalerts.com/"

# ===== БОТ =====
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ===== REPLY (только меню) =====
menu_kb = ReplyKeyboardMarkup(resize_keyboard=True)
menu_kb.add(KeyboardButton("🏠 Главное меню"))

# ===== INLINE =====
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔐 Мой VPN", callback_data="vpn"),
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
    )
    kb.add(
        InlineKeyboardButton("💳 Пополнить", callback_data="pay"),
        InlineKeyboardButton("🌍 Серверы", callback_data="servers"),
    )
    return kb


def back_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🏠 В главное меню", callback_data="menu"))
    return kb


def pay_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 Оплатить", url=DA_URL))
    kb.add(InlineKeyboardButton("🏠 В меню", callback_data="menu"))
    return kb


# ===== START =====
@dp.message_handler(commands=["start"])
@dp.message_handler(lambda m: m.text == "🏠 Главное меню")
async def start(message: types.Message):
    await message.answer(
        "🔐 Moonlight VPN\n\nВыберите действие:",
        reply_markup=menu_kb
    )

    await message.answer(
        "👇 Управление:",
        reply_markup=main_menu()
    )


# ===== CALLBACK =====
@dp.callback_query_handler(lambda c: True)
async def callbacks(call: types.CallbackQuery):

    # ===== ГЛАВНОЕ МЕНЮ =====
    if call.data == "menu":
        await call.message.edit_text(
            "👇 Главное меню:",
            reply_markup=main_menu()
        )

    # ===== ПРОФИЛЬ =====
    elif call.data == "profile":
        user_id = call.from_user.id

        text = f"""👤 Профиль

Баланс: 0₽
Тариф: ❌ Нет активной подписки
ID: {user_id}
"""

        await call.message.edit_text(
            text,
            reply_markup=back_menu()
        )

    # ===== ОПЛАТА =====
    elif call.data == "pay":
        await call.message.edit_text(
            "💳 Пополнение\n\nНажмите кнопку ниже:",
            reply_markup=pay_menu()
        )

    # ===== СЕРВЕРА =====
    elif call.data == "servers":
        text = """🌍 Серверы

⚡ Автовыбор (обычные VPN)

🇰🇿 Казахстан
🇷🇺 Россия
🇳🇱 Нидерланды

──────────────

⚡ Автовыбор (обход блокировок)

🇩🇪 Обход 1 — Германия
🇩🇪 Обход 2 — Германия
🇩🇪 Обход 3 — Германия
"""

        await call.message.edit_text(
            text,
            reply_markup=back_menu()
        )

    # ===== МОЙ VPN =====
    elif call.data == "vpn":
        await call.message.edit_text(
            "🔐 Здесь будет выдача VPN (подключим позже)",
            reply_markup=back_menu()
        )

    await call.answer()


# ===== ЗАПУСК =====
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
