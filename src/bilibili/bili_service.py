import asyncio
import json

from bilibili_api import Credential, live, user
from loguru import logger
from PySide6.QtCore import QObject, QTimer, Signal

from core.const import COOKIES_PATH
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


class BiliService(QObject):
    """B站直播服务

    处理B站直播连接和事件监听。
    """

    # 定义信号
    danmaku_received = Signal(str)  # 弹幕消息信号
    gift_received = Signal(str)  # 礼物消息信号
    guard_received = Signal(str)  # 舰长消息信号
    superchat_received = Signal(str)  # SC 消息信号

    def __init__(self):
        super().__init__()
        self.credential: Credential | None = None
        self.room_obj: live.LiveDanmaku | None = None
        self.run_task = None
        self.status_check_timer: QTimer | None = None

    def _check_room_status(self):
        """检查直播间状态，如果关闭则重新连接"""
        if not self.run_task or not self.room_obj:
            return
        if self.room_obj.get_status() == live.LiveDanmaku.STATUS_CLOSED:
            logger.warning("检测到直播间连接已关闭，正在尝试重新连接...")
            self.run_task.cancel()
            self.room_obj = live.LiveDanmaku(
                cfg.roomId.value,
                credential=self.credential,
            )
            self.add_event_listener()
            self.run_task = asyncio.create_task(self.room_obj.connect())
            logger.info("已重新创建直播间连接任务")

    def add_event_listener(self):
        @self.room_obj.on(EventType.DANMU_MSG)
        async def on_danmaku(event):
            if not cfg.normalDanmakuOn.value:
                return
            danmu_message = DanmuMessage.parse(event)
            logger.info(danmu_message)

            # 发射信号到 GUI
            display_text = cfg.danmakuOnText.value.format(
                user_name=danmu_message.user_name, message=danmu_message.message
            )
            self.danmaku_received.emit(display_text)

            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(display_text)
            await audio_player.play_bytes_async(audio)

        @self.room_obj.on(EventType.SEND_GIFT)
        async def on_send_gift(event):
            gift_message = GiftMessage.parse(event)
            if not cfg.freeGiftOn.value and gift_message.coin_type == "silver":
                return
            if (
                gift_message.gift_price / 1000 * gift_message.gift_num
                < cfg.giftThreshold.value
            ):
                return
            logger.info(gift_message)

            # 发射信号到 GUI
            display_text = cfg.giftOnText.value.format(
                user_name=gift_message.user_name,
                gift_name=gift_message.gift_name,
                gift_num=gift_message.gift_num,
            )
            self.gift_received.emit(display_text)

            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(display_text)
            await audio_player.play_bytes_async(audio)

        @self.room_obj.on(EventType.GUARD_BUY)
        async def on_guard_buy(event):
            if not cfg.guardOn.value:
                return
            guard_buy_message = GuardBuy.parse(event)
            logger.info(guard_buy_message)

            # 发射信号到 GUI
            display_text = cfg.guardOnText.value.format(
                user_name=guard_buy_message.user_name,
                guard_name=guard_buy_message.guard_level.name_cn,
            )
            self.guard_received.emit(display_text)

            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(display_text)
            await audio_player.play_bytes_async(audio)

        @self.room_obj.on(EventType.SUPER_CHAT_MESSAGE)
        async def on_super_chat_message(event):
            if not cfg.superChatOn.value:
                return
            super_chat_message = SuperChatMessage.parse(event)
            logger.info(super_chat_message)

            # 发射信号到 GUI
            display_text = cfg.superChatOnText.value.format(
                user_name=super_chat_message.user_name,
                message=super_chat_message.message,
            )
            self.superchat_received.emit(display_text)

            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(display_text)
            await audio_player.play_bytes_async(audio)

    def load_credential(self):
        with open(COOKIES_PATH, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        for cookie in cookies["cookie_info"]["cookies"]:
            if cookie["name"] == "bili_jct":
                bili_jct = cookie["value"]
            if cookie["name"] == "SESSDATA":
                sessdata = cookie["value"]
            if cookie["name"] == "DedeUserID":
                dedeuserid = cookie["value"]
        assert (
            bili_jct and sessdata and dedeuserid
        ), "cookies.json 中没有 bili_jct, SESSDATA, DedeUserID"
        self.credential = Credential(
            bili_jct=bili_jct, sessdata=sessdata, dedeuserid=dedeuserid
        )

    async def run(self):
        self.load_credential()
        self.room_obj = live.LiveDanmaku(
            cfg.roomId.value,
            credential=self.credential,
        )
        self.add_event_listener()
        self.run_task = asyncio.create_task(self.room_obj.connect())

        # 创建并启动状态检查定时器（必须在 Qt 事件循环启动后）
        if not self.status_check_timer:
            self.status_check_timer = QTimer(self)
            self.status_check_timer.timeout.connect(self._check_room_status)
            self.status_check_timer.setInterval(1000)  # 每秒检查一次
            self.status_check_timer.start()
            logger.info("状态检查定时器已启动")

    async def stop(self):
        if self.run_task:
            self.run_task.cancel()
            self.run_task = None
        if self.status_check_timer:
            self.status_check_timer.stop()
        logger.info("停止直播间监听")

    def is_logged_in(self) -> bool:
        return self.credential is not None

    async def logout(self):
        await self.stop()
        self.credential = None
        self.room_obj = None
        self.run_task = None
        if self.status_check_timer:
            self.status_check_timer.stop()
            self.status_check_timer = None
        if COOKIES_PATH.exists():
            COOKIES_PATH.unlink()

    async def get_self_info(self) -> dict:
        self_info = await user.get_self_info(credential=self.credential)
        return self_info


bili_service = BiliService()
