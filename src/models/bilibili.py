import json
import time
from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field


class GuardLevel(Enum):
    """舰长等级枚举
    1: 总督
    2: 提督
    3: 舰长
    """

    NONE = 0  # 非舰长
    GOVERNOR = 1  # 总督
    LIEUTENANT = 2  # 提督
    CAPTAIN = 3  # 舰长

    @property
    def name_cn(self) -> str:
        """获取中文名称"""
        name_map = {
            GuardLevel.NONE: "非舰长",
            GuardLevel.GOVERNOR: "总督",
            GuardLevel.LIEUTENANT: "提督",
            GuardLevel.CAPTAIN: "舰长",
        }
        return name_map.get(self, "未知等级")


class EventType(str, Enum):
    """事件类型枚举"""

    DANMU_MSG = "DANMU_MSG"  # 弹幕
    SEND_GIFT = "SEND_GIFT"  # 礼物
    GUARD_BUY = "GUARD_BUY"  # 舰长
    SUPER_CHAT_MESSAGE = "SUPER_CHAT_MESSAGE"  # 醒目留言


class DanmuMessage(BaseModel):
    room_id: int = Field(default=0, description="房间 ID")
    user_mid: int = Field(default=0, description="用户 ID")
    user_name: str = Field(default="", description="用户名")
    message: str = Field(default="", description="弹幕内容")
    user_face: str = Field(default="", description="用户头像")
    fans_medal_name: str = Field(default="", description="粉丝勋章")
    fans_medal_level: int = Field(default=0, description="粉丝勋章等级")
    guard_level: GuardLevel = Field(default=GuardLevel.NONE, description="舰队等级")
    reply_mid: int = Field(default=0, description="回复用户 ID")
    reply_uname: str = Field(default="", description="回复用户名")
    timestamp: int = Field(default=0, description="发送时的 UNIX 毫秒时间戳")
    emotion: Dict[str, str] = Field(
        default_factory=dict, description="表情相关信息 (用于文本替换)"
    )
    pic_emoticon: str = Field(default="", description="图片表情")

    @classmethod
    def parse(cls, event_data: Dict[str, Any]) -> "DanmuMessage":
        """
        解析弹幕信息
        Args:
            info: 弹幕信息
        Returns:
            DanmuMessage: 弹幕消息
        See: https://socialsisteryi.github.io/bilibili-API-collect/docs/live/message_stream.html#普通包
        """
        instance = cls()

        instance.room_id = int(event_data["room_display_id"])

        # 防空处理：检查 info 是否存在
        if "data" not in event_data or "info" not in event_data["data"]:
            return instance
        info = event_data["data"]["info"]
        instance.message = info[1]
        instance.timestamp = info[0][4]
        if info[0][15]:
            extra = json.loads(info[0][15].get("extra", "{}"))
        else:
            extra = {}
        emotion = extra.get("emots", {})
        if emotion:
            for k, v in emotion.items():
                instance.emotion[k] = v.get("url", "")
        if extra:
            show_reply = extra.get("show_reply", False)
            if show_reply:
                instance.reply_mid = extra.get("reply_mid", 0)
                instance.reply_uname = extra.get("reply_uname", "")
        instance.user_mid = info[2][0]
        instance.user_name = info[2][1]
        if info[0][15]:
            # 防空处理：使用 get 方法获取用户头像
            instance.user_face = (
                info[0][15].get("user", {}).get("base", {}).get("face", "")
            )
        if info[3]:
            instance.fans_medal_name = info[3][1]
            instance.fans_medal_level = info[3][0]
            instance.guard_level = GuardLevel(info[3][10])

        pic_emoticon = info[0][13]
        if isinstance(pic_emoticon, dict):
            instance.pic_emoticon = pic_emoticon.get("url", "")

        return instance

    def __str__(self):
        result = ""
        if self.guard_level.value:
            result += f"[{self.guard_level.name_cn}]"
        if self.fans_medal_name and self.fans_medal_level:
            result += f"[{self.fans_medal_name}({self.fans_medal_level})]"
        result += f"{self.user_name}:{self.message}"
        return result


