import json
from pathlib import Path

from bilibili_api import Credential, live

from config import config_manager


class BiliService:
    def __init__(self):
        self.credential: Credential | None = None
        self.room_obj: live.LiveDanmaku | None = None

    @staticmethod
    def load_credential():
        cookies_path = Path("cookies.json")
        with open(cookies_path, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        for cookie in cookies["cookie_info"]["cookies"]:
            if cookie["name"] == "bili_jct":
                bili_jct = cookie["value"]
            if cookie["name"] == "SESSDATA":
                sessdata = cookie["value"]
            if cookie["name"] == "DedeUserID":
                dedeuserid = cookie["value"]
        assert bili_jct and sessdata and dedeuserid, (
            "cookies.json 中没有 bili_jct, SESSDATA, DedeUserID"
        )
        return Credential(
            bili_jct=bili_jct,
            sessdata=sessdata,
            dedeuserid=dedeuserid,
        )

    async def run(self):
        self.credential = self.load_credential()
        self.room_obj = live.LiveDanmaku(
            config_manager.config.room_id,
            credential=self.credential,
        )
        await self.room_obj.connect()
