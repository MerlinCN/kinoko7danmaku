import http.cookies
import json
import logging
import os

import aiohttp

import blivedm.blivedm as blivedm
from config import gConfig
from danmaku_handler import BliveHandler
from event_handler import gEventHandler


logger = logging.getLogger("kinoko7danmaku")


async def run_client():
    room_id = gConfig.room_id
    assert room_id != 0
    cookies = http.cookies.SimpleCookie()
    os.system(r"bin\biliup.exe renew")
    with open("cookies.json", "r", encoding="utf-8") as f:
        tmp = json.load(f)
    sessdata = ""
    for value in tmp["cookie_info"]["cookies"]:
        if value["name"] == "SESSDATA":
            sessdata = value["value"]
            continue
    assert sessdata != ""
    cookies['SESSDATA'] = sessdata
    cookies['SESSDATA']['domain'] = 'bilibili.com'

    session = aiohttp.ClientSession()
    session.cookie_jar.update_cookies(cookies)
    client = blivedm.BLiveClient(room_id, session=session)
    handler = BliveHandler()

    client.set_handler(handler)
    client.start()
    await gEventHandler.trigger_client_init(client)
    try:
        await client.join()
    finally:
        await client.stop_and_close()
