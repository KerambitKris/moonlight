import os


BOT_TOKEN = os.getenv("BOT_TOKEN")

DATABASE_URL = os.getenv("DATABASE_URL")


# 3X-UI
PANEL_URL = os.getenv("PANEL_URL", "").rstrip("/")
PANEL_LOGIN = os.getenv("PANEL_LOGIN")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD")
PANEL_API_TOKEN = os.getenv("PANEL_API_TOKEN")

INBOUND_ID = int(os.getenv("INBOUND_ID", "1"))


# Твой красивый домен подписок
SUB_DOMAIN = os.getenv(
    "SUB_DOMAIN",
    "https://moonlight-vpn.ru"
)


if not BOT_TOKEN:
    raise Exception("Нет BOT_TOKEN")

if not DATABASE_URL:
    raise Exception("Нет DATABASE_URL")

if not PANEL_URL:
    raise Exception("Нет PANEL_URL")
