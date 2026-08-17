import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()


# =========================
# КНОПКИ
# =========================

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


def back():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="home")]
        ]
    )


def buy_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 1 месяц — 199 ₽", callback_data="buy_1")],
            [InlineKeyboardButton(text="💳 3 месяца — 499 ₽", callback_data="buy_3")],
            [InlineKeyboardButton(text="💳 12 месяцев — 1499 ₽", callback_data="buy_12")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="home")]
        ]
    )


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):
    text = (
        "🔐 <b>Moonlight VPN</b>\n\n"
        "Добро пожаловать в Moonlight VPN!\n\n"
        "Быстрый и стабильный VPN для ваших устройств, вы сможете подключаться "
        "ко всем ресурсам в интернете, даже запрещенным.\n\n"
        "⭐️ Новостной канал — @moonlight_vpn_news\n"
        "⭐️ Связь и техническая поддержка — @mtfunit\n\n"
        "Выберите действие:"
    )

    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")


# =========================
# ГЛАВНАЯ
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
        "📡 Статус: Не подключён\n"
        "🌍 Сервер: Германия\n"
        "💎 Тариф: Бесплатный\n\n"
        "Купите подписку чтобы получить доступ"
    )

    await callback.message.edit_text(text, reply_markup=back(), parse_mode="HTML")
    await callback.answer()


# =========================
# ПОКУПКА
# =========================

@dp.callback_query(F.data == "buy")
async def buy(callback: CallbackQuery):
    await callback.message.edit_text(
        "💎 Выберите тариф:",
        reply_markup=buy_menu()
    )
    await callback.answer()


# =========================
# ВЫБОР ТАРИФА
# =========================

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery):
    prices = {
        "buy_1": ("1 месяц", 19900),
        "buy_3": ("3 месяца", 49900),
        "buy_12": ("12 месяцев", 149900),
    }

    plan, amount = prices[callback.data]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Moonlight VPN — {plan}",
        description=f"Подписка VPN ({plan})",
        payload=f"vpn_{plan}",
        provider_token=os.getenv("PAYMENT_TOKEN"),
        currency="RUB",
        prices=[{"label": plan, "amount": amount}],
        start_parameter="vpn-sub"
    )

    await callback.answer()


# =========================
# ОБРАБОТКА ОПЛАТЫ
# =========================

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    await message.answer("✅ Оплата прошла! VPN будет выдан позже (в разработке)")


# =========================
# ПРОФИЛЬ
# =========================

@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    user = callback.from_user

    text = (
        "👤 <b>Профиль</b>\n\n"
        f"ID: <code>{user.id}</code>\n"
        "Тариф: Бесплатный"
    )

    await callback.message.edit_text(text, reply_markup=back(), parse_mode="HTML")
    await callback.answer()


# =========================
# СЕРВЕРЫ
# =========================

@dp.callback_query(F.data == "servers")
async def servers(callback: CallbackQuery):
    text = (
        "🌍 Серверы\n\n"
        "🇩🇪 Германия\n"
        "🇳🇱 Нидерланды\n"
        "🇫🇮 Финляндия"
    )

    await callback.message.edit_text(text, reply_markup=back())
    await callback.answer()


# =========================
# ЗАПУСК
# =========================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
