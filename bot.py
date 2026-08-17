import os
import json
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

BOT_TOKEN = os.getenv("BOT_TOKEN")
DA_TOKEN = os.getenv("DA_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

DB_FILE = "db.json"

# ================= БАЗА =================
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

# ================= REPLY (НИЗ) =================
reply_kb = ReplyKeyboardMarkup(resize_keyboard=True)
reply_kb.add(KeyboardButton("⬅️ Главное меню"))

# ================= МЕНЮ =================

def menu_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🔐 Мой VPN", callback_data="vpn")],
        [InlineKeyboardButton("🌍 Серверы", callback_data="servers")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("💰 Пополнить", callback_data="pay")]
    ])

def menu_servers():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("⚡ Автовыбор", callback_data="auto")],
        [InlineKeyboardButton("🇰🇿 Казахстан", callback_data="kz")],
        [InlineKeyboardButton("🇷🇺 Россия", callback_data="ru")],
        [InlineKeyboardButton("🇳🇱 Нидерланды", callback_data="nl")],
        [InlineKeyboardButton("🇩🇪 Обход 1", callback_data="de1")],
        [InlineKeyboardButton("🇩🇪 Обход 2", callback_data="de2")],
        [InlineKeyboardButton("🇩🇪 Обход 3", callback_data="de3")]
    ])

def menu_pay():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("💳 50₽", callback_data="pay_50")],
        [InlineKeyboardButton("💳 100₽", callback_data="pay_100")],
        [InlineKeyboardButton("💳 200₽", callback_data="pay_200")]
    ])

# ================= START =================
@dp.message_handler(commands=["start"])
@dp.message_handler(lambda m: m.text == "⬅️ Главное меню")
async def start(msg: types.Message):
    await msg.answer(
        "🔐 Moonlight VPN\n\nВыберите действие:",
        reply_markup=menu_main()
    )

# ================= ПРОФИЛЬ =================
@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile(call: types.CallbackQuery):
    db = load_db()
    uid = str(call.from_user.id)

    if uid not in db:
        db[uid] = {"balance": 0}
        save_db(db)

    bal = db[uid]["balance"]

    await call.message.edit_text(
f"""👤 Профиль

Баланс: {bal}₽
Тариф: ❌ Нет активной подписки
ID: {uid}""",
        reply_markup=menu_main()
    )

# ================= VPN =================
@dp.callback_query_handler(lambda c: c.data == "vpn")
async def vpn(call: types.CallbackQuery):
    await call.message.edit_text(
        "🔐 Ваш VPN\n\n(тут будет ключ)",
        reply_markup=menu_main()
    )

# ================= СЕРВЕРА =================
@dp.callback_query_handler(lambda c: c.data == "servers")
async def servers(call: types.CallbackQuery):
    await call.message.edit_text(
        "🌍 Выберите сервер:",
        reply_markup=menu_servers()
    )

# ================= ВЫБОР СЕРВЕРА =================
@dp.callback_query_handler(lambda c: c.data in ["auto","kz","ru","nl","de1","de2","de3"])
async def choose_server(call: types.CallbackQuery):
    await call.answer("Выбрано ✅", show_alert=True)

# ================= ОПЛАТА =================
@dp.callback_query_handler(lambda c: c.data == "pay")
async def pay(call: types.CallbackQuery):
    await call.message.edit_text(
        "💰 Выберите сумму:",
        reply_markup=menu_pay()
    )

@dp.callback_query_handler(lambda c: c.data.startswith("pay_"))
async def pay_create(call: types.CallbackQuery):
    amount = int(call.data.split("_")[1])
    uid = call.from_user.id

    link = f"https://www.donationalerts.com/r/YOURNAME?message={uid}&amount={amount}"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 Оплатить", url=link))

    await call.message.edit_text(
        f"Сумма: {amount}₽\n\nНажмите кнопку ниже:",
        reply_markup=kb
    )

# ================= ДОНАТЫ =================
last_ids = set()

async def check_donates():
    global last_ids

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {DA_TOKEN}"}

                async with session.get(
                    "https://www.donationalerts.com/api/v1/alerts/donations",
                    headers=headers
                ) as resp:

                    data = await resp.json()

                    db = load_db()

                    for d in data["data"]:
                        if d["id"] in last_ids:
                            continue

                        last_ids.add(d["id"])

                        uid = d["message"]
                        amount = int(float(d["amount"]))

                        if uid not in db:
                            db[uid] = {"balance": 0}

                        db[uid]["balance"] += amount

                        await bot.send_message(uid, f"💰 +{amount}₽")

                    save_db(db)

        except:
            pass

        await asyncio.sleep(15)

# ================= ЗАПУСК =================
async def on_startup(_):
    asyncio.create_task(check_donates())

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