class InteractType(Enum):
    """互动类型枚举
    1为进场，2为关注，3为分享"""

    ENTER = 1  # 进场
    FOLLOW = 2  # 关注
    SHARE = 3  # 分享


class InteractWord(BaseModel):
    room_id: int = Field(default=0, description="房间 ID")
    user_mid: int = Field(default=0, description="用户 ID")
    user_name: str = Field(default="", description="用户名")
    msg_type: InteractType = Field(default=InteractType.ENTER, description="互动类型")
    timestamp: int = Field(default=0, description="发送时的 UNIX 毫秒时间戳")

    @classmethod
    def parse(cls, event_data: Dict[str, Any]) -> "InteractWord":
        instance = cls()
        instance.room_id = int(event_data["room_display_id"])
        instance.user_mid = event_data["data"]["data"]["uid"]
        instance.user_name = event_data["data"]["data"]["uname"]
        instance.msg_type = InteractType(event_data["data"]["data"]["msg_type"])
        instance.timestamp = event_data["data"]["data"]["timestamp"]
        return instance


class GuardBuy(BaseModel):
    room_id: int = Field(default=0, description="房间 ID")
    user_mid: int = Field(default=0, description="用户 ID")
    user_name: str = Field(default="", description="用户名")
    guard_level: GuardLevel = Field(default=GuardLevel.CAPTAIN, description="舰队等级")
    num: int = Field(default=0, description="购买数量")
    price: int = Field(default=0, description="购买价格 CNY*1000")
    timestamp: int = Field(default=0, description="发送时的 UNIX 毫秒时间戳")

    @classmethod
    def parse(cls, event_data: Dict[str, Any]) -> "GuardBuy":
        instance = cls()
        data = event_data["data"]["data"]
        instance.room_id = int(event_data["room_display_id"])
        instance.user_mid = data["uid"]
        instance.user_name = data["username"]
        instance.guard_level = GuardLevel(data["guard_level"])
        instance.num = data["num"]
        instance.price = data["price"]
        instance.timestamp = int(time.time())
        return instance

    def __str__(self):
        return f"{self.user_name}[{self.user_mid}] 购买了 {self.guard_level.name_cn}，价值 {self.price} 元"


class SuperChatMessage(BaseModel):
    room_id: int = Field(default=0, description="房间 ID")
    user_mid: int = Field(default=0, description="用户 ID")
    user_name: str = Field(default="", description="用户名")
    price: int = Field(default=0, description="为 CNY 价值")
    message: str = Field(default="", description="消息内容")
    time: int = Field(default=0, description="消息持续时间")
    fans_medal_name: str = Field(default="", description="粉丝勋章")
    fans_medal_level: int = Field(default=0, description="粉丝勋章等级")
    guard_level: GuardLevel = Field(default=GuardLevel.CAPTAIN, description="舰队等级")
    user_face: str = Field(default="", description="用户头像")
    timestamp: int = Field(default=0, description="发送时的 UNIX 毫秒时间戳")

    @classmethod
    def parse(cls, event_data: Dict[str, Any]) -> "SuperChatMessage":
        instance = cls()
        instance.room_id = int(event_data["room_display_id"])
        data = event_data["data"]["data"]
        instance.user_mid = data["uid"]
        instance.user_name = data["user_info"]["uname"]
        instance.price = data["price"]
        instance.message = data["message"]
        instance.fans_medal_name = data["medal_info"]["medal_name"]
        instance.fans_medal_level = data["medal_info"]["medal_level"]
        instance.guard_level = GuardLevel(data["medal_info"]["guard_level"])
        instance.user_face = data["user_info"]["face"]
        instance.time = int(time.time())

        return instance

    def __str__(self):
        return f"{self.user_name}[{self.user_mid}] 发送了一条醒目留言，他说“{self.message}”，价值 {self.price} 元"


