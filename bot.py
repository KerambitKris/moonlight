import os
import uuid
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import aiohttp
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# =========================================================
# ENV / НАСТРОЙКИ
# =========================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")

PANEL_URL = os.getenv("PANEL_URL", "").rstrip("/")
PANEL_LOGIN = os.getenv("PANEL_LOGIN")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD")
# Для современных 3X-UI предпочтительно использовать API Token.
# Если токен задан, логин/пароль панели не используются.
PANEL_API_TOKEN = os.getenv("PANEL_API_TOKEN", "").strip()
INBOUND_ID = int(os.getenv("INBOUND_ID", "1"))

# Ссылка на страницу приёма донатов DonationAlerts
DA_URL = os.getenv("DA_URL", "").rstrip("/")
DA_TOKEN = os.getenv("DA_TOKEN")

# Railway PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN")
if not DATABASE_URL:
    raise RuntimeError("Не задан DATABASE_URL (Railway PostgreSQL)")
if not DA_URL:
    raise RuntimeError("Не задан DA_URL")
if not PANEL_URL:
    raise RuntimeError("Не задан PANEL_URL")
if not PANEL_API_TOKEN and (not PANEL_LOGIN or not PANEL_PASSWORD):
    raise RuntimeError(
        "Задай либо PANEL_API_TOKEN, либо PANEL_LOGIN + PANEL_PASSWORD"
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# =========================================================
# ТАРИФЫ
# =========================================================
TARIFFS = {
    "5": {"days": 5, "price": 19},
    "14": {"days": 14, "price": 49},
    "30": {"days": 30, "price": 99},
}

# =========================================================
# ПРОМОКОДЫ
# =========================================================
PROMO_CODES = {
    "FREE30": {"amount": 30, "uses": 5},
    "VIP100": {"amount": 100, "uses": 2},
}

waiting_promo = set()
waiting_days = set()

db_pool = None
panel_session = None
donations_initialized = False
panel_lock = asyncio.Lock()


# =========================================================
# МЕНЮ
# =========================================================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    # Размеры как на примере: 1 / 2 / 2 / 1
    kb.row(
        KeyboardButton("🚀 Подключиться"),
    )
    kb.row(
        KeyboardButton("💳 Купить/Продлить"),
        KeyboardButton("📱 Мои устройства"),
    )
    kb.row(
        KeyboardButton("🔗 Рефералы"),
        KeyboardButton("🌐 Web Кабинет"),
    )
    kb.row(
        KeyboardButton("🆘 Помощь"),
    )
    kb.row(
        KeyboardButton("🎟 Ввести промокод"),
    )

    return kb


# =========================================================
# DATABASE
# =========================================================
async def init_db():
    global db_pool

    db_url = DATABASE_URL
    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://"):]

    db_pool = await asyncpg.create_pool(db_url, min_size=1, max_size=5)

    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                username TEXT,
                balance NUMERIC(12,2) NOT NULL DEFAULT 0,
                payment_code TEXT UNIQUE NOT NULL,
                vpn_key TEXT,
                vpn_client_id TEXT,
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


async def get_user(uid):
    async with db_pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id=$1",
            uid
        )


async def register_user(message: types.Message):
    uid = message.from_user.id
    username = message.from_user.username or ""

    user = await get_user(uid)
    if user:
        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET username=$1 WHERE telegram_id=$2",
                username, uid
            )
        return user

    # Уникальный код для оплаты.
    # Пользователь пишет его в сообщение DonationAlerts.
    while True:
        payment_code = str(uuid.uuid4()).replace("-", "")[:8].upper()
        try:
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO users
                    (telegram_id, username, balance, payment_code)
                    VALUES ($1, $2, 0, $3)
                    """,
                    uid, username, payment_code
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
            amount, uid
        )


async def subtract_balance(uid, amount):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE users
            SET balance = balance - $1
            WHERE telegram_id=$2 AND balance >= $1
            RETURNING balance
            """,
            amount, uid
        )
        return row["balance"] if row else None


