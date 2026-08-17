import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# =========================
# КЛАВИАТУРЫ
# =========================

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔐 Мой VPN", callback_data="vpn")],
            [
                InlineKeyboardButton(text="💎 Тарифы", callback_data="plans"),
                InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            ],
            [InlineKeyboardButton(text="🌍 Серверы", callback_data="servers")],
            [InlineKeyboardButton(text="📖 Помощь", callback_data="help")],
        ]
    )


def back():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="home")]
        ]
    )


# =========================
# /start
# =========================

@dp.message(CommandStart())
async def start(message: Message):
    text = (
        "🔐 <b>Moonlight VPN</b>\n\n"
        "Добро пожаловать в Moonlight VPN!\n\n"
        "Быстрый и стабильный VPN для ваших устройств, "
        "вы сможете подключаться ко всем ресурсам в интернете, "
        "даже запрещенным.\n\n"
        "⭐️ Новостной канал — @moonlight_vpn_news\n"
        "⭐️ Связь и техническая поддержка — @mtfunit\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Выберите действие:"
    )

    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")


# =========================
# ГЛАВНОЕ МЕНЮ
# =========================

@dp.callback_query(F.data == "home")
async def home(callback: CallbackQuery):
    await start(callback.message)
    await callback.answer()


# =========================
# МОЙ VPN
# =========================

@dp.callback_query(F.data == "vpn")
async def vpn(callback: CallbackQuery):
    text = (
        "🔐 <b>Мой VPN</b>\n\n"
        "📡 Статус: ⚪ Не подключён\n"
        "🌍 Сервер: 🇩🇪 Германия\n"
        "💎 Тариф: Бесплатный\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "VPN пока не активирован.\n"
        "Купите подписку, чтобы получить доступ."
    )

    await callback.message.edit_text(text, reply_markup=back(), parse_mode="HTML")
    await callback.answer()


# =========================
# ТАРИФЫ
# =========================

@dp.callback_query(F.data == "plans")
async def plans(callback: CallbackQuery):
    text = (
        "💎 <b>Тарифы</b>\n\n"
        "1 месяц — 199 ₽\n"
        "3 месяца — 499 ₽\n"
        "12 месяцев — 1499 ₽\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🚧 Оплата пока в разработке"
    )

    await callback.message.edit_text(text, reply_markup=back(), parse_mode="HTML")
    await callback.answer()


# =========================
# ПРОФИЛЬ
# =========================

@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    user = callback.from_user

    text = (
        "👤 <b>Профиль</b>\n\n"
        f"ID: <code>{user.id}</code>\n\n"
        "💎 Тариф: Бесплатный\n"
        "📅 Доступ: —\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"Имя: {user.first_name}"
    )

    await callback.message.edit_text(text, reply_markup=back(), parse_mode="HTML")
    await callback.answer()


# =========================
# СЕРВЕРЫ
# =========================

@dp.callback_query(F.data == "servers")
async def servers(callback: CallbackQuery):
    text = (
        "🌍 <b>Серверы</b>\n\n"
        "🇩🇪 Германия — 🟢 низкая нагрузка\n"
        "🇳🇱 Нидерланды — 🟢 низкая нагрузка\n"
        "🇫🇮 Финляндия — 🟡 средняя нагрузка\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Выбор сервера будет доступен после покупки."
    )

    await callback.message.edit_text(text, reply_markup=back(), parse_mode="HTML")
    await callback.answer()


# =========================
# ПОМОЩЬ
# =========================

@dp.callback_query(F.data == "help")
async def help_menu(callback: CallbackQuery):
    text = (
        "📖 <b>Помощь</b>\n\n"
        "1. Установите WireGuard\n"
        "2. Получите конфигурацию\n"
        "3. Подключитесь\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🚧 Инструкции скоро появятся"
    )

    await callback.message.edit_text(text, reply_markup=back(), parse_mode="HTML")
    await callback.answer()


# =========================
# ЗАПУСК
# =========================

async def main():
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
