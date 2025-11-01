import asyncio
import json
from pathlib import Path

from bilibili_api import Credential, live, user
from loguru import logger

from core.player import audio_player
from core.qconfig import cfg
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
        self.credential: Credential | None = None
        self.room_obj: live.LiveDanmaku | None = None
        self.run_task = None
        self.check_room_status_task = None

    def add_event_listener(self):
        @self.room_obj.on(EventType.DANMU_MSG)
        async def on_danmaku(event):
            if not cfg.normalDanmakuOn.value:
                return
            danmu_message = DanmuMessage.parse(event)
            logger.info(danmu_message)
            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(
                cfg.danmakuOnText.value.format(
                    user_name=danmu_message.user_name, message=danmu_message.message
                )
            )
            audio_player.play_bytes(audio)

        @self.room_obj.on(EventType.SEND_GIFT)
        async def on_send_gift(event):
            gift_message = GiftMessage.parse(event)
            if (
                gift_message.gift_price / 1000 * gift_message.gift_num
                < cfg.giftThreshold.value
            ):
                return
            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(
                cfg.giftOnText.value.format(
                    user_name=gift_message.user_name,
                    gift_name=gift_message.gift_name,
                    gift_num=gift_message.gift_num,
                )
            )
            audio_player.play_bytes(audio)
            logger.info(gift_message)

        @self.room_obj.on(EventType.GUARD_BUY)
        async def on_guard_buy(event):
            if not cfg.guardOn.value:
                return
            guard_buy_message = GuardBuy.parse(event)
            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(
                cfg.guardOnText.value.format(
                    user_name=guard_buy_message.user_name,
                    guard_name=guard_buy_message.guard_level.name_cn,
                )
            )
            audio_player.play_bytes(audio)
            logger.info(guard_buy_message)

        @self.room_obj.on(EventType.SUPER_CHAT_MESSAGE)
        async def on_super_chat_message(event):
            if not cfg.superChatOn.value:
                return
            super_chat_message = SuperChatMessage.parse(event)
            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(
                cfg.superChatOnText.value.format(
                    user_name=super_chat_message.user_name,
                    message=super_chat_message.message,
                )
            )
            audio_player.play_bytes(audio)
            logger.info(super_chat_message)

    def load_credential(self):
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
        self.credential = Credential(
            bili_jct=bili_jct, sessdata=sessdata, dedeuserid=dedeuserid
        )

    async def check_room_status(self):
        while True:
            await asyncio.sleep(1)
            if self.room_obj.get_status() == live.LiveDanmaku.STATUS_CLOSED:
                logger.error("直播间已关闭")
                self.run_task.cancel()
                self.room_obj = live.LiveDanmaku(
                    cfg.roomId.value,
                    credential=self.credential,
                )
                self.run_task = asyncio.create_task(self.room_obj.connect())

    async def run(self):
        self.load_credential()
        self.room_obj = live.LiveDanmaku(
            cfg.roomId.value,
            credential=self.credential,
        )
        self.add_event_listener()
        self.run_task = asyncio.create_task(self.room_obj.connect())
        self.check_room_status_task = asyncio.create_task(self.check_room_status())

    async def stop(self):
        if self.run_task:
            self.run_task.cancel()
        if self.check_room_status_task:
            self.check_room_status_task.cancel()
        logger.info("停止直播间监听")

    def is_logged_in(self) -> bool:
        return self.credential is not None

    async def logout(self):
        await self.stop()
        self.credential = None
        self.room_obj = None
        self.run_task = None
        self.check_room_status_task = None
        cookies_path = Path("cookies.json")
        if cookies_path.exists():
            cookies_path.unlink()

    async def reload(self):
        if self.run_task:
            self.run_task.cancel()
        if self.check_room_status_task:
            self.check_room_status_task.cancel()
        self.load_credential()
        self.room_obj = live.LiveDanmaku(cfg.roomId.value, credential=self.credential)
        self.add_event_listener()
        self.run_task = asyncio.create_task(self.room_obj.connect())
        self.check_room_status_task = asyncio.create_task(self.check_room_status())

    async def get_self_info(self) -> dict:
        self_info = await user.get_self_info(credential=self.credential)
        return self_info


bili_service = BiliService()
