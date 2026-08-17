import os
import json
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

BOT_TOKEN = os.getenv("BOT_TOKEN")
DA_TOKEN = os.getenv("DA_TOKEN")
DA_URL = os.getenv("DA_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

DB_FILE = "db.json"

# ---------- БАЗА ----------
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

# ---------- КНОПКИ ----------

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔐 Мой VPN", callback_data="vpn"),
