import os
import uuid
import asyncio
import logging
import json
import secrets
import string
from datetime import datetime, timedelta, timezone

import aiohttp
import asyncpg

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils import executor


# =========================================================
# ENV
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

PANEL_URL = os.getenv("PANEL_URL", "").strip().rstrip("/")
PANEL_LOGIN = os.getenv("PANEL_LOGIN", "").strip()
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD", "").strip()
PANEL_API_TOKEN = os.getenv("PANEL_API_TOKEN", "").strip()

INBOUND_ID = int(os.getenv("INBOUND_ID", "1"))

DA_URL = os.getenv("DA_URL", "").strip().rstrip("/")
DA_TOKEN = os.getenv("DA_TOKEN", "").strip()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


# =========================================================
# ПРОВЕРКА ENV
# =========================================================

if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN")

if not DATABASE_URL:
    raise RuntimeError("Не задан DATABASE_URL")

if not PANEL_URL:
    raise RuntimeError("Не задан PANEL_URL")

if not PANEL_API_TOKEN and not (PANEL_LOGIN and PANEL_PASSWORD):
    raise RuntimeError(
        "Задай PANEL_API_TOKEN или PANEL_LOGIN + PANEL_PASSWORD"
    )

if not DA_TOKEN:
    raise RuntimeError(
        "Не задан DA_TOKEN. "
        "Нужен DonationAlerts OAuth access token."
    )


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


# =========================================================
# BOT
# =========================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


# =========================================================
# ТАРИФЫ
# =========================================================

TARIFFS = {
    "5": {
        "days": 5,
        "price": 19,
    },
    "14": {
        "days": 14,
        "price": 49,
    },
    "30": {
        "days": 30,
        "price": 99,
    },
}


# =========================================================
# ПРОМОКОДЫ
# =========================================================

PROMO_CODES = {
    "FREE30": {
        "amount": 30,
        "uses": 5,
    },
    "VIP100": {
        "amount": 100,
        "uses": 2,
    },
}


waiting_promo = set()

db_pool = None
panel_session = None
panel_lock = asyncio.Lock()
donation_task = None


# =========================================================
# HELPERS
# =========================================================

def utc_now():
    return datetime.now(timezone.utc)


def make_payment_code():
    alphabet = string.ascii_uppercase + string.digits

    return "".join(
        secrets.choice(alphabet)
        for _ in range(8)
    )


def make_sub_id():
    alphabet = string.ascii_lowercase + string.digits

    return "".join(
        secrets.choice(alphabet)
        for _ in range(16)
    )


# =========================================================
# МЕНЮ
# =========================================================

def main_menu():

    kb = ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        KeyboardButton("🚀 Подключиться")
    )

    kb.row(
        KeyboardButton("💳 Купить/Продлить"),
        KeyboardButton("📱 Мои устройства")
    )

    kb.row(
        KeyboardButton("🔗 Рефералы"),
        KeyboardButton("🌐 Web Кабинет")
    )

    kb.row(
        KeyboardButton("🆘 Помощь")
    )

    kb.row(
        KeyboardButton("🎟 Ввести промокод")
    )

    return kb


def tariffs_keyboard():

    kb = ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row(
        KeyboardButton("5 дней — 19 ₽"),
        KeyboardButton("14 дней — 49 ₽")
    )

    kb.row(
        KeyboardButton("30 дней — 99 ₽")
    )

    kb.row(
        KeyboardButton("💰 Баланс"),
        KeyboardButton("◀️ Главное меню")
    )

    return kb


# =========================================================
# DATABASE
# =========================================================

