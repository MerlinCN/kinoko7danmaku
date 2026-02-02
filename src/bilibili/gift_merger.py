"""礼物合并管理器

用于合并短时间内相同类型和数量的礼物，减少 TTS 播报频率。
"""

from time import time

from loguru import logger
from pydantic import BaseModel, Field
from PySide6.QtCore import QObject, QTimer, Signal
from qasync import asyncSlot

from core.player import audio_player
from core.qconfig import cfg
from models.bilibili import GiftMessage
from tts_service import get_tts_service


class UserGiftGroup(BaseModel):
    """单用户礼物组数据类

    存储单个用户连续赠送的同一种礼物信息，用于合并同一用户短时间内的礼物。
    窗口时间会随着礼物数量的增加而递增，直到达到最大窗口时间。
    """

    user_name: str = Field(description="用户名")
    gift_name: str = Field(description="礼物名称")
    total_num: int = Field(description="累计礼物数量")
    first_time: float = Field(
        default_factory=time, description="第一次收到礼物的时间戳"
    )
    last_update_time: float = Field(
        default_factory=time, description="最后一次更新的时间戳"
    )
    current_window: float = Field(description="当前窗口时间（秒）")


class GiftMerger(QObject):
    """礼物合并管理器

    管理单用户礼物合并逻辑：合并同一用户短时间内赠送的相同礼物。
    使用单个 QTimer 定期检查所有礼物组，而不是为每个礼物组创建单独的任务。

    Attributes:
        user_gift_groups: 单用户礼物组字典，key 为 (用户名, 礼物名称)
        check_timer: 定时器，每秒检查一次所有礼物组

    Signals:
        merged_gift_received(str): 发送合并后的文本到 GUI
    """

    merged_gift_received = Signal(str)

    def __init__(self):
        """初始化礼物合并管理器

        创建单用户礼物组字典和定时器。
        定时器每秒触发一次，检查所有礼物组的状态。
        """
        super().__init__()
        self.user_gift_groups: dict[tuple[str, str], UserGiftGroup] = {}

        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self._check_gift_groups)
        # 不在这里启动，等待 Qt 事件循环启动后再调用 start()

    def start(self) -> None:
        """启动定时器

        必须在 Qt 事件循环启动后调用，否则定时器不会触发。
        """
        if not self.check_timer.isActive():
            self.check_timer.start(1000)
            logger.info("礼物检查定时器已启动")

    def stop(self) -> None:
        """停止定时器"""
        if self.check_timer.isActive():
            self.check_timer.stop()
            logger.info("礼物检查定时器已停止")

    async def add_gift(self, gift_message: GiftMessage):
        """添加礼物到合并队列

        如果开启礼物合并，将礼物添加到单用户礼物组；否则直接播报。

        Args:
            gift_message: 礼物消息对象
        """
        if cfg.giftMergeOn.value:
            await self._add_to_user_gift_group(gift_message)
        else:
            await self._process_single_gift(gift_message)

    async def _add_to_user_gift_group(self, gift_message: GiftMessage):
        """添加礼物到单用户礼物组

        如果是新礼物组，使用初始窗口时间；
        如果是追加礼物，递增窗口时间直到最大值。

        Args:
            gift_message: 礼物消息对象
        """
        user_key = (gift_message.user_name, gift_message.gift_name)

        if user_key not in self.user_gift_groups:
            # 创建新的单用户礼物组，使用初始窗口时间
            initial_window = cfg.giftMergeWindowInitial.value
            self.user_gift_groups[user_key] = UserGiftGroup(
                user_name=gift_message.user_name,
                gift_name=gift_message.gift_name,
                total_num=gift_message.gift_num,
                current_window=initial_window,
            )
            logger.debug(
                f"创建新单用户礼物组: {gift_message.user_name} - {gift_message.gift_name} "
                f"x{gift_message.gift_num}，初始窗口时间: {initial_window}s"
            )
        else:
            # 累加数量并递增窗口时间
            user_gift_group = self.user_gift_groups[user_key]
            user_gift_group.total_num += gift_message.gift_num
            user_gift_group.last_update_time = time()

            # 递增窗口时间，但不超过最大窗口时间
            max_window = cfg.giftMergeWindow.value
            increment = cfg.giftMergeWindowIncrement.value
            user_gift_group.current_window = min(
                user_gift_group.current_window + increment, max_window
            )

            logger.debug(
                f"累加礼物到单用户礼物组 {user_key}，当前总数: {user_gift_group.total_num}，"
                f"当前窗口时间: {user_gift_group.current_window}s"
            )

    @asyncSlot()
    async def _check_gift_groups(self):
        """定时检查所有礼物组，处理满足条件的组

        由 QTimer 每秒触发一次，检查单用户礼物组的窗口期。
        每个礼物组使用自己的动态窗口时间（会随着礼物数量递增，直到最大窗口时间）。
        """
        if not cfg.giftMergeOn.value:
            return

        current_time = time()
        user_keys_to_process = []

        for user_key, user_gift_group in self.user_gift_groups.items():
            # 使用该礼物组的当前窗口时间（动态递增的）
            time_since_last_update = current_time - user_gift_group.last_update_time
            if time_since_last_update >= user_gift_group.current_window:
                logger.debug(
                    f"单用户礼物组 {user_key} 窗口期结束（窗口时间: {user_gift_group.current_window}s），处理"
                )
                user_keys_to_process.append(user_key)

        # 处理收集到的单用户礼物组
        for user_key in user_keys_to_process:
            await self._process_user_gift_group(user_key)

    async def _process_user_gift_group(self, user_key: tuple[str, str]):
        """处理单用户礼物组，合并单个用户的礼物并播报

        从字典中取出单用户礼物组，格式化文本后发送信号到 GUI 并进行 TTS 播报。

        Args:
            user_key: 单用户礼物组的键 (user_name, gift_name)
        """
        if user_key not in self.user_gift_groups:
            return

        user_gift_group = self.user_gift_groups.pop(user_key)

        logger.info(
            f"处理单用户礼物组: {user_gift_group.user_name} - {user_gift_group.gift_name} "
            f"x{user_gift_group.total_num}"
        )

        # 创建合并后的 GiftMessage 并直接播报
        merged_gift = GiftMessage(
            user_name=user_gift_group.user_name,
            gift_name=user_gift_group.gift_name,
            gift_num=user_gift_group.total_num,
        )
        await self._process_single_gift(merged_gift)

    async def _process_single_gift(self, gift_message: GiftMessage):
        """处理单个礼物（不合并）

        当礼物合并功能关闭时调用，直接格式化文本并播报，不进行合并。

        Args:
            gift_message: 礼物消息对象
        """
        display_text = cfg.giftOnText.value.format(
            user_name=gift_message.user_name,
            gift_name=gift_message.gift_name,
            gift_num=gift_message.gift_num,
        )

        # 发射信号到 GUI
        self.merged_gift_received.emit(display_text)

        # 发送 TTS
        tts_service = get_tts_service()
        audio = await tts_service.text_to_speech(display_text)
        await audio_player.play_bytes_async(audio)

    async def clear_all(self):
        """清空所有礼物组

        清除字典中所有未处理的单用户礼物组。
        通常在停止监听或重新连接时调用。
        """
        self.user_gift_groups.clear()
        logger.info("清空所有礼物组")


# 创建全局礼物合并管理器实例
gift_merger = GiftMerger()
