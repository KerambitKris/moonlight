import asyncio
import os
import random

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()


# =======================
# КНОПКИ
# =======================

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔐 Мой VPN", callback_data="vpn")],
            [
                InlineKeyboardButton(text="💎 Купить", callback_data="buy"),
                InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            ],
            [InlineKeyboardButton(text="🌍 Серверы", callback_data="servers")],
        ]
    )


def back_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="home")]
        ]
    )


# =======================
# START
# =======================

@dp.message(CommandStart())
async def start(message: Message):
    text = (
        "🔐 Moonlight VPN\n\n"
        "👋 Добро пожаловать в Moonlight VPN!\n\n"
        "⚡ Быстрый и стабильный VPN для ваших устройств, вы сможете подключаться ко всем ресурсам в интернете, даже запрещенным.\n\n"
        "⭐️ Новостной канал — @moonlight_vpn_news\n"
        "⭐️ Связь и техническая поддержка — @mtfunit\n\n"
        "👇 Выберите действие:"
    )

    await message.answer(text, reply_markup=main_menu())


# =======================
# ГЛАВНОЕ МЕНЮ
# =======================

@dp.callback_query(F.data == "home")
async def home(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔐 Moonlight VPN\n\n👇 Выберите действие:",
        reply_markup=main_menu()
    )
    await callback.answer()


# =======================
# ШКАЛА НАГРУЗКИ
# =======================

def load_bar(percent):
    filled = int(percent / 10)
    empty = 10 - filled

    bar = "█" * filled + "░" * empty

    if percent < 40:
        color = "🟢"
    elif percent < 70:
        color = "🟡"
    else:
        color = "🔴"

    return f"{color} [{bar}] {percent}%"


# =======================
# СЕРВЕРА
# =======================

@dp.callback_query(F.data == "servers")
async def servers(callback: CallbackQuery):
    load = random.randint(15, 90)

    text = (
        "🌍 Здесь вы можете посмотреть доступные сервера и их загруженность чтобы выбрать самый оптимальный сервер.\n\n"
        "🇩🇪 Германия\n"
        f"{load_bar(load)}"
    )

    await callback.message.edit_text(text, reply_markup=back_menu())
    await callback.answer()


# =======================
# КУПИТЬ
# =======================

@dp.callback_query(F.data == "buy")
async def buy(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 1 месяц — 199₽", callback_data="buy_1")],
            [InlineKeyboardButton(text="💳 3 месяца — 499₽", callback_data="buy_3")],
            [InlineKeyboardButton(text="💳 12 месяцев — 1499₽", callback_data="buy_12")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="home")]
        ]
    )

    await callback.message.edit_text("💎 Выберите тариф:", reply_markup=keyboard)
    await callback.answer()


# =======================
# МОЙ VPN
# =======================

@dp.callback_query(F.data == "vpn")
async def vpn(callback: CallbackQuery):
    text = (
        "🔐 Мой VPN\n\n"
        "📡 Статус: Не подключён\n"
        "🌍 Сервер: Германия\n"
        "💎 Тариф: Бесплатный"
    )

    await callback.message.edit_text(text, reply_markup=back_menu())
    await callback.answer()


# =======================
# ПРОФИЛЬ
# =======================

@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    user = callback.from_user

    text = (
        "👤 Профиль\n\n"
        f"ID: {user.id}\n"
        "Тариф: Бесплатный"
    )

    await callback.message.edit_text(text, reply_markup=back_menu())
    await callback.answer()


# =======================
# ЗАПУСК
# =======================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
