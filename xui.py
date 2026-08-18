import aiohttp
import uuid
import json
from datetime import datetime, timedelta, timezone

from config import (
    PANEL_URL,
    PANEL_LOGIN,
    PANEL_PASSWORD,
    PANEL_API_TOKEN,
    INBOUND_ID,
    SUB_DOMAIN
)


session = None



async def panel_login():

    global session


    if session:
        await session.close()


    session = aiohttp.ClientSession(
        cookie_jar=aiohttp.CookieJar()
    )


    # Если есть API токен
    if PANEL_API_TOKEN:

        session.headers.update({

            "Authorization":
            f"Bearer {PANEL_API_TOKEN}",

            "Content-Type":
            "application/json"

        })

        return



    # Старый способ через логин

    async with session.post(

        f"{PANEL_URL}/login",

        json={

            "username": PANEL_LOGIN,

            "password": PANEL_PASSWORD

        }

    ) as r:


        data = await r.json(
            content_type=None
        )


        if not data.get("success"):

            raise Exception(
                "Ошибка входа в 3X-UI"
            )





async def request(
        method,
        url,
        data=None
):


    async with session.request(

        method,

        url,

        json=data

    ) as r:


        text = await r.text()


        try:
            return await r.json(
                content_type=None
            )

        except:

            return {
                "raw":text
            }







async def create_client(
        telegram_id,
        days,
        traffic
):


    await panel_login()



    client_uuid = str(
        uuid.uuid4()
    )


    sub_id = uuid.uuid4().hex[:16]


    expire = datetime.now(
        timezone.utc
    ) + timedelta(
        days=days
    )


    expire_ms = int(
        expire.timestamp()*1000
    )



    # 500 ГБ
    # 0 = безлимит


    total_gb = 0


    if traffic:

        total_gb = (
            traffic *
            1024 *
            1024 *
            1024
        )



    client = {


        "id":
        client_uuid,


        "email":
        f"tg_{telegram_id}",


        "enable":
        True,


        "expiryTime":
        expire_ms,


        "totalGB":
        total_gb,


        "limitIp":
        5,


        "subId":
        sub_id,


        "tgId":
        telegram_id,


        "comment":
        "Moonlight VPN"

    }




    payload = {


        "id":
        INBOUND_ID,


        "settings":
        json.dumps({

            "clients":[client]

        })

    }



    result = await request(

        "POST",

        f"{PANEL_URL}/panel/api/inbounds/addClient",

        payload

    )



    if result.get("success") is False:

        raise Exception(
            result
        )




    # ВАЖНО:
    # клиент получает только это


    subscribe = (
        f"{SUB_DOMAIN}"
        f"/sub/{sub_id}"
    )



    return {


        "client_id":
        client_uuid,


        "subscription":
        subscribe,


        "expire":
        expire,


        "sub_id":
        sub_id

  }