async def init_db():

    global db_pool

    db_url = DATABASE_URL

    if db_url.startswith("postgres://"):
        db_url = (
            "postgresql://"
            + db_url[len("postgres://"):]
        )

    db_pool = await asyncpg.create_pool(
        db_url,
        min_size=1,
        max_size=5,
        command_timeout=30,
    )

    async with db_pool.acquire() as conn:

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                username TEXT,
                balance NUMERIC(12,2) NOT NULL DEFAULT 0,
                payment_code TEXT UNIQUE NOT NULL,
                vpn_key TEXT,
                vpn_client_id TEXT,
                vpn_sub_id TEXT,
                vpn_expires TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS donations (
                donation_id BIGINT PRIMARY KEY,
                telegram_id BIGINT NOT NULL,
                amount NUMERIC(12,2) NOT NULL,
                currency TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        await conn.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS vpn_sub_id TEXT
        """)

    logging.info("Database connected")


async def get_user(uid):

    async with db_pool.acquire() as conn:

        return await conn.fetchrow(
            """
            SELECT *
            FROM users
            WHERE telegram_id=$1
            """,
            uid
        )


async def register_user(message):

    uid = message.from_user.id
    username = message.from_user.username or ""

    user = await get_user(uid)

    if user:

        async with db_pool.acquire() as conn:

            await conn.execute(
                """
                UPDATE users
                SET username=$1
                WHERE telegram_id=$2
                """,
                username,
                uid
            )

        return await get_user(uid)

    while True:

        payment_code = make_payment_code()

        try:

            async with db_pool.acquire() as conn:

                await conn.execute(
                    """
                    INSERT INTO users
                    (
                        telegram_id,
                        username,
                        balance,
                        payment_code
                    )
                    VALUES ($1, $2, 0, $3)
                    """,
                    uid,
                    username,
                    payment_code
                )

            break

        except asyncpg.UniqueViolationError:

            continue

    return await get_user(uid)


async def add_balance(uid, amount):

    async with db_pool.acquire() as conn:

        return await conn.fetchval(
            """
            UPDATE users
            SET balance = balance + $1
            WHERE telegram_id=$2
            RETURNING balance
            """,
            amount,
            uid
        )


async def subtract_balance(uid, amount):

    async with db_pool.acquire() as conn:

        row = await conn.fetchrow(
            """
            UPDATE users
            SET balance = balance - $1
            WHERE telegram_id=$2
              AND balance >= $1
            RETURNING balance
            """,
            amount,
            uid
        )

        if not row:
            return None

        return row["balance"]


# =========================================================
# DONATIONALERTS
# =========================================================

async def process_donation(donation):

    try:

        donation_id = int(
            donation["id"]
        )

        amount = float(
            donation.get("amount", 0)
        )

        currency = str(
            donation.get("currency", "")
        ).upper()

        message = str(
            donation.get("message") or ""
        ).upper()

        if currency != "RUB":
            return

        if amount <= 0:
            return

        async with db_pool.acquire() as conn:

            users = await conn.fetch(
                """
                SELECT
                    telegram_id,
                    payment_code
                FROM users
                """
            )

        target_uid = None

        for user in users:

            code = str(
                user["payment_code"]
            ).upper()

            if code and code in message:

                target_uid = user["telegram_id"]

                break

        if target_uid is None:

            logging.warning(
                "Donation %s без payment_code: %r",
                donation_id,
                message
            )

            return

        async with db_pool.acquire() as conn:

            async with conn.transaction():

                inserted = await conn.fetchval(
                    """
                    INSERT INTO donations
                    (
                        donation_id,
                        telegram_id,
                        amount,
                        currency
                    )
                    VALUES ($1, $2, $3, $4)

                    ON CONFLICT (donation_id)
                    DO NOTHING

                    RETURNING donation_id
                    """,
                    donation_id,
                    target_uid,
                    amount,
                    currency
                )

                if inserted is None:
                    return

                new_balance = await conn.fetchval(
                    """
                    UPDATE users
                    SET balance = balance + $1
                    WHERE telegram_id=$2
                    RETURNING balance
                    """,
                    amount,
                    target_uid
                )

        await bot.send_message(
            target_uid,

            "✅ Пополнение получено!\n\n"
            f"💰 +{amount:.2f} ₽\n"
            f"💳 Баланс: {float(new_balance):.2f} ₽",

            reply_markup=main_menu()
        )

        logging.info(
            "Donation %s: %.2f RUB -> %s",
            donation_id,
            amount,
            target_uid
        )

    except Exception:

        logging.exception(
            "Ошибка обработки доната"
        )


async def donation_loop():

    await asyncio.sleep(5)

    initialized = False

    timeout = aiohttp.ClientTimeout(
        total=20
    )

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        while True:

            try:

                headers = {
                    "Authorization":
                        f"Bearer {DA_TOKEN}",

                    "Accept":
                        "application/json",
                }

                async with session.get(
                    "https://www.donationalerts.com/api/v1/alerts/donations",
                    params={
                        "page": 1
                    },
                    headers=headers
                ) as resp:

                    body = await resp.text()

                    if resp.status == 401:

                        logging.error(
                            "DonationAlerts HTTP 401: "
                            "DA_TOKEN не принят. "
                            "Нужен OAuth access token "
                            "со scope oauth-donation-index."
                        )

                    elif resp.status != 200:

                        logging.error(
                            "DonationAlerts HTTP %s: %s",
                            resp.status,
                            body[:500]
                        )

                    else:

                        try:
                            data = json.loads(body)
                        except Exception:
                            data = {}

                        donations = data.get(
                            "data",
                            []
                        )

                        # При первом запуске
                        # старые донаты НЕ начисляем.
                        if not initialized:

                            async with db_pool.acquire() as conn:

                                for donation in donations:

                                    try:

                                        donation_id = int(
                                            donation["id"]
                                        )

                                        await conn.execute(
                                            """
                                            INSERT INTO donations
                                            (
                                                donation_id,
                                                telegram_id,
                                                amount,
                                                currency
                                            )
                                            VALUES
                                            ($1, 0, $2, $3)

                                            ON CONFLICT
                                            (donation_id)
                                            DO NOTHING
                                            """,
                                            donation_id,
                                            float(
                                                donation.get(
                                                    "amount",
                                                    0
                                                )
                                            ),
                                            str(
                                                donation.get(
                                                    "currency",
                                                    ""
                                                )
                                            )
                                        )

                                    except Exception:

                                        logging.exception(
                                            "Ошибка истории DA"
                                        )

                            initialized = True

                            logging.info(
                                "DonationAlerts history initialized"
                            )

                        else:

                            for donation in reversed(
                                donations
                            ):

                                await process_donation(
                                    donation
                                )

            except asyncio.CancelledError:

                raise

            except Exception:

                logging.exception(
                    "Ошибка DonationAlerts"
                )

            await asyncio.sleep(20)


# =========================================================
# 3X-UI
# =========================================================

async def close_panel_session():

    global panel_session

    if (
        panel_session is not None
        and not panel_session.closed
    ):

        await panel_session.close()

    panel_session = None


async def panel_login():

    global panel_session

    await close_panel_session()

    panel_session = aiohttp.ClientSession(
        cookie_jar=aiohttp.CookieJar()
    )

    # =============================================
    # API TOKEN
    # =============================================

    if PANEL_API_TOKEN:

        panel_session.headers.update({

            "Authorization":
                f"Bearer {PANEL_API_TOKEN}",

            "Accept":
                "application/json",
        })

        url = (
            f"{PANEL_URL}"
            "/panel/api/inbounds/list"
        )

        logging.info(
            "3X-UI API token check: %s",
            url
        )

        try:

            async with panel_session.get(
                url
            ) as resp:

                body = await resp.text()

                logging.info(
                    "3X-UI token response: "
                    "HTTP %s | %s",
                    resp.status,
                    body[:500]
                )

                if resp.status != 200:

                    raise RuntimeError(
                        "3X-UI API Token error: "
                        f"HTTP {resp.status}: "
                        f"{body[:500]}"
                    )

                try:
                    data = json.loads(body)
                except Exception:
                    data = {}

                if data.get("success") is False:

                    raise RuntimeError(
                        f"3X-UI rejected token: {data}"
                    )

                logging.info(
                    "3X-UI Bearer authorization OK"
                )

                return

        except aiohttp.ClientError as exc:

            raise RuntimeError(
                f"3X-UI connection error: {exc}"
            )

    # =============================================
    # FALLBACK LOGIN/PASSWORD
    # =============================================

    url = f"{PANEL_URL}/login"

    logging.info(
        "3X-UI login URL: %s",
        url
    )

    async with panel_session.post(
        url,

        json={
            "username": PANEL_LOGIN,
            "password": PANEL_PASSWORD,
        },

        headers={
            "Accept":
                "application/json"
        },

        allow_redirects=True
    ) as resp:

        body = await resp.text()

        logging.info(
            "3X-UI login response: "
            "HTTP %s | %s",
            resp.status,
            body[:500]
        )

        if resp.status != 200:

            raise RuntimeError(
                f"3X-UI login HTTP "
                f"{resp.status}: {body[:500]}"
            )

        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if data.get("success") is False:

            raise RuntimeError(
                f"3X-UI login rejected: {data}"
            )


async def panel_request(
    method,
    path,
    **kwargs
):

    global panel_session

    if (
        panel_session is None
        or panel_session.closed
    ):

        await panel_login()

    url = f"{PANEL_URL}{path}"

    async with panel_session.request(
        method,
        url,
        allow_redirects=True,
        **kwargs
    ) as resp:

        body = await resp.text()

        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        # Повторная авторизация.
        if resp.status in (401, 403):

            logging.warning(
                "3X-UI HTTP %s -> "
                "повторная авторизация",
                resp.status
            )

            await close_panel_session()
            await panel_login()

            async with panel_session.request(
                method,
                url,
                allow_redirects=True,
                **kwargs
            ) as retry:

                retry_body = await retry.text()

                try:
                    retry_data = (
                        json.loads(retry_body)
                        if retry_body
              
