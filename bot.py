import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ======================
# СОСТОЯНИЯ
# ======================
class PayState(StatesGroup):
    waiting_amount = State()

# ======================
# REPLY (ТОЛЬКО МЕНЮ)
# ======================
reply_kb = ReplyKeyboardMarkup(resize_keyboard=True)
reply_kb.add(KeyboardButton("🏠 Главное меню"))

# ======================
# INLINE МЕНЮ
# ======================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🔐 Мой VPN", callback_data="vpn")],
        [
            InlineKeyboardButton("🌍 Серверы", callback_data="servers"),
            InlineKeyboardButton("👤 Профиль", callback_data="profile")
        ],
        [InlineKeyboardButton("💰 Пополнить", callback_data="pay")]
    ])

# ======================
# START
# ======================
@dp.message_handler(commands=["start"])
@dp.message_handler(lambda m: m.text == "🏠 Главное меню")
async def start(message: types.Message):
    await message.answer(
        "🔐 Moonlight VPN\n\nВыберите действие:",
        reply_markup=main_menu()
    )

# ======================
# ПРОФИЛЬ
# ======================
@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile(call: types.CallbackQuery):
    text = (
        "👤 Профиль\n\n"
        f"Баланс: 0₽\n"
        f"Тариф: ❌ Нет активной подписки\n"
        f"ID: {call.from_user.id}"
    )
    await call.message.edit_text(text, reply_markup=main_menu())

# ======================
# VPN
# ======================
@dp.callback_query_handler(lambda c: c.data == "vpn")
async def vpn(call: types.CallbackQuery):
    await call.message.edit_text(
        "🔐 Здесь будут ваши VPN ключи (подключим x-ui позже)",
        reply_markup=main_menu()
    )

# ======================
# СЕРВЕРЫ
# ======================
@dp.callback_query_handler(lambda c: c.data == "servers")
async def servers(call: types.CallbackQuery):
    text = (
        "⚡ Автовыбор (обычные VPN)\n\n"
        "🇰🇿 Казахстан\n"
        "🇷🇺 Россия\n"
        "🇳🇱 Нидерланды\n\n\n"
        "⚡ Автовыбор (обход блокировок)\n\n"
        "🇩🇪 Обход 1 — Германия\n"
        "🇩🇪 Обход 2 — Германия\n"
        "🇩🇪 Обход 3 — Германия"
    )
    await call.message.edit_text(text, reply_markup=main_menu())

# ======================
# ПОПОЛНЕНИЕ (ШАГ 1)
# ======================
@dp.callback_query_handler(lambda c: c.data == "pay")
async def pay(call: types.CallbackQuery):
    await call.message.edit_text(
        "💰 Введите сумму пополнения (число):",
        reply_markup=None
    )
    await PayState.waiting_amount.set()

# ======================
# ПОПОЛНЕНИЕ (ШАГ 2)
# ======================
@dp.message_handler(state=PayState.waiting_amount)
async def process_amount(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Введите число")
        return

    amount = int(message.text)

    # тут позже будет генерация DonationAlerts ссылки
    fake_link = f"https://donationalerts.com/r/demo?amount={amount}"

    await message.answer(
        f"💳 Сумма: {amount}₽\n"
        f"👉 Оплатить:\n{fake_link}",
        reply_markup=reply_kb
    )

    await state.finish()

# ======================
# ЗАПУСК
# ======================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
