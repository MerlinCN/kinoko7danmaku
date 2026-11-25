import asyncio
import json

from PySide6.QtCore import QObject, QTimer, Signal
from bilibili_api import Credential, live, user
from loguru import logger

from core.const import COOKIES_PATH
from core.player import audio_player
from core.qconfig import cfg
from models.bilibili import (
    ConnectionState,
    DanmuMessage,
    EventType,
    GiftMessage,
    GuardBuy,
    LiveMessage,
    LiveMessageType,
    SelfInfo,
    SessionStats,
    SuperChatMessage,
)
from tts_service import get_tts_service

from .gift_merger import gift_merger


class BiliService(QObject):
    """B站直播服务

    处理B站直播连接和事件监听，并向界面广播连接状态、会话统计与消息。
    """

    connection_state_changed = Signal(str)  # 连接状态（ConnectionState 的值）
    stats_changed = Signal(object)  # 会话统计（SessionStats）
    message_received = Signal(object)  # 直播消息（LiveMessage）
    session_started = Signal()  # 新的监听会话开始

    def __init__(self) -> None:
        super().__init__()
        self.credential: Credential | None = None
        self.room_obj: live.LiveDanmaku | None = None
        self.run_task: asyncio.Task[None] | None = None
        self.status_check_timer: QTimer | None = None
        self.connection_state = ConnectionState.DISCONNECTED
        self.stats = SessionStats()

    def _set_connection_state(self, state: ConnectionState) -> None:
        """更新连接状态并通知界面

        Args:
            state: 新的连接状态
        """
        if state == self.connection_state:
            return
        self.connection_state = state
        self.connection_state_changed.emit(state.value)

    def _reset_stats(self) -> None:
        """重置会话统计并通知界面开始新会话"""
        self.stats = SessionStats()
        self.stats_changed.emit(self.stats.model_copy())
        self.session_started.emit()

    def _emit_stats(self) -> None:
        """通知界面刷新会话统计"""
        self.stats_changed.emit(self.stats.model_copy())

    def _emit_message(self, message_type: LiveMessageType, text: str) -> None:
        """向界面发送直播消息

        Args:
            message_type: 消息类型
            text: 展示文本
        """
        self.message_received.emit(LiveMessage(type=message_type, text=text))

    def _check_room_status(self) -> None:
        """检查直播间状态，如果关闭则重新连接"""
        if not self.run_task or not self.room_obj:
            return

        status = self.room_obj.get_status()
        if status == live.LiveDanmaku.STATUS_ESTABLISHED:
            self._set_connection_state(ConnectionState.CONNECTED)
            return
        if status == live.LiveDanmaku.STATUS_ERROR:
            self._set_connection_state(ConnectionState.ERROR)
            return
        if status == live.LiveDanmaku.STATUS_CLOSED:
            self._set_connection_state(ConnectionState.CONNECTING)
            logger.warning('检测到直播间连接已关闭，正在尝试重新连接...')
            self.run_task.cancel()
            self.room_obj = live.LiveDanmaku(
                cfg.roomId.value,
                credential=self.credential,
            )
            self.add_event_listener()
            self.run_task = asyncio.create_task(self.room_obj.connect())
            logger.info('已重新创建直播间连接任务')
            return

        self._set_connection_state(ConnectionState.CONNECTING)

    def add_event_listener(self) -> None:
        @self.room_obj.on(EventType.DANMU_MSG)
        async def on_danmaku(event: dict[str, object]) -> None:
            self.stats.danmaku += 1
            self._emit_stats()

            danmu_message = DanmuMessage.parse(event)
            display_text = cfg.danmakuOnText.value.format(
                user_name=danmu_message.user_name, message=danmu_message.message
            )
            self._emit_message(LiveMessageType.DANMAKU, display_text)

            if not cfg.normalDanmakuOn.value:
                return
            logger.info(danmu_message)

            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(display_text)
            await audio_player.play_bytes_async(audio)

        @self.room_obj.on(EventType.SEND_GIFT)
        async def on_send_gift(event: dict[str, object]) -> None:
            self.stats.gift += 1
            self._emit_stats()

            gift_message = GiftMessage.parse(event)
            display_text = cfg.giftOnText.value.format(
                user_name=gift_message.user_name,
                gift_name=gift_message.gift_name,
                gift_num=gift_message.gift_num,
            )
            self._emit_message(LiveMessageType.GIFT, display_text)

            if not cfg.freeGiftOn.value and gift_message.coin_type == 'silver':
                return
            if gift_message.gift_price / 1000 * gift_message.gift_num < cfg.giftThreshold.value:
                return
            logger.info(gift_message)

            # 使用礼物合并管理器处理礼物（合并后由合并器负责 TTS）
            await gift_merger.add_gift(gift_message)

        @self.room_obj.on(EventType.GUARD_BUY)
        async def on_guard_buy(event: dict[str, object]) -> None:
            self.stats.guard += 1
            self._emit_stats()

            guard_buy_message = GuardBuy.parse(event)
            display_text = cfg.guardOnText.value.format(
                user_name=guard_buy_message.user_name,
                guard_name=guard_buy_message.guard_level.name_cn,
            )
            self._emit_message(LiveMessageType.GUARD, display_text)

            if not cfg.guardOn.value:
                return
            logger.info(guard_buy_message)

            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(display_text)
            await audio_player.play_bytes_async(audio)

        @self.room_obj.on(EventType.SUPER_CHAT_MESSAGE)
        async def on_super_chat_message(event: dict[str, object]) -> None:
            self.stats.super_chat += 1
            self._emit_stats()

            super_chat_message = SuperChatMessage.parse(event)
            display_text = cfg.superChatOnText.value.format(
                user_name=super_chat_message.user_name,
                message=super_chat_message.message,
            )
            self._emit_message(LiveMessageType.SUPER_CHAT, display_text)

            if not cfg.superChatOn.value:
                return
            if super_chat_message.price < cfg.superChatThreshold.value:
                return
            logger.info(super_chat_message)

            tts_service = get_tts_service()
            audio = await tts_service.text_to_speech(display_text)
            await audio_player.play_bytes_async(audio)

    def load_credential(self) -> None:
        with open(COOKIES_PATH, encoding='utf-8') as f:
            cookies = json.load(f)

        for cookie in cookies['cookie_info']['cookies']:
            if cookie['name'] == 'bili_jct':
                bili_jct = cookie['value']
            if cookie['name'] == 'SESSDATA':
                sessdata = cookie['value']
            if cookie['name'] == 'DedeUserID':
                dedeuserid = cookie['value']
        assert bili_jct and sessdata and dedeuserid, 'cookies.json 中没有 bili_jct, SESSDATA, DedeUserID'
        self.credential = Credential(bili_jct=bili_jct, sessdata=sessdata, dedeuserid=dedeuserid)

    async def run(self) -> None:
        self.load_credential()
        self._reset_stats()
        self._set_connection_state(ConnectionState.CONNECTING)
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
        logger.info('状态检查定时器已启动')

        # 启动礼物合并定时器（必须在 Qt 事件循环启动后）
        gift_merger.start()

    async def stop(self) -> None:
        if self.run_task:
            self.run_task.cancel()
            self.run_task = None
        if self.status_check_timer:
            self.status_check_timer.stop()
        self.room_obj = None
        self._set_connection_state(ConnectionState.DISCONNECTED)
        gift_merger.stop()
        await gift_merger.clear_all()
        logger.info('停止直播间监听')

    def is_logged_in(self) -> bool:
        return self.credential is not None

    async def logout(self) -> None:
        await self.stop()
        self.credential = None
        if self.status_check_timer:
            self.status_check_timer.stop()
            self.status_check_timer = None
        if COOKIES_PATH.exists():
            COOKIES_PATH.unlink()

    async def get_self_info(self) -> SelfInfo:
        info = await user.get_self_info(credential=self.credential)
        return SelfInfo(
            mid=int(info.get('mid', 0)),
            uname=info.get('name', ''),
            face=info.get('face', ''),
        )


bili_service = BiliService()
