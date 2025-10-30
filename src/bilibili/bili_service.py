import asyncio
import json
import platform
import subprocess
from pathlib import Path

from bilibili_api import Credential, live
from loguru import logger

from core import setting
from core.player import audio_player
from models.bilibili import (
    DanmuMessage,
    EventType,
    GiftMessage,
    GuardBuy,
    SuperChatMessage,
)
from tts_service import get_tts_service


class BiliService:
    def __init__(self):
        login_biliup()
        self.credential: Credential = self.load_credential()
        self.room_obj: live.LiveDanmaku = live.LiveDanmaku(
            setting.bili_service.room_id,
            credential=self.credential,
        )
        self.run_task = None
        self.add_event_listener()

    def add_event_listener(self):
        @self.room_obj.on(EventType.DANMU_MSG)
        async def on_danmaku(event):
            if not setting.bili_service.normal_danmaku_on:
                return
            danmu_message = DanmuMessage.parse(event)
            logger.info(danmu_message)
            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(
                setting.bili_service.danmaku_on_text.format(
                    user_name=danmu_message.user_name, message=danmu_message.message
                )
            )
            audio_player.play_bytes(audio)

        @self.room_obj.on(EventType.SEND_GIFT)
        async def on_send_gift(event):
            gift_message = GiftMessage.parse(event)
            if (
                gift_message.gift_price / 1000 * gift_message.gift_num
                < setting.bili_service.gift_threshold
            ):
                return
            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(
                setting.bili_service.gift_on_text.format(
                    user_name=gift_message.user_name,
                    gift_name=gift_message.gift_name,
                    gift_num=gift_message.gift_num,
                )
            )
            audio_player.play_bytes(audio)
            logger.info(gift_message)

        @self.room_obj.on(EventType.GUARD_BUY)
        async def on_guard_buy(event):
            if not setting.bili_service.guard_on:
                return
            guard_buy_message = GuardBuy.parse(event)
            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(
                setting.bili_service.guard_on_text.format(
                    user_name=guard_buy_message.user_name,
                    guard_name=guard_buy_message.guard_level.name_cn,
                )
            )
            audio_player.play_bytes(audio)
            logger.info(guard_buy_message)

        @self.room_obj.on(EventType.SUPER_CHAT_MESSAGE)
        async def on_super_chat_message(event):
            if not setting.bili_service.super_chat_on:
                return
            super_chat_message = SuperChatMessage.parse(event)
            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(
                setting.bili_service.super_chat_on_text.format(
                    user_name=super_chat_message.user_name,
                    message=super_chat_message.message,
                )
            )
            audio_player.play_bytes(audio)
            logger.info(super_chat_message)

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

    async def check_room_status(self):
        while True:
            await asyncio.sleep(1)
            if self.room_obj.get_status() == live.LiveDanmaku.STATUS_CLOSED:
                logger.error("直播间已关闭")
                self.run_task.cancel()
                self.room_obj = live.LiveDanmaku(
                    setting.bili_service.room_id,
                    credential=self.credential,
                )
                self.run_task = asyncio.create_task(self.room_obj.connect())

    async def run(self):
        self.run_task = asyncio.create_task(self.room_obj.connect())
        asyncio.create_task(self.check_room_status())

    async def reload(self, room_id: int):
        if self.run_task:
            self.run_task.cancel()
        self.room_obj: live.LiveDanmaku = live.LiveDanmaku(
            room_id, credential=self.credential
        )
        self.add_event_listener()
        self.run_task = asyncio.create_task(self.room_obj.connect())


def login_biliup():
    biliup_path = Path("bin") / "biliup.exe"
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        biliup_path = Path("bin") / "biliup-aarch64-macos"

    cookies_path = Path("cookies.json")
    if cookies_path.exists():
        # todo: 做登录校验
        subprocess.run([biliup_path, "renew"])
        return

    subprocess.run(
        [
            biliup_path,
            "login",
        ]
    )


bili_service = BiliService()
