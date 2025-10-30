"""基于 qfluentwidgets 的配置管理"""

from enum import StrEnum

from qfluentwidgets import BoolValidator, ConfigItem, ConfigValidator, EnumSerializer, OptionsConfigItem, OptionsValidator, QConfig, qconfig
from schema.const import SUPPORTED_SERVICES,ServiceType

class ConfigGroup(StrEnum):
    """配置分组名称"""

    BILI_SERVICE = "BiliService"
    TTS_SERVICE = "TTSService"
    PLAYER = "Player"


class ConfigKey(StrEnum):
    """配置项名称"""

    # B站直播服务
    ROOM_ID = "RoomId"
    GIFT_THRESHOLD = "GiftThreshold"
    NORMAL_DANMAKU_ON = "NormalDanmakuOn"
    GUARD_ON = "GuardOn"
    SUPER_CHAT_ON = "SuperChatOn"
    WELCOME_ON = "WelcomeOn"
    DEBUG = "Debug"

    # TTS 服务
    MINIMAX_API_KEY = "MinimaxApiKey"
    MINIMAX_VOICE_ID = "MinimaxVoiceId"
    FISH_SPEECH_URL = "FishSpeechUrl"
    GPT_SOVITS_URL = "GptSovitsUrl"
    ACTIVE_TTS = "ActiveTTS"

    # 播放器
    PLAYER_DEVICE = "PlayerDevice"


class IntValidator(ConfigValidator):
    """整数验证器

    验证配置值是否为整数类型，不限制范围。
    """

    def validate(self, value) -> bool:
        """验证值是否为整数"""
        return isinstance(value, int)

    def correct(self, value):
        """将值修正为整数"""
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0


class Config(QConfig):
    """应用配置类

    使用 qfluentwidgets 的 QConfig 系统管理配置。
    """

    # B站直播服务配置
    roomId = ConfigItem(
        ConfigGroup.BILI_SERVICE,
        ConfigKey.ROOM_ID,
        213,  # 默认值
        IntValidator(),
    )

    giftThreshold = ConfigItem(
        ConfigGroup.BILI_SERVICE,
        ConfigKey.GIFT_THRESHOLD,
        5,  # 默认值：5元
        IntValidator(),
    )

    normalDanmakuOn = ConfigItem(
        ConfigGroup.BILI_SERVICE,
        ConfigKey.NORMAL_DANMAKU_ON,
        False,  # 默认值
        BoolValidator(),
    )

    guardOn = ConfigItem(
        ConfigGroup.BILI_SERVICE,
        ConfigKey.GUARD_ON,
        True,  # 默认值
        BoolValidator(),
    )

    superChatOn = ConfigItem(
        ConfigGroup.BILI_SERVICE,
        ConfigKey.SUPER_CHAT_ON,
        True,  # 默认值
        BoolValidator(),
    )

    welcomeOn = ConfigItem(
        ConfigGroup.BILI_SERVICE,
        ConfigKey.WELCOME_ON,
        True,  # 默认值
        BoolValidator(),
    )

    debug = ConfigItem(
        ConfigGroup.BILI_SERVICE,
        ConfigKey.DEBUG,
        False,  # 默认值
        BoolValidator(),
    )

    # TTS 服务配置
    minimaxApiKey = ConfigItem(
        ConfigGroup.TTS_SERVICE,
        ConfigKey.MINIMAX_API_KEY,
        "",  # 默认值
    )

    minimaxVoiceId = ConfigItem(
        ConfigGroup.TTS_SERVICE,
        ConfigKey.MINIMAX_VOICE_ID,
        "",  # 默认值
    )

    fishSpeechUrl = ConfigItem(
        ConfigGroup.TTS_SERVICE,
        ConfigKey.FISH_SPEECH_URL,
        "http://localhost:8080/v1/tts",  # 默认值
    )

    gptSovitsUrl = ConfigItem(
        ConfigGroup.TTS_SERVICE,
        ConfigKey.GPT_SOVITS_URL,
        "http://localhost:19874",  # 默认值
    )

    # 播放器配置
    playerDevice = ConfigItem(
        ConfigGroup.PLAYER,
        ConfigKey.PLAYER_DEVICE,
        "",  # 默认值：留空为默认设备
    )

    activeTTS = OptionsConfigItem(
        ConfigGroup.TTS_SERVICE,
        ConfigKey.ACTIVE_TTS,
        [ServiceType.MINIMAX],  # 默认值
        OptionsValidator(list(SUPPORTED_SERVICES.keys())),
    )

# 创建全局配置实例
cfg = Config()

# 加载配置文件
qconfig.load("config/config.json", cfg)
