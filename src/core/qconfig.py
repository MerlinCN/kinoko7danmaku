"""基于 qfluentwidgets 的配置管理"""

from enum import StrEnum
from typing import override

import httpx
from qfluentwidgets import (
    BoolValidator,
    ConfigItem,
    ConfigValidator,
    OptionsConfigItem,
    OptionsValidator,
    QConfig,
    RangeConfigItem,
    RangeValidator,
    qconfig,
)

from models.service import ServiceType

from .const import (
    GPT_SOVITS_LANGUAGES,
    GPT_SOVITS_TEXT_SPLIT_METHODS,
    MINIMAX_ERROR_VOICE_ID,
    MINIMAX_MODELS,
    MINIMAX_VOICE_IDS,
    SUPPORTED_SERVICES,
)
from .player import audio_player


class ConfigGroup(StrEnum):
    """配置分组名称"""

    BILI_SERVICE = "BiliService"
    TTS_SERVICE = "TTSService"
    MINIMAX_SERVICE = "MinimaxService"
    FISH_SPEECH_SERVICE = "FishSpeechService"
    GPT_SOVITS_SERVICE = "GptSovitsService"
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
    GIFT_ON_TEXT = "GiftOnText"
    DANMAKU_ON_TEXT = "DanmakuOnText"
    GUARD_ON_TEXT = "GuardOnText"
    SUPER_CHAT_ON_TEXT = "SuperChatOnText"

    # TTS 服务通用
    ACTIVE_TTS = "ActiveTTS"

    # Minimax 服务
    MINIMAX_API_URL = "ApiUrl"
    MINIMAX_API_KEY = "ApiKey"
    MINIMAX_MODEL = "Model"
    MINIMAX_VOICE_ID = "VoiceId"
    MINIMAX_SPEED = "Speed"
    MINIMAX_VOL = "Vol"
    MINIMAX_PITCH = "Pitch"

    # Fish Speech 服务
    FISH_SPEECH_API_URL = "ApiUrl"

    # GPT-SoVITS 服务
    GPT_SOVITS_API_URL = "ApiUrl"
    GPT_SOVITS_SOVITS_MODEL = "SovitsModel"
    GPT_SOVITS_GPT_MODEL = "GptModel"
    GPT_SOVITS_TEXT_LANG = "TextLang"
    GPT_SOVITS_REF_AUDIO_PATH = "RefAudioPath"
    GPT_SOVITS_REF_TEXT = "RefText"
    GPT_SOVITS_REF_TEXT_LANG = "RefTextLang"
    GPT_SOVITS_TOP_K = "TopK"
    GPT_SOVITS_TOP_P = "TopP"
    GPT_SOVITS_TEMPERATURE = "Temperature"
    GPT_SOVITS_TEXT_SPLIT_METHOD = "TextSplitMethod"
    GPT_SOVITS_SPEED_FACTOR = "SpeedFactor"
    GPT_SOVITS_REF_TEXT_FREE = "RefTextFree"
    GPT_SOVITS_SAMPLE_STEPS = "SampleSteps"
    GPT_SOVITS_SUPER_SAMPLING = "SuperSampling"
    GPT_SOVITS_PAUSE_SECONDS = "PauseSeconds"

    # 播放器
    PLAYER_DEVICE = "PlayerDevice"

    # 别名字典
    ALIAS_DICT = "AliasDict"

    # 音色字典
    VOICE_DICT = "VoiceDict"


class DictValidator(ConfigValidator):
    """字典验证器

    验证配置值是否为字典类型。
    """

    def validate(self, value) -> bool:
        """验证值是否为字典"""
        return isinstance(value, dict)

    def correct(self, value):
        """将值修正为字典"""
        if isinstance(value, dict):
            return value
        return {}


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


