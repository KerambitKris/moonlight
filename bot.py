import asyncio
import time
import random
import aiohttp
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart

BOT_TOKEN = os.getenv("BOT_TOKEN")
DA_TOKEN = os.getenv("DA_TOKEN")
DA_URL = os.getenv("DA_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

users = {}
sessions = {}  # user_id -> {amount, time}

# ========= UI =========

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔐 Мой VPN", callback_data="vpn")],
            [
                InlineKeyboardButton(text="💳 Пополнить", callback_data="topup"),
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

# ========= START =========

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🔐 Moonlight VPN\n\n"
        "👋 Добро пожаловать!\n\n"
        "👇 Выберите действие:",
        reply_markup=main_menu()
    )

# ========= MENU =========

@dp.callback_query(F.data == "home")
async def home(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("👇 Выберите действие:", reply_markup=main_menu())
    await callback.answer()

# ========= PROFILE =========

@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = users.setdefault(user_id, {"balance": 0, "sub": None})

    sub = user["sub"] if user["sub"] else "❌ Нет подписки"

    await callback.message.delete()
    await callback.message.answer(
        f"👤 Профиль\n\n"
        f"Баланс: {user['balance']}₽\n"
        f"ID: {user_id}\n"
        f"Тариф: {sub}",
        reply_markup=back_menu()
    )
    await callback.answer()

# ========= VPN =========

@dp.callback_query(F.data == "vpn")
async def vpn(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "🔐 VPN пока не активирован",
        reply_markup=back_menu()
    )
    await callback.answer()

# ========= SERVERS =========

def load_bar(percent):
    filled = int(percent / 10)
    bar = "█" * filled + "░" * (10 - filled)

    if percent < 40:
        color = "🟢"
    elif percent < 70:
        color = "🟡"
    else:
        color = "🔴"

    return f"{color} [{bar}] {percent}%"


@dp.callback_query(F.data == "servers")
async def servers(callback: CallbackQuery):
    load = random.randint(10, 95)

    await callback.message.delete()
    await callback.message.answer(
        "🌍 Доступные сервера:\n\n"
        "🇩🇪 Германия\n"
        f"{load_bar(load)}",
        reply_markup=back_menu()
    )
    await callback.answer()

# ========= TOPUP =========

@dp.callback_query(F.data == "topup")
async def topup(callback: CallbackQuery):
    user_id = callback.from_user.id

    amount = random.choice([100, 200, 300, 500]) + random.randint(1, 99)

    sessions[user_id] = {
        "amount": amount,
        "time": time.time()
    }

    await callback.message.delete()
    await callback.message.answer(
        f"💳 Оплата\n\n"
        f"Переведи ровно: {amount}₽\n\n"
        f"⚠️ Сумма должна совпадать!\n"
        f"⏱ Время: 5 минут\n\n"
        f"После оплаты подожди 10-30 сек",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить", url=DA_URL)],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="home")]
            ]
        )
    )
    await callback.answer()

# ========= CHECK PAYMENTS =========

async def check_donations():
    url = "https://www.donationalerts.com/api/v1/alerts/donations"

    headers = {
        "Authorization": f"Bearer {DA_TOKEN}"
    }

    processed = set()

    while True:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()

                for d in data.get("data", []):
                    if d["id"] in processed:
                        continue

                    amount = int(float(d["amount"]))

                    for user_id, s in list(sessions.items()):
                        # проверка времени
                        if time.time() - s["time"] > 300:
                            del sessions[user_id]
                            continue

                        if s["amount"] == amount:
                            users.setdefault(user_id, {"balance": 0, "sub": None})
                            users[user_id]["balance"] += amount

                            await bot.send_message(
                                user_id,
                                f"💰 Баланс пополнен на {amount}₽"
                            )

                            del sessions[user_id]
                            processed.add(d["id"])
                            break

        await asyncio.sleep(10)

# ========= START =========

async def main():
    asyncio.create_task(check_donations())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
