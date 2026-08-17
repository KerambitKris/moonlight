import asyncio
import os
import random
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# =======================
# ДАННЫЕ
# =======================

users = {}  
# user_id: {balance, sub_until}

promo_codes = {}  
# code: {amount, uses_left}


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
    await message.answer(
        "🔐 Moonlight VPN\n\n"
        "👋 Добро пожаловать в Moonlight VPN!\n\n"
        "⚡ Быстрый и стабильный VPN для ваших устройств.\n\n"
        "👇 Выберите действие:",
        reply_markup=main_menu()
    )


# =======================
# ГЛАВНАЯ
# =======================

@dp.callback_query(F.data == "home")
async def home(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "🔐 Moonlight VPN\n\n👇 Выберите действие:",
        reply_markup=main_menu()
    )
    await callback.answer()


# =======================
# СЕРВЕРА
# =======================

def load_bar(percent):
    filled = int(percent / 10)
    bar = "█" * filled + "░" * (10 - filled)

    if percent < 40:
        color = "🟢"
    elif percent < 70:
        color = "🟡"
    else:
        color = "🔴"

    return f"{color} {percent}%\n[{bar}]"


@dp.callback_query(F.data == "servers")
async def servers(callback: CallbackQuery):
    load = random.randint(10, 100)

    text = (
        "🌍 Доступные сервера:\n\n"
        "🇩🇪 Германия\n"
        f"{load_bar(load)}"
    )

    await callback.message.delete()
    await callback.message.answer(text, reply_markup=back_menu())
    await callback.answer()


# =======================
# ПРОФИЛЬ
# =======================

@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    user_id = callback.from_user.id

    user = users.get(user_id, {"balance": 0, "sub": None})

    balance = user["balance"]

    if user["sub"]:
        tariff = f"До {user['sub']}"
    else:
        tariff = "❌ Нет активной подписки"

    text = (
        "👤 Профиль\n\n"
        f"Баланс: {balance}₽\n\n"
        f"ID: {user_id}\n"
        f"Тариф: {tariff}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Ввести промокод", callback_data="promo")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="home")]
        ]
    )

    await callback.message.delete()
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


# =======================
# ПРОМОКОД ВВОД
# =======================

waiting_promo = {}

@dp.callback_query(F.data == "promo")
async def promo_enter(callback: CallbackQuery):
    waiting_promo[callback.from_user.id] = True

    await callback.message.answer("Введите промокод:")
    await callback.answer()


@dp.message()
async def handle_promo(message: Message):
    user_id = message.from_user.id

    if not waiting_promo.get(user_id):
        return

    code = message.text.upper()

    if code in promo_codes:
        promo = promo_codes[code]

        if promo["uses_left"] > 0:
            users.setdefault(user_id, {"balance": 0, "sub": None})

            users[user_id]["balance"] += promo["amount"]
            promo["uses_left"] -= 1

            await message.answer(f"✅ Вы получили {promo['amount']}₽!")
        else:
            await message.answer("❌ Промокод закончился")
    else:
        await message.answer("❌ Неверный промокод")

    waiting_promo[user_id] = False


# =======================
# АДМИН ПРОМОКОД
# =======================

ADMIN_ID = 123456789  # ВСТАВЬ СВОЙ ID

@dp.message(Command("addpromo"))
async def add_promo(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        _, code, amount, uses = message.text.split()

        promo_codes[code.upper()] = {
            "amount": int(amount),
            "uses_left": int(uses)
        }

        await message.answer("✅ Промокод создан")

    except:
        await message.answer("❌ Формат: /addpromo CODE 300 10")


# =======================
# ПОКУПКА
# =======================

@dp.callback_query(F.data == "buy")
async def buy(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 1 месяц — 199₽", callback_data="sub_1")],
            [InlineKeyboardButton(text="💳 3 месяца — 499₽", callback_data="sub_3")],
            [InlineKeyboardButton(text="💳 12 месяцев — 1499₽", callback_data="sub_12")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="home")]
        ]
    )

    await callback.message.delete()
    await callback.message.answer("Выберите тариф:", reply_markup=keyboard)
    await callback.answer()


# =======================
# ПОКУПКА С БАЛАНСА
# =======================

@dp.callback_query(F.data.startswith("sub_"))
async def buy_sub(callback: CallbackQuery):
    user_id = callback.from_user.id

    users.setdefault(user_id, {"balance": 0, "sub": None})

    prices = {
        "sub_1": (199, 30),
        "sub_3": (499, 90),
        "sub_12": (1499, 365)
    }

    price, days = prices[callback.data]
    balance = users[user_id]["balance"]

    if balance >= price:
        users[user_id]["balance"] -= price
        expire = datetime.now() + timedelta(days=days)
        users[user_id]["sub"] = expire.strftime("%d.%m.%Y")

        await callback.message.answer("✅ Подписка активирована!")
    else:
        need = price - balance
        await callback.message.answer(
            f"❌ Недостаточно средств.\nНужно доплатить: {need}₽"
        )

    await callback.answer()


# =======================
# VPN
# =======================

@dp.callback_query(F.data == "vpn")
async def vpn(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "🔐 VPN пока не активирован\n\nКупите подписку",
        reply_markup=back_menu()
    )
    await callback.answer()


# =======================
# ЗАПУСК
# =======================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
