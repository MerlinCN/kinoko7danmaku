import asyncio
import json
import platform
import subprocess
from pathlib import Path

from bilibili_api import Credential, live
from loguru import logger

from audio_player import get_stream_player
from bilibili.model import (
    DanmuMessage,
    EventType,
    GiftMessage,
    GuardBuy,
    SuperChatMessage,
)
from config import config_manager


class BiliService:
    def __init__(self):
        login_biliup()
        self.credential: Credential = self.load_credential()
        self.room_obj: live.LiveDanmaku = live.LiveDanmaku(
            config_manager.config.room_id,
            credential=self.credential,
        )
        self.run_task = None
        self.add_event_listener()

    def add_event_listener(self):
        @self.room_obj.on(EventType.DANMU_MSG.value)
        async def on_danmaku(event):
            if not config_manager.config.normal_danmaku_on:
                return
            danmu_message = DanmuMessage.parse(event)
            stream_player = get_stream_player()
            await stream_player.play_from_text(
                config_manager.config.danmaku_on_text.format(
                    user_name=danmu_message.user_name, message=danmu_message.message
                )
            )
            logger.info(danmu_message)

        @self.room_obj.on(EventType.SEND_GIFT.value)
        async def on_send_gift(event):
            gift_message = GiftMessage.parse(event)
            if (
                gift_message.gift_price / 1000 * gift_message.gift_num
                < config_manager.config.gift_threshold
            ):
                return
            stream_player = get_stream_player()
            await stream_player.play_from_text(
                config_manager.config.gift_on_text.format(
                    user_name=gift_message.user_name,
                    gift_name=gift_message.gift_name,
                    gift_num=gift_message.gift_num,
                )
            )
            logger.info(gift_message)

        @self.room_obj.on(EventType.GUARD_BUY.value)
        async def on_guard_buy(event):
            if not config_manager.config.guard_on:
                return
            guard_buy_message = GuardBuy.parse(event)
            stream_player = get_stream_player()
            await stream_player.play_from_text(
                config_manager.config.guard_on_text.format(
                    user_name=guard_buy_message.user_name,
                    guard_name=guard_buy_message.guard_level.name_cn,
                )
            )
            logger.info(guard_buy_message)

        @self.room_obj.on(EventType.SUPER_CHAT_MESSAGE.value)
        async def on_super_chat_message(event):
            if not config_manager.config.super_chat_on:
                return
            super_chat_message = SuperChatMessage.parse(event)
            stream_player = get_stream_player()
            await stream_player.play_from_text(
                config_manager.config.super_chat_on_text.format(
                    user_name=super_chat_message.user_name,
                    message=super_chat_message.message,
                )
            )
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

    async def run(self):
        self.run_task = asyncio.create_task(self.room_obj.connect())

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


# 全局变量存储服务实例
bili_service = BiliService()


def get_bili_service():
    return bili_service