class OutputDeviceValidator(OptionsValidator):
    """输出设备验证器

    动态获取输出设备列表，验证设备索引是否有效。
    """

    def __init__(self):
        self.options = [device.index for device in audio_player.get_output_devices()]

    @override
    def validate(self, value) -> bool:
        """验证值是否为有效的设备索引

        Args:
            value: 设备索引

        Returns:
            bool: 索引是否有效
        """

        self.options = [device.index for device in audio_player.get_output_devices()]
        return value in self.options

    @override
    def correct(self, value) -> int:
        """将值修正为有效的设备索引

        Args:
            value: 设备索引

        Returns:
            int: 有效的设备索引
        """
        return value if self.validate(value) else self.options[0]


def get_voices(api_key: str) -> list[str]:
    """获取Minimax支持的音色列表"""
    api_url = "https://api.minimax.io/v1/get_voice"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    params = {
        "voice_type": "all",
    }
    try:
        response = httpx.post(api_url, headers=headers, json=params, verify=False)
        response.raise_for_status()
        result = response.json()
    except httpx.HTTPStatusError:
        return [MINIMAX_ERROR_VOICE_ID]
    ret = []
    if not result or "voice_cloning" not in result:
        return [MINIMAX_ERROR_VOICE_ID]
    for voice in result["voice_cloning"]:
        ret.append(voice["voice_id"])
    if not ret:
        return [MINIMAX_ERROR_VOICE_ID]
    return ret