# =========================================================
# DONATIONALERTS
# =========================================================
async def donation_loop():
    global donations_initialized

    await asyncio.sleep(5)

    if not DA_TOKEN:
        logging.error(
            "DonationAlerts отключён: не задан DA_TOKEN. "
            "Нужен OAuth access token со scope oauth-donation-index."
        )
        return

    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        auth_failed = False

        while True:
            try:
                headers = {
                    "Authorization": f"Bearer {DA_TOKEN.strip()}",
                    "Accept": "application/json",
                }

                async with session.get(
                    "https://www.donationalerts.com/api/v1/alerts/donations",
                    params={"page": 1},
                    headers=headers,
                ) as resp:
                    body = await resp.text()

                    if resp.status == 401:
                        if not auth_failed:
                            logging.error(
                                "DonationAlerts HTTP 401: токен недействителен/истёк "
                                "или у токена нет scope oauth-donation-index. "
                                "Обнови DA_TOKEN в Railway."
                            )
                            auth_failed = True
                        await asyncio.sleep(60)
                        continue

                    auth_failed = False

                    if resp.status != 200:
                        logging.error(
                            "DonationAlerts HTTP %s: %s",
                            resp.status, body[:500]
                        )
                    else:
                        try:
                            data = await resp.json(content_type=None)
                        except Exception:
                            logging.error(
                                "DonationAlerts вернул не-JSON: %s", body[:500]
                            )
                            data = {}

                        donations = data.get("data", [])

                        if not donations_initialized:
                            for donation in donations:
                                try:
                                    donation_id = int(donation["id"])
                                    async with db_pool.acquire() as conn:
                                        await conn.execute(
                                            """
                                            INSERT INTO donations
                                            (donation_id, telegram_id, amount, currency)
                                            VALUES ($1, 0, $2, $3)
                                            ON CONFLICT (donation_id) DO NOTHING
                                            """,
                                            donation_id,
                                            float(donation.get("amount", 0)),
                                            str(donation.get("currency", "")),
                                        )
                                except Exception:
                                    logging.exception(
                                        "Ошибка инициализации донатов"
                                    )

                            donations_initialized = True
                            logging.info(
                                "DonationAlerts: история инициализирована"
                            )
                        else:
                            for donation in reversed(donations):
                                await process_donation(donation)

            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception("Ошибка проверки DonationAlerts")

            await asyncio.sleep(20)


async def process_donation(donation):
    try:
        donation_id = int(donation["id"])
        amount = float(donation["amount"])
        currency = str(donation.get("currency", "")).upper()
        message = str(donation.get("message") or "").upper()

        # Для безопасности принимаем только RUB.
        if currency != "RUB" or amount <= 0:
            return

        # Надёжный поиск кода: берём зарегистрированных пользователей.
        async with db_pool.acquire() as conn:
            users = await conn.fetch(
                "SELECT telegram_id, payment_code FROM users"
            )

        target_uid = None
        for row in users:
            if row["payment_code"].upper() in message:
                target_uid = row["telegram_id"]
                break

        if not target_uid:
            logging.warning(
                "Донат %s на %.2f RUB без payment_code: %r",
                donation_id, amount, message
            )
            return

        # INSERT + уникальный donation_id защищает от двойного начисления.
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                inserted = await conn.fetchval(
                    """
                    INSERT INTO donations
                    (donation_id, telegram_id, amount, currency)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (donation_id) DO NOTHING
                    RETURNING donation_id
                    """,
                    donation_id, target_uid, amount, currency
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
                    amount, target_uid
                )

        await bot.send_message(
            target_uid,
            "✅ Пополнение получено!\n\n"
            f"💰 +{amount:.2f} ₽\n"
            f"💳 Баланс: {float(new_balance):.2f} ₽",
            reply_markup=main_menu()
        )

        logging.info(
            "Зачислен донат %s: %.2f RUB -> %s",
            donation_id, amount, target_uid
        )

    except Exception:
        logging.exception("Ошибка обработки доната: %r", donation)


