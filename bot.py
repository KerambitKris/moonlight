import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

# =========================
# 🔐 ПЕРЕМЕННЫЕ (Railway)
# =========================
TOKEN = os.getenv("BOT_TOKEN")
DONATE_URL = os.getenv("DONATE_URL")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# =========================
# 🔥 БОЛЬШОЕ МЕНЮ (как Kyra)
# =========================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row(
        KeyboardButton("💳 Купить/Продлить"),
        KeyboardButton("📱 Мои устройства")
    )
    kb.row(
        KeyboardButton("🔗 Рефералы"),
        KeyboardButton("🌐 Web кабинет")
    )
    kb.row(
        KeyboardButton("🚀 Подключиться к VPN")
    )
    kb.row(
        KeyboardButton("🆘 Помощь")
    )
    kb.row(
        KeyboardButton("🎟 Ввести промокод")
    )

    return kb


# =========================
# 🚀 СТАРТ
# =========================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "🔐 Moonlight VPN\n\nДобро пожаловать 👇",
        reply_markup=main_menu()
    )


# =========================
# 💳 ПОКУПКА
# =========================
@dp.message_handler(lambda m: m.text == "💳 Купить/Продлить")
async def buy(message: types.Message):
    await message.answer(
        f"💳 Оплата\n\nПерейди по ссылке:\n{DONATE_URL}",
        reply_markup=main_menu()
    )


# =========================
# 📱 УСТРОЙСТВА
# =========================
@dp.message_handler(lambda m: m.text == "📱 Мои устройства")
async def devices(message: types.Message):
    await message.answer(
        "📱 Устройства\n\nУ вас пока нет подключённых устройств",
        reply_markup=main_menu()
    )


# =========================
# 🔗 РЕФЕРАЛЫ
# =========================
@dp.message_handler(lambda m: m.text == "🔗 Рефералы")
async def refs(message: types.Message):
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={message.from_user.id}"

    await message.answer(
        f"👥 Реферальная программа\n\n"
        f"Ваша ссылка:\n{ref_link}\n\n"
        f"Доход: 0₽",
        reply_markup=main_menu()
    )


# =========================
# 🌐 WEB
# =========================
@dp.message_handler(lambda m: m.text == "🌐 Web кабинет")
async def web(message: types.Message):
    await message.answer(
        "🌐 Кабинет:\nhttps://client.disavi.store/",
        reply_markup=main_menu()
    )


# =========================
# 🚀 VPN
# =========================
@dp.message_handler(lambda m: m.text == "🚀 Подключиться к VPN")
async def vpn(message: types.Message):
    await message.answer(
        "🚀 У вас нет активной подписки\n\nСначала пополните баланс",
        reply_markup=main_menu()
    )


# =========================
# 🆘 ПОМОЩЬ
# =========================
@dp.message_handler(lambda m: m.text == "🆘 Помощь")
async def help_cmd(message: types.Message):
    await message.answer(
        "🆘 Поддержка: @your_support",
        reply_markup=main_menu()
    )


# =========================
# 🎟 ПРОМОКОД
# =========================
@dp.message_handler(lambda m: m.text == "🎟 Ввести промокод")
async def promo(message: types.Message):
    await message.answer(
        "Введите промокод:",
        reply_markup=main_menu()
    )


# =========================
# 🚀 ЗАПУСК
# =========================
if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN не найден в переменных Railway")

    executor.start_polling(dp, skip_updates=True)