class Config(QConfig):
    """应用配置类

    使用 qfluentwidgets 的 QConfig 系统管理配置。
    """

    # B站直播服务配置
    roomId = ConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.ROOM_ID,
        default=213,
        validator=IntValidator(),
    )

    giftThreshold = ConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.GIFT_THRESHOLD,
        default=5,
        validator=IntValidator(),
    )

    normalDanmakuOn = ConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.NORMAL_DANMAKU_ON,
        default=False,
        validator=BoolValidator(),
    )

    guardOn = ConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.GUARD_ON,
        default=True,
        validator=BoolValidator(),
    )

    superChatOn = ConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.SUPER_CHAT_ON,
        default=True,
        validator=BoolValidator(),
    )

    debug = ConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.DEBUG,
        default=False,
        validator=BoolValidator(),
    )

    giftOnText = ConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.GIFT_ON_TEXT,
        default='"{user_name}" 赠送了{gift_num}个{gift_name}',
    )

    danmakuOnText = ConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.DANMAKU_ON_TEXT,
        default='"{user_name}"说:"{message}"',
    )

    guardOnText = ConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.GUARD_ON_TEXT,
        default='感谢 "{user_name}" 赠送的{guard_name},祝你熬夜不秃头,瞎吃不长胖!',
    )

    superChatOnText = ConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.SUPER_CHAT_ON_TEXT,
        default='"{user_name}" 发送了一条醒目留言,他说"{message}"',
    )

    aliasDict = ConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.ALIAS_DICT,
        default={"Merlin": "么林"},
        validator=DictValidator(),
    )

    voiceDict = ConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.VOICE_DICT,
        default=MINIMAX_VOICE_IDS,
        validator=DictValidator(),
    )

    # TTS 服务通用配置
    activeTTS = OptionsConfigItem(
        group=ConfigGroup.TTS_SERVICE,
        name=ConfigKey.ACTIVE_TTS,
        default=ServiceType.MINIMAX,
        validator=OptionsValidator(list(SUPPORTED_SERVICES.keys())),
    )

    # Minimax TTS 服务配置

    minimaxApiKey = ConfigItem(
        group=ConfigGroup.MINIMAX_SERVICE,
        name=ConfigKey.MINIMAX_API_KEY,
        default="",
    )

    minimaxModel = OptionsConfigItem(
        group=ConfigGroup.MINIMAX_SERVICE,
        name=ConfigKey.MINIMAX_MODEL,
        default=MINIMAX_MODELS[0],
        validator=OptionsValidator(MINIMAX_MODELS),
    )

    minimaxVoiceId = OptionsConfigItem(
        group=ConfigGroup.MINIMAX_SERVICE,
        name=ConfigKey.MINIMAX_VOICE_ID,
        default=list(MINIMAX_VOICE_IDS.keys())[0],
        validator=OptionsValidator(list(MINIMAX_VOICE_IDS.keys())),
    )

    minimaxSpeed = RangeConfigItem(
        group=ConfigGroup.MINIMAX_SERVICE,
        name=ConfigKey.MINIMAX_SPEED,
        default=1.2,
        validator=RangeValidator(0.1, 2.0),
    )

    minimaxVol = RangeConfigItem(
        group=ConfigGroup.MINIMAX_SERVICE,
        name=ConfigKey.MINIMAX_VOL,
        default=1.0,
        validator=RangeValidator(0.0, 2.0),
    )

    minimaxPitch = RangeConfigItem(
        group=ConfigGroup.MINIMAX_SERVICE,
        name=ConfigKey.MINIMAX_PITCH,
        default=0,
        validator=RangeValidator(-12, 12),
    )

    # Fish Speech TTS 服务配置
    fishSpeechApiUrl = ConfigItem(
        group=ConfigGroup.FISH_SPEECH_SERVICE,
        name=ConfigKey.FISH_SPEECH_API_URL,
        default="http://localhost:8080/v1/tts",
    )

    # GPT-SoVITS TTS 服务配置
    gptSovitsApiUrl = ConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_API_URL,
        default="http://localhost:19874",
    )

    gptSovitsSovitsModel = ConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_SOVITS_MODEL,
        default="",
    )

    gptSovitsGptModel = ConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_GPT_MODEL,
        default="",
    )

    gptSovitsTextLang = OptionsConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_TEXT_LANG,
        default="auto",
        validator=OptionsValidator(GPT_SOVITS_LANGUAGES),
    )

    gptSovitsRefAudioPath = ConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_REF_AUDIO_PATH,
        default="",
    )

    gptSovitsRefText = ConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_REF_TEXT,
        default="",
    )

    gptSovitsRefTextLang = OptionsConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_REF_TEXT_LANG,
        default="auto",
        validator=OptionsValidator(GPT_SOVITS_LANGUAGES),
    )

    gptSovitsTopK = ConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_TOP_K,
        default=5,
        validator=IntValidator(),
    )

    gptSovitsTopP = RangeConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_TOP_P,
        default=1.0,
        validator=RangeValidator(0.0, 1.0),
    )

    gptSovitsTemperature = RangeConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_TEMPERATURE,
        default=1.0,
        validator=RangeValidator(0.0, 2.0),
    )

    gptSovitsTextSplitMethod = OptionsConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_TEXT_SPLIT_METHOD,
        default="不切",
        validator=OptionsValidator(GPT_SOVITS_TEXT_SPLIT_METHODS),
    )

    gptSovitsSpeedFactor = RangeConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_SPEED_FACTOR,
        default=1.0,
        validator=RangeValidator(0.5, 2.0),
    )

    gptSovitsRefTextFree = ConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_REF_TEXT_FREE,
        default=False,
        validator=BoolValidator(),
    )

    gptSovitsSampleSteps = ConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_SAMPLE_STEPS,
        default=8,
        validator=IntValidator(),
    )

    gptSovitsSuperSampling = ConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_SUPER_SAMPLING,
        default=False,
        validator=BoolValidator(),
    )

    gptSovitsPauseSeconds = RangeConfigItem(
        group=ConfigGroup.GPT_SOVITS_SERVICE,
        name=ConfigKey.GPT_SOVITS_PAUSE_SECONDS,
        default=0.3,
        validator=RangeValidator(0.0, 5.0),
    )

    # 播放器配置
    playerDevice = OptionsConfigItem(
        group=ConfigGroup.PLAYER,
        name=ConfigKey.PLAYER_DEVICE,
        default=audio_player.default_output_index,  # 在实际使用时会通过 validator 修正为有效值
        validator=OutputDeviceValidator(),
    )


# 创建全局配置实例
cfg = Config()

# 加载配置文件
qconfig.load("data/config.json", cfg)