class GiftMessage(BaseModel):
    room_id: int = Field(default=0, description="房间 ID")
    user_mid: int = Field(default=0, description="用户 ID")
    user_name: str = Field(default="", description="用户名")
    gift_name: str = Field(default="", description="礼物名称")
    gift_num: int = Field(default=0, description="礼物数量")
    gift_price: int = Field(default=0, description="礼物价格 CNY*1000")
    timestamp: int = Field(default=0, description="发送时的 UNIX 毫秒时间戳")
    coin_type: str = Field(default="", description="付费类型")

    @classmethod
    def parse(cls, event_data: Dict[str, Any]) -> "GiftMessage":
        instance = cls()
        instance.room_id = int(event_data["room_display_id"])
        data = event_data["data"]["data"]
        instance.user_mid = data["uid"]
        instance.user_name = data["uname"]
        instance.gift_name = data["giftName"]
        instance.gift_num = data["num"]
        instance.gift_price = data["price"]
        instance.timestamp = int(time.time())
        instance.coin_type = data["coin_type"]
        return instance

    def __str__(self):
        return f"{self.user_name}[{self.user_mid}] 赠送了 {self.gift_num} 个 {self.gift_name}，价值 {self.gift_price} 元"


class OnlineCount(BaseModel):
    room_id: int = Field(default=0, description="房间 ID")
    online_count: int = Field(default=0, description="在线人数")
    timestamp: int = Field(default=0, description="发送时的 UNIX 毫秒时间戳")

    @classmethod
    def parse(cls, event_data: Dict[str, Any]) -> "OnlineCount":
        instance = cls()
        instance.room_id = int(event_data["room_display_id"])
        data = event_data["data"]["data"]
        instance.online_count = data["count"]
        instance.timestamp = int(time.time())
        return instance


class RoomBlockMsg(BaseModel):
    room_id: int = Field(default=0, description="房间 ID")
    user_mid: int = Field(default=0, description="用户 ID")
    user_name: str = Field(default="", description="用户名")
    timestamp: int = Field(default=0, description="发送时的 UNIX 毫秒时间戳")

    @classmethod
    def parse(cls, event_data: Dict[str, Any]) -> "RoomBlockMsg":
        instance = cls()
        instance.room_id = int(event_data["room_display_id"])
        data = event_data["data"]["data"]
        instance.user_mid = data["uid"]
        instance.user_name = data["uname"]
        instance.timestamp = int(time.time())
        return instance


class AnchorLotStart(BaseModel):
    room_id: int = Field(default=0, description="房间 ID")
    id: int = Field(default=0, description="ID")
    danmu: str = Field(default="", description="弹幕")
    gift_name: str = Field(default="", description="礼物名称")
    gift_num: int = Field(default=0, description="礼物数量")
    require_text: str = Field(default="", description="要求文本")
    timestamp: int = Field(default=0, description="发送时的 UNIX 毫秒时间戳")

    @classmethod
    def parse(cls, event_data: Dict[str, Any]) -> "AnchorLotStart":
        instance = cls()
        instance.room_id = int(event_data["room_display_id"])
        data = event_data["data"]["data"]
        instance.id = data["id"]
        instance.danmu = data["danmu"]
        instance.gift_name = data["gift_name"]
        instance.gift_num = data["gift_num"]
        instance.require_text = data["require_text"]
        instance.timestamp = int(time.time())
        return instance


class AnchorLotAward(BaseModel):
    room_id: int = Field(default=0, description="房间 ID")
    id: int = Field(default=0, description="ID")
    user_mid: int = Field(default=0, description="用户 ID")
    user_name: str = Field(default="", description="用户名")
    award_name: str = Field(default="", description="奖励名称")
    award_num: int = Field(default=0, description="奖励数量")
    timestamp: int = Field(default=0, description="发送时的 UNIX 毫秒时间戳")

    @classmethod
    def parse(cls, event_data: Dict[str, Any]) -> "AnchorLotAward":
        instance = cls()
        instance.room_id = int(event_data["room_display_id"])
        data = event_data["data"]["data"]
        instance.id = event_data["data"]["id"]
        instance.user_mid = data["user_info"]["uid"]
        instance.user_name = data["user_info"]["uname"]
        instance.award_name = data["award_name"]
        instance.award_num = data["award_num"]
        instance.timestamp = int(time.time())
        return instance
