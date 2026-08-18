import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
DONATE_URL = os.getenv("DA_URL")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# =========================
# 🔘 ГЛАВНОЕ МЕНЮ (КАК У КУРА)
# =========================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add(
        KeyboardButton("💳 Купить/продлить"),
        KeyboardButton("📱 Мои устройства")
    )

    kb.add(
        KeyboardButton("🔗 Рефералы"),
        KeyboardButton("🌐 Web кабинет")
    )

    kb.add(KeyboardButton("🆘 Помощь"))
    kb.add(KeyboardButton("🎟 Ввести промокод"))

    return kb


# =========================
# 🔙 КНОПКА НАЗАД
# =========================
def back_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🏠 В меню"))
    return kb


# =========================
# 🚀 START
# =========================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    text = (
        "🔐 Moonlight VPN\n\n"
        "💰 Баланс: 0₽\n"
        "❌ Нет активной подписки\n\n"
        "Выберите действие:"
    )

    await message.answer(text, reply_markup=main_menu())


# =========================
# 🏠 В МЕНЮ
# =========================
@dp.message_handler(lambda m: m.text == "🏠 В меню")
async def back(message: types.Message):
    await message.answer("🏠 Главное меню:", reply_markup=main_menu())


# =========================
# 💳 КУПИТЬ
# =========================
@dp.message_handler(lambda m: m.text == "💳 Купить/продлить")
async def buy(message: types.Message):
    text = (
        "💳 Покупка VPN\n\n"
        "Перейдите по ссылке для оплаты:\n"
        f"{DONATE_URL}"
    )

    await message.answer(text, reply_markup=back_menu())


# =========================
# 📱 УСТРОЙСТВА
# =========================
@dp.message_handler(lambda m: m.text == "📱 Мои устройства")
async def devices(message: types.Message):
    text = (
        "📱 Ваши устройства:\n\n"
        "Доступно: 0\n"
        "Активных: 0"
    )

    await message.answer(text, reply_markup=back_menu())


# =========================
# 🔗 РЕФЕРАЛЫ
# =========================
@dp.message_handler(lambda m: m.text == "🔗 Рефералы")
async def refs(message: types.Message):
    text = (
        "🔗 Реферальная система\n\n"
        "Приглашай друзей и получай бонусы"
    )

    await message.answer(text, reply_markup=back_menu())


# =========================
# 🌐 WEB
# =========================
@dp.message_handler(lambda m: m.text == "🌐 Web кабинет")
async def web(message: types.Message):
    text = (
        "🌐 Web кабинет\n\n"
        "Функция в разработке"
    )

    await message.answer(text, reply_markup=back_menu())


# =========================
# 🆘 ПОМОЩЬ
# =========================
@dp.message_handler(lambda m: m.text == "🆘 Помощь")
async def help_cmd(message: types.Message):
    text = (
        "🆘 Поддержка\n\n"
        "Напишите администратору"
    )

    await message.answer(text, reply_markup=back_menu())


# =========================
# 🎟 ПРОМОКОД
# =========================
@dp.message_handler(lambda m: m.text == "🎟 Ввести промокод")
async def promo(message: types.Message):
    text = (
        "🎟 Введите промокод:\n\n"
        "Функция скоро будет доступна"
    )

    await message.answer(text, reply_markup=back_menu())


# =========================
# 🚀 ЗАПУСК
# =========================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
