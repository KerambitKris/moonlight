import logging
import asyncio
import os
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DA_TOKEN = os.getenv("DA_TOKEN")
DA_NICK = os.getenv("DA_NICK")
DA_URL = os.getenv("DA_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

users = {}
payments = {}

# --- КНОПКИ ---
def main_menu():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("🏠 Главное меню")
    )

def inline_main():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        InlineKeyboardButton("💰 Пополнить", callback_data="deposit"),
    )
    return kb

# --- СТАРТ ---
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    user_id = msg.from_user.id
    if user_id not in users:
        users[user_id] = {"balance": 0}

    await msg.answer(
        "🔐 Moonlight VPN\n\nВыберите действие:",
        reply_markup=inline_main()
    )

# --- ПРОФИЛЬ ---
@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile(call: types.CallbackQuery):
    user_id = call.from_user.id
    balance = users[user_id]["balance"]

    text = f"""👤 Профиль

Баланс: {balance}₽
Тариф: ❌ Нет активной подписки
ID: {user_id}
"""

    await call.message.edit_text(text, reply_markup=inline_main())

# --- ПОПОЛНЕНИЕ ---
@dp.callback_query_handler(lambda c: c.data == "deposit")
async def deposit(call: types.CallbackQuery):
    await call.message.answer("💰 Введите сумму пополнения:")
    await Deposit.waiting.set()

from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext

dp.storage = MemoryStorage()

class Deposit(StatesGroup):
    waiting = State()

@dp.message_handler(state=Deposit.waiting)
async def process_amount(msg: types.Message, state: FSMContext):
    try:
        amount = int(msg.text)
        if amount < 1:
            raise ValueError
    except:
        return await msg.answer("❌ Введите нормальную сумму")

    user_id = msg.from_user.id
    payments[user_id] = amount

    pay_url = f"{DA_URL}?amount={amount}"

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("💳 Оплатить", url=pay_url),
        InlineKeyboardButton("🔄 Проверить оплату", callback_data="check_pay")
    )

    await msg.answer(
        f"💸 К оплате: {amount}₽\n\nПосле оплаты нажми 'Проверить оплату'",
        reply_markup=kb
    )

    await state.finish()

# --- ПРОВЕРКА ОПЛАТЫ ---
async def check_donations():
    url = "https://www.donationalerts.com/api/v1/alerts/donations"
    headers = {"Authorization": f"Bearer {DA_TOKEN}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            return data["data"]

@dp.callback_query_handler(lambda c: c.data == "check_pay")
async def check_payment(call: types.CallbackQuery):
    user_id = call.from_user.id

    if user_id not in payments:
        return await call.answer("❌ Нет ожидаемых платежей")

    amount = payments[user_id]
    donations = await check_donations()

    for d in donations:
        # ВАЖНО: тут мы ищем сумму
        if int(float(d["amount"])) == amount:
            users[user_id]["balance"] += amount
            del payments[user_id]

            return await call.message.answer(
                f"✅ Оплата подтверждена!\nБаланс: {users[user_id]['balance']}₽"
            )

    await call.answer("❌ Платёж не найден", show_alert=True)

# --- ЗАПУСК ---
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
