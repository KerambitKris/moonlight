import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton


TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()


def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔐 Мой VPN",
                    callback_data="vpn"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💎 Тарифы",
                    callback_data="plans"
                ),
                InlineKeyboardButton(
                    text="👤 Профиль",
                    callback_data="profile"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌍 Серверы",
                    callback_data="servers"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📖 Помощь",
                    callback_data="help"
                )
            ],
        ]
    )


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "<b>🔐 MYVPN</b>\n\n"
        "Добро пожаловать!\n\n"
        "Быстрый и стабильный VPN "
        "для ваших устройств.\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📡 Статус: ⚪ Не подключён\n"
        "🌍 Сервер: 🇩🇪 Германия\n"
        "💎 Тариф: Бесплатный\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Выберите действие:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


async def main():
    print("🔐 MyVPN Bot запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
