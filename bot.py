import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
DA_URL = os.getenv("DA_URL")  # ссылка на донат

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# база
users = {}

# ===== КНОПКИ =====
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
    text = (
        "🔐 Moonlight VPN\n\n"
        "👋 Добро пожаловать в Moonlight VPN!\n\n"
        "⚡ Быстрый и стабильный VPN для ваших устройств.\n\n"
        "⭐️ Новостной канал — @moonlight_vpn_news\n"
        "⭐️ Техническая Поддержка — @mtfunit\n\n"
        "👇 Выберите действие:"
    )

    await message.answer(text, reply_markup=main_menu())

# ===== В МЕНЮ =====
@dp.callback_query(F.data == "home")
async def home(callback: CallbackQuery):
    text = (
        "🔐 Moonlight VPN\n\n"
        "👋 Добро пожаловать в Moonlight VPN!\n\n"
        "⚡ Быстрый и стабильный VPN для ваших устройств.\n\n"
        "⭐️ Новостной канал — @moonlight_vpn_news\n"
        "⭐️ Техническая Поддержка — @mtfunit\n\n"
        "👇 Выберите действие:"
    )

    await callback.message.answer(text, reply_markup=main_menu())
    await callback.answer()

# ===== ПОПОЛНЕНИЕ =====
@dp.callback_query(F.data == "deposit")
async def deposit(callback: CallbackQuery):
    users[callback.from_user.id] = {"state": "wait_amount"}

    await callback.message.answer(
        "💳 Введите сумму пополнения (например: 300):",
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
        if amount < 10:
            await message.answer("❌ Минимум 10₽")
            return
    except:
        await message.answer("❌ Введите число")
        return

    users[user_id]["amount"] = amount
    users[user_id]["state"] = "wait_payment"

    text = (
        f"💰 Сумма: {amount}₽\n\n"
        "👉 Нажмите кнопку ниже для оплаты:\n\n"
        "⚠️ После оплаты подождите до 1-2 минут"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=DA_URL)],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="home")]
    ])

    await message.answer(text, reply_markup=keyboard)

# ===== ПРОФИЛЬ =====
@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    user = callback.from_user
    balance = users.get(user.id, {}).get("balance", 0)

    text = (
        "👤 Профиль\n\n"
        f"Баланс: {balance}₽\n"
        f"ID: {user.id}\n"
        "Тариф: ❌ Нет активной подписки"
    )

    await callback.message.answer(text, reply_markup=back_menu())
    await callback.answer()

# ===== VPN =====
@dp.callback_query(F.data == "vpn")
async def vpn(callback: CallbackQuery):
    await callback.message.answer(
        "🔐 Ваш VPN\n\n📡 Статус: Не подключён",
        reply_markup=back_menu()
    )
    await callback.answer()

# ===== СЕРВЕРА =====
@dp.callback_query(F.data == "servers")
async def servers(callback: CallbackQuery):
    await callback.message.answer(
        "🌍 Германия\n🟢 Нагрузка: 34%",
        reply_markup=back_menu()
    )
    await callback.answer()

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