# =========================================================
# X-UI / 3X-UI
# =========================================================
async def panel_login():
    global panel_session

    if panel_session is not None and not panel_session.closed:
        await panel_session.close()

    panel_session = aiohttp.ClientSession(
        cookie_jar=aiohttp.CookieJar()
    )

    if PANEL_API_TOKEN:
        panel_session.headers.update({
            "Authorization": f"Bearer {PANEL_API_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

        api_check_url = f"{PANEL_URL}/panel/api/inbounds/list"
        logging.info("3X-UI API token check: %s", api_check_url)

        try:
            async with panel_session.get(api_check_url) as resp:
                body = await resp.text()
                logging.info(
                    "3X-UI API token response: HTTP %s | %s",
                    resp.status,
                    body[:500],
                )

                if resp.status != 200:
                    raise RuntimeError(
                        f"Проверка API Token HTTP {resp.status}: {body[:500]}"
                    )

                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    data = {}

                if data and data.get("success") is False:
                    raise RuntimeError(
                        f"3X-UI отклонила API Token: {data}"
                    )

                logging.info(
                    "3X-UI авторизация через API Token успешна"
                )
                return

        except aiohttp.ClientError as e:
            raise RuntimeError(
                f"Ошибка подключения к VPN-панели: {e}"
            )

    login_url = f"{PANEL_URL}/login"
    logging.info("3X-UI login URL: %s", login_url)

    try:
        async with panel_session.post(
            login_url,
            json={
                "username": PANEL_LOGIN,
                "password": PANEL_PASSWORD,
            },
            headers={"Accept": "application/json"},
            allow_redirects=True,
        ) as resp:
            text = await resp.text()

            logging.info(
                "3X-UI login response: HTTP %s | %s",
                resp.status,
                text[:500],
            )

            if resp.status != 200:
                raise RuntimeError(
                    f"Панель логин HTTP {resp.status}: {text[:500]}"
                )

            try:
                data = await resp.json(content_type=None)
            except Exception:
                data = {}

            if data and data.get("success") is False:
                raise RuntimeError(
                    f"Панель отклонила авторизацию: {data}"
                )

            logging.info("Авторизация в VPN-панели выполнена")

    except aiohttp.ClientError as e:
        raise RuntimeError(
            f"Ошибка подключения к VPN-панели: {e}"
        )


async def panel_get_inbound():
    url = f"{PANEL_URL}/panel/api/inbounds/get/{INBOUND_ID}"

    async with panel_session.get(url) as resp:
        text = await resp.text()

        try:
            data = await resp.json(content_type=None)
        except Exception:
            data = {}

        logging.info(
            "3X-UI inbound: HTTP %s | %s",
            resp.status,
            text[:1000],
        )

        if resp.status != 200 or not data.get("success"):
            raise RuntimeError(
                f"Не удалось получить inbound {INBOUND_ID}: "
                f"HTTP {resp.status} {text[:500]}"
            )

        inbound = data.get("obj") or data.get("data")
        if not inbound:
            raise RuntimeError("3X-UI не вернула данные inbound")

        return inbound


async def panel_request_json(method, url, payload=None):
    kwargs = {"allow_redirects": True}
    if payload is not None:
        kwargs["json"] = payload

    async with panel_session.request(method, url, **kwargs) as resp:
        text = await resp.text()

        try:
            data = await resp.json(content_type=None)
        except Exception:
            data = {}

        logging.info(
            "3X-UI %s %s -> HTTP %s | %s",
            method,
            url,
            resp.status,
            text[:1500],
        )

        return resp.status, data, text


async def get_client_by_email(email):
    url = f"{PANEL_URL}/panel/api/clients/get/{email}"
    status, data, text = await panel_request_json("GET", url)

    if status != 200 or not data.get("success"):
        return None

    obj = data.get("obj") or data.get("data")
    if isinstance(obj, dict):
        client = obj.get("client")
        if isinstance(client, dict):
            return client
        if "email" in obj:
            return obj

    return None


def make_client_payload(uid, client_id, sub_id, expiry_ms):
    return {
        "id": client_id,
        "email": f"tg_{uid}",
        "subId": sub_id,
        "enable": True,
        "expiryTime": expiry_ms,
        "totalGB": 0,
        "limitIp": 0,
        "tgId": int(uid),
        "comment": f"Telegram {uid}",
    }


async def create_vpn(uid, days):
    global panel_session

    async with panel_lock:
        await panel_login()

        inbound = await panel_get_inbound()
        settings = inbound.get("settings", {})
        if isinstance(settings, str):
            import json
            settings = json.loads(settings)

        protocol = str(inbound.get("protocol", "")).lower()
        logging.info(
            "Создание клиента: inbound=%s protocol=%s",
            INBOUND_ID,
            protocol,
        )

        client_id = str(uuid.uuid4())
        sub_id = uuid.uuid4().hex[:16]
        email = f"tg_{uid}"
        now = datetime.now(timezone.utc)
        expiry_dt = now + timedelta(days=days)
        expiry_ms = int(expiry_dt.timestamp() * 1000)

        client = make_client_payload(
            uid, client_id, sub_id, expiry_ms
        )

        # Новый API 3X-UI: /panel/api/clients/add.
        # Именно его используем первым. Старые панели могут вернуть 404 —
        # тогда ниже используется старый /inbounds/addClient.
        modern_url = f"{PANEL_URL}/panel/api/clients/add"
        modern_payload = {
            "client": client,
            "inboundIds": [INBOUND_ID],
        }

        status, data, text = await panel_request_json(
            "POST",
            modern_url,
            modern_payload,
        )

        created = False

        if status in (200, 201) and data.get("success") is not False:
            created = True
            logging.info(
                "3X-UI modern API: клиент создан через /clients/add"
            )

        elif status == 404:
            logging.warning(
                "3X-UI /clients/add вернул 404; "
                "пробуем legacy /inbounds/addClient"
            )

            import json

            legacy_client = dict(client)

            # Для legacy API безопаснее передать только известные
            # универсальные поля + UUID/email/subId.
            legacy_payload = {
                "id": INBOUND_ID,
                "settings": json.dumps(
                    {"clients": [legacy_client]},
                    ensure_ascii=False,
                ),
            }

            legacy_url = f"{PANEL_URL}/panel/api/inbounds/addClient"

            status, data, text = await panel_request_json(
                "POST",
                legacy_url,
                legacy_payload,
            )

            if status == 200 and data.get("success") is not False:
                created = True
                logging.info(
                    "3X-UI legacy API: клиент создан через /inbounds/addClient"
                )

        if not created:
            raise RuntimeError(
                "Ошибка создания VPN в 3X-UI: "
                f"HTTP {status} {text[:1000]}"
            )

        # Проверяем, что клиент реально появился.
        saved_client = await get_client_by_email(email)
        if saved_client:
            client_id = str(saved_client.get("id") or client_id)
            sub_id = str(saved_client.get("subId") or sub_id)

        key = f"{PANEL_URL}/sub/{sub_id}"

        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET vpn_key=$1, vpn_client_id=$2, vpn_expires=$3
                WHERE telegram_id=$4
                """,
                key,
                client_id,
                expiry_dt,
                uid,
            )

        logging.info(
            "VPN успешно создан: telegram_id=%s client_id=%s "
            "sub_id=%s expires=%s",
            uid,
            client_id,
            sub_id,
            expiry_dt,
        )

        return key, expiry_dt


async def extend_vpn(uid, days):
    """
    Продлевает клиента через современный API 3X-UI.
    Если клиента больше нет — создаёт нового.
    """
    user = await get_user(uid)

    if not user or not user["vpn_client_id"]:
        return await create_vpn(uid, days)

    async with panel_lock:
        if panel_session is None or panel_session.closed:
            await panel_login()

        email = f"tg_{uid}"
        client = await get_client_by_email(email)

        # Если современный endpoint не доступен, ищем старым способом.
        if not client:
            inbound = await panel_get_inbound()
            settings = inbound.get("settings", {})
            if isinstance(settings, str):
                import json
                settings = json.loads(settings)

            clients = settings.get("clients", [])

            for item in clients:
                if str(item.get("id")) == str(user["vpn_client_id"]):
                    client = dict(item)
                    break

        if not client:
            return await create_vpn(uid, days)

        now = datetime.now(timezone.utc)
        old_expiry = user["vpn_expires"]
        base = old_expiry if old_expiry and old_expiry > now else now
        new_expiry = base + timedelta(days=days)

        client["enable"] = True
        client["expiryTime"] = int(new_expiry.timestamp() * 1000)
        client["email"] = email

        # Современный API обновляет клиента по email.
        modern_email = str(client.get("email") or email)
        modern_url = (
            f"{PANEL_URL}/panel/api/clients/update/"
            f"{modern_email}"
        )

        status, data, text = await panel_request_json(
            "POST",
            modern_url,
            client,
        )

        updated = status in (200, 201) and data.get("success") is not False

        if not updated and status == 404:
            # Legacy API.
            import json

            legacy_payload = {
                "id": INBOUND_ID,
                "settings": json.dumps(
                    {"clients": [client]},
                    ensure_ascii=False,
                ),
            }

            legacy_url = (
                f"{PANEL_URL}/panel/api/inbounds/updateClient/"
                f"{user['vpn_client_id']}"
            )

            status, data, text = await panel_request_json(
                "POST",
                legacy_url,
                legacy_payload,
            )

            updated = (
                status == 200
                and data.get("success") is not False
            )

        if not updated:
            raise RuntimeError(
                "Ошибка продления VPN: "
                f"HTTP {status} {text[:1000]}"
            )

        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET vpn_expires=$1
                WHERE telegram_id=$2
                """,
                new_expiry,
                uid,
            )

        # Сохраняем текущий ключ. Если subId есть — строим корректную
        # subscription URL.
        sub_id = str(client.get("subId") or "").strip()
        vpn_key = (
            f"{PANEL_URL}/sub/{sub_id}"
            if sub_id
            else user["vpn_key"]
        )

        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET vpn_key=$1
                WHERE telegram_id=$2
                """,
                vpn_key,
                uid,
            )

        return vpn_key, new_expiry


# =========================================================
# /start
# =========================================================
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    user = await register_user(msg)

    await msg.answer(
        "🔐 Moonlight VPN\n\n"
        "👋 Добро пожаловать в Moonlight VPN!\n\n"
        "⚡ Быстрый и стабильный VPN для ваших устройств.\n\n"
        "⭐️ Новостной канал — @moonlight_vpn_news\n"
        "⭐️ Техническая Поддержка — @mtfunit\n\n"
        "👇 Выберите действие:",
        reply_markup=main_menu()
    )


# =========================================================
# БАЛАНС
# =========================================================
@dp.message_handler(lambda m: m.text == "💰 Баланс")
async def balance(msg: types.Message):
    user = await register_user(msg)

    await msg.answer(
        f"💰 Баланс: {float(user['balance']):.2f} ₽\n\n"
        f"🧾 Код для пополнения: `{user['payment_code']}`",
        parse_mode="Markdown"
    )


# =========================================================
# ПОПОЛНЕНИЕ
# =========================================================
@dp.message_handler(lambda m: m.text == "💳 Купить/Продлить")
async def buy(msg: types.Message):
    await register_user(msg)

    text = (
        "💳 Выбери тариф:\n\n"
        "5 дней — 19 ₽\n"
        "14 дней — 49 ₽\n"
        "30 дней — 99 ₽\n\n"
        "Если на балансе недостаточно денег, сначала пополни его."
    )

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(
        KeyboardButton("5 дней — 19 ₽"),
        KeyboardButton("14 дней — 49 ₽"),
    )
    kb.row(
        KeyboardButton("30 дней — 99 ₽"),
    )
    kb.row(
        KeyboardButton("💰 Баланс"),
        KeyboardButton("◀️ Главное меню"),
    )

    pay_kb = InlineKeyboardMarkup()
    pay_kb.add(
        InlineKeyboardButton("💰 Пополнить баланс", url=DA_URL)
    )

    user = await get_user(msg.from_user.id)
    await msg.answer(
        f"💳 Твой баланс: {float(user['balance']):.2f} ₽\n\n"
        f"🧾 Для автоматического зачисления укажи в сообщении доната код:\n"
        f"`{user['payment_code']}`\n\n"
        "Можно отправить любую сумму в RUB.",
        parse_mode="Markdown",
        reply_markup=pay_kb
    )

    await msg.answer(text, reply_markup=kb)


@dp.message_handler(lambda m: m.text in {
    "5 дней — 19 ₽",
    "14 дней — 49 ₽",
    "30 дней — 99 ₽",
})
async def process_buy(msg: types.Message):
    uid = msg.from_user.id
    await register_user(msg)

    mapping = {
        "5 дней — 19 ₽": "5",
        "14 дней — 49 ₽": "14",
        "30 дней — 99 ₽": "30",
    }

    key = mapping[msg.text]
    tariff = TARIFFS[key]

    new_balance = await subtract_balance(uid, tariff["price"])

    if new_balance is None:
        user = await get_user(uid)
        await msg.answer(
            f"❌ Недостаточно средств.\n\n"
            f"Цена: {tariff['price']} ₽\n"
            f"Баланс: {float(user['balance']):.2f} ₽",
            reply_markup=main_menu()
        )
        return

    try:
        user = await get_user(uid)

        if user["vpn_client_id"]:
            vpn_key, expiry = await extend_vpn(uid, tariff["days"])
        else:
            vpn_key, expiry = await create_vpn(uid, tariff["days"])

        await msg.answer(
            "✅ VPN успешно активирован!\n\n"
            f"📅 Тариф: {tariff['days']} дней\n"
            f"💰 Списано: {tariff['price']} ₽\n"
            f"💳 Остаток: {float(new_balance):.2f} ₽\n\n"
            f"🔗 Ключ для подключения:\n{vpn_key}\n\n"
            f"⏳ Действует до: "
            f"{expiry.astimezone().strftime('%d.%m.%Y %H:%M')}",
            reply_markup=main_menu()
        )

    except Exception:
        # Возвращаем деньги, если панель не выдала VPN.
        await add_balance(uid, tariff["price"])

        logging.exception("Не удалось выдать VPN пользователю %s", uid)

        await msg.answer(
            "⚠️ Не удалось выдать VPN-подписку.\n"
            "Деньги возвращены на баланс.\n\n"
            "Проверь настройки панели.",
            reply_markup=main_menu()
        )


# =========================================================
# ПОДКЛЮЧИТЬСЯ
# =========================================================
@dp.message_handler(lambda m: m.text == "🚀 Подключиться")
async def connect(msg: types.Message):
    user = await register_user(msg)

    if not user["vpn_key"]:
        await msg.answer(
            "❌ У тебя пока нет активного VPN.\n"
            "Нажми «💳 Купить/Продлить».",
            reply_markup=main_menu()
        )
        return

    expiry = user["vpn_expires"]

    await msg.answer(
        "🚀 Твой VPN\n\n"
        f"🔗 Ключ:\n{user['vpn_key']}\n\n"
        f"⏳ До: "
        f"{expiry.astimezone().strftime('%d.%m.%Y %H:%M')}",
        reply_markup=main_menu()
    )


# =========================================================
# МОИ УСТРОЙСТВА
# =========================================================
@dp.message_handler(lambda m: m.text == "📱 Мои устройства")
async def devices(msg: types.Message):
    user = await register_user(msg)

    if not user["vpn_key"]:
        await msg.answer(
            "📱 У тебя пока нет подключённых устройств.",
            reply_markup=main_menu()
        )
        return

    await msg.answer(
        "📱 Мои устройства\n\n"
        "Доступно устройств: 5\n\n"
        f"🔗 Ключ:\n{user['vpn_key']}",
        reply_markup=main_menu()
    )


# =========================================================
# ПРОМОКОД
# =========================================================
@dp.message_handler(lambda m: m.text in {"🎟 Ввести промокод", "🎁 Промокод"})
async def promo(msg: types.Message):
    await register_user(msg)
    waiting_promo.add(msg.from_user.id)
    await msg.answer("🎟 Введи промокод:")


@dp.message_handler()
async def text_router(msg: types.Message):
    uid = msg.from_user.id

    if msg.text == "◀️ Главное меню":
        waiting_promo.discard(uid)
        waiting_days.discard(uid)
        await msg.answer(
            "👇 Выберите действие:",
            reply_markup=main_menu()
        )
        return

    if uid not in waiting_promo:
        return

    waiting_promo.remove(uid)
    code = msg.text.strip().upper()

    promo = PROMO_CODES.get(code)

    if not promo or promo["uses"] <= 0:
        await msg.answer(
            "❌ Неверный или законченный промокод.",
            reply_markup=main_menu()
        )
        return

    new_balance = await add_balance(uid, promo["amount"])
    promo["uses"] -= 1

    if promo["uses"] <= 0:
        del PROMO_CODES[code]

    await msg.answer(
        f"✅ Промокод активирован!\n\n"
        f"💰 +{promo['amount']} ₽\n"
        f"💳 Баланс: {float(new_balance):.2f} ₽",
        reply_markup=main_menu()
    )


# =========================================================
# STARTUP / SHUTDOWN
# =========================================================
async def on_startup(_):
    await init_db()
    logging.info("Database connected")

    # Фоновая проверка DonationAlerts.
    asyncio.create_task(donation_loop())

    logging.info("Bot started")


async def on_shutdown(_):
    global panel_session, db_pool

    if panel_session and not panel_session.closed:
        await panel_session.close()

    if db_pool:
        await db_pool.close()

    await bot.session.close()


if __name__ == "__main__":
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
    )
