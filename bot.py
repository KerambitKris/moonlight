import asyncio
import os
import aiohttp

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
DA_TOKEN = os.getenv("DA_TOKEN")
DA_URL = os.getenv("DA_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

users = {}
processed = set()  # уже обработанные донаты


# ===== МЕНЮ =====
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Мой VPN", callback_data="vpn")],
        [
            InlineKeyboardButton(text="💳 Пополнить", callback_data="deposit"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        ],
        [InlineKeyboardButton(text="🌍 Серверы", callback_data="servers")],
    ])


def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="home")]
    ])


# ===== СТАРТ =====
@dp.message(F.text == "/start")
async def start(message: Message):
    await message.answer(
        "🔐 Moonlight VPN\n\n"
        "👋 Добро пожаловать в Moonlight VPN!\n\n"
        "⚡ Быстрый и стабильный VPN для ваших устройств.\n\n"
        "⭐️ Новостной канал — @moonlight_vpn_news\n"
        "⭐️ Техническая Поддержка — @mtfunit\n\n"
        "👇 Выберите действие:",
        reply_markup=main_menu()
    )


# ===== В МЕНЮ =====
@dp.callback_query(F.data == "home")
async def home(callback: CallbackQuery):
    await callback.message.answer(
        "🔐 Moonlight VPN\n\n"
        "👋 Добро пожаловать в Moonlight VPN!\n\n"
        "⚡ Быстрый и стабильный VPN для ваших устройств.\n\n"
        "⭐️ Новостной канал — @moonlight_vpn_news\n"
        "⭐️ Техническая Поддержка — @mtfunit\n\n"
        "👇 Выберите действие:",
        reply_markup=main_menu()
    )
    await callback.answer()


# ===== ПОПОЛНЕНИЕ =====
@dp.callback_query(F.data == "deposit")
async def deposit(callback: CallbackQuery):
    users[callback.from_user.id] = {"state": "wait_amount"}

    await callback.message.answer(
        "💳 Введите сумму пополнения:",
        reply_markup=back_menu()
    )
    await callback.answer()


# ===== ВВОД СУММЫ =====
@dp.message()
async def handle_amount(message: Message):
    user_id = message.from_user.id

    if user_id not in users:
        return

    if users[user_id].get("state") != "wait_amount":
        return

    try:
        amount = int(message.text)
    except:
        await message.answer("❌ Введите число")
        return

    users[user_id]["amount"] = amount
    users[user_id]["state"] = "wait_payment"

    await message.answer(
        f"💰 Сумма: {amount}₽\n\n"
        "👉 Оплатите по кнопке ниже:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=DA_URL)],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="home")]
        ])
    )


# ===== ПРОФИЛЬ =====
@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    user = callback.from_user
    balance = users.get(user.id, {}).get("balance", 0)

    await callback.message.answer(
        f"👤 Профиль\n\n"
        f"Баланс: {balance}₽\n"
        f"ID: {user.id}\n"
        f"Тариф: ❌ Нет активной подписки",
        reply_markup=back_menu()
    )
    await callback.answer()


# ===== ПРОВЕРКА ДОНАТОВ =====
async def check_donations():
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {DA_TOKEN}"
                }

                async with session.get(
                    "https://www.donationalerts.com/api/v1/alerts/donations",
                    headers=headers
                ) as resp:

                    data = await resp.json()

                    if "data" in data:
                        for d in data["data"]:
                            donate_id = d["id"]

                            if donate_id in processed:
                                continue

                            processed.add(donate_id)

                            amount = int(float(d["amount"]))

                            # ищем пользователя
                            for user_id, u in users.items():
                                if u.get("state") == "wait_payment":
                                    expected = u.get("amount")

                                    if abs(expected - amount) <= 2:
                                        users[user_id]["balance"] = users[user_id].get("balance", 0) + amount
                                        users[user_id]["state"] = "none"

                                        await bot.send_message(
                                            user_id,
                                            f"✅ Баланс пополнен на {amount}₽"
                                        )
                                        break

        except Exception as e:
            print("Ошибка:", e)

        await asyncio.sleep(5)


# ===== ЗАПУСК =====
async def main():
    asyncio.create_task(check_donations())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
