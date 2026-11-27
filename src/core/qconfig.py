"""基于 qfluentwidgets 的配置管理"""

import json

from enum import StrEnum
from pathlib import Path
from typing import Any, cast, override

import httpx

from loguru import logger
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
    DATA_DIR,
    EDGE_VOICES,
    MINIMAX_ERROR_VOICE_ID,
    MINIMAX_MODELS,
    SUPPORTED_SERVICES,
)
from .player import audio_player
from .secret import decrypt, encrypt, is_encrypted


class ConfigGroup(StrEnum):
    """配置分组名称"""

    BILI_SERVICE = 'BiliService'
    TTS_SERVICE = 'TTSService'
    MINIMAX_SERVICE = 'MinimaxService'
    OMNIVOICE_SERVICE = 'OmniVoiceService'
    EDGE_SERVICE = 'EdgeService'
    PLAYER = 'Player'
    DIAGNOSTICS = 'Diagnostics'


class ConfigKey(StrEnum):
    """配置项名称"""

    # B站直播服务
    ROOM_ID = 'RoomId'
    GIFT_THRESHOLD = 'GiftThreshold'
    FREE_GIFT_ON = 'FreeGiftOn'
    NORMAL_DANMAKU_ON = 'NormalDanmakuOn'
    GUARD_ON = 'GuardOn'
    SUPER_CHAT_ON = 'SuperChatOn'
    SUPER_CHAT_THRESHOLD = 'SuperChatThreshold'
    WELCOME_ON = 'WelcomeOn'
    DEBUG = 'Debug'
    GIFT_ON_TEXT = 'GiftOnText'
    DANMAKU_ON_TEXT = 'DanmakuOnText'
    GUARD_ON_TEXT = 'GuardOnText'
    SUPER_CHAT_ON_TEXT = 'SuperChatOnText'
    GIFT_MERGE_ON = 'GiftMergeOn'
    GIFT_MERGE_WINDOW = 'GiftMergeWindow'
    GIFT_MERGE_WINDOW_INITIAL = 'GiftMergeWindowInitial'
    GIFT_MERGE_WINDOW_INCREMENT = 'GiftMergeWindowIncrement'

    # TTS 服务通用
    ACTIVE_TTS = 'ActiveTTS'

    # Minimax 服务
    MINIMAX_API_URL = 'ApiUrl'
    MINIMAX_API_KEY = 'ApiKey'
    MINIMAX_MODEL = 'Model'
    MINIMAX_VOICE_ID = 'VoiceId'
    MINIMAX_SPEED = 'Speed'
    MINIMAX_VOL = 'Vol'
    MINIMAX_PITCH = 'Pitch'

    # OmniVoice 本地服务
    OMNIVOICE_PORT = 'Port'
    OMNIVOICE_HF_ENDPOINT = 'HfEndpoint'

    # Edge 服务
    EDGE_VOICE = 'Voice'
    EDGE_RATE = 'Rate'
    EDGE_VOLUME = 'Volume'
    EDGE_PITCH = 'Pitch'

    # 播放器
    PLAYER_DEVICE = 'PlayerDevice'

    # 别名字典
    ALIAS_DICT = 'AliasDict'

    # 音色字典
    VOICE_DICT = 'VoiceDict'

    # 诊断
    TELEMETRY_ENABLED = 'TelemetryEnabled'


class DictValidator(ConfigValidator):
    """字典验证器

    验证配置值是否为字典类型。
    """

    def validate(self, value: object) -> bool:
        """验证值是否为字典"""
        return isinstance(value, dict)

    def correct(self, value: object) -> dict[str, object]:
        """将值修正为字典"""
        if isinstance(value, dict):
            return value
        return {}


class IntValidator(ConfigValidator):
    """整数验证器

    验证配置值是否为整数类型，不限制范围。
    """

    def validate(self, value: object) -> bool:
        """验证值是否为整数"""
        return isinstance(value, int)

    def correct(self, value: object) -> int:
        """将值修正为整数"""
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0


class OutputDeviceValidator(OptionsValidator):
    """输出设备验证器

    动态获取输出设备列表，验证设备索引是否有效。
    系统没有输出设备时用 -1（跟随系统默认设备）占位，
    否则下拉框没有任何可选项，界面构造会直接失败。
    """

    def __init__(self) -> None:
        self._refresh()

    def _refresh(self) -> list[int]:
        """刷新可选项

        Returns:
            有效的设备索引；没有输出设备时为 [-1]
        """
        indexes = [device.index for device in audio_player.get_output_devices()]
        self.options = indexes or [-1]
        return self.options

    @override
    def validate(self, value: object) -> bool:
        """验证值是否为有效的设备索引

        Args:
            value: 设备索引

        Returns:
            bool: 索引是否有效
        """
        return value in self._refresh()

    @override
    def correct(self, value: object) -> int:
        """将值修正为有效的设备索引

        Args:
            value: 设备索引

        Returns:
            int: 有效的设备索引；没有输出设备时为 -1
        """
        if self.validate(value):
            return cast('int', value)
        return self.options[0]


class VoiceIdValidator(ConfigValidator):
    """音色 ID 验证器

    options/validate/correct 都从 voiceDict 实时读取，无任何缓存，
    避免初始化时 voiceDict 还是 default 导致缓存的列表过时。
    OptionsConfigItem.options 直接读 validator.options，因此 ComboBoxSettingCard
    构造时也能拿到最新的音色列表。
    """

    def __init__(self, voice_dict_config_item: Any) -> None:
        """初始化验证器

        Args:
            voice_dict_config_item: voiceDict 的 ConfigItem 实例
        """
        self.voice_dict_config_item = voice_dict_config_item

    @property
    def options(self) -> list[str]:
        """实时返回 voiceDict 当前的音色 ID 列表"""
        return list(self.voice_dict_config_item.value.keys())

    @override
    def validate(self, value: object) -> bool:
        """验证音色 ID 是否在 voiceDict 中"""
        return value in self.voice_dict_config_item.value

    @override
    def correct(self, value: object) -> str:
        """修正音色 ID；voiceDict 为空时返回 ""，否则返回第一个 key"""
        if self.validate(value):
            return value
        keys = list(self.voice_dict_config_item.value.keys())
        return keys[0] if keys else ''


def get_voices(api_key: str) -> list[str]:
    """获取Minimax支持的音色列表"""
    api_url = 'https://api.minimax.io/v1/get_voice'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    params = {
        'voice_type': 'all',
    }
    try:
        response = httpx.post(api_url, headers=headers, json=params, verify=False)
        response.raise_for_status()
        result = response.json()
    except httpx.HTTPStatusError:
        return [MINIMAX_ERROR_VOICE_ID]
    if not result or 'voice_cloning' not in result:
        return [MINIMAX_ERROR_VOICE_ID]
    ret = [voice['voice_id'] for voice in result['voice_cloning']]
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

    freeGiftOn = OptionsConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.FREE_GIFT_ON,
        default=False,
        validator=BoolValidator(),
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

    superChatThreshold = ConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.SUPER_CHAT_THRESHOLD,
        default=30,
        validator=IntValidator(),
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
        default={'Merlin': '么林'},
        validator=DictValidator(),
    )

    giftMergeOn = ConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.GIFT_MERGE_ON,
        default=False,
        validator=BoolValidator(),
    )

    giftMergeWindowInitial = RangeConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.GIFT_MERGE_WINDOW_INITIAL,
        default=1.5,
        validator=RangeValidator(0.5, 5.0),
    )

    giftMergeWindowIncrement = RangeConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.GIFT_MERGE_WINDOW_INCREMENT,
        default=0.5,
        validator=RangeValidator(0.1, 2.0),
    )

    giftMergeWindow = RangeConfigItem(
        group=ConfigGroup.BILI_SERVICE,
        name=ConfigKey.GIFT_MERGE_WINDOW,
        default=5.0,
        validator=RangeValidator(1.0, 30.0),
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
        default='',
    )

    voiceDict = ConfigItem(
        group=ConfigGroup.MINIMAX_SERVICE,
        name=ConfigKey.VOICE_DICT,
        default={'kinoko7_v1': 'kinoko7_v1'},
        validator=DictValidator(),
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
        default=next(iter(voiceDict.value.keys())),
        validator=VoiceIdValidator(voiceDict),
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

    # OmniVoice 本地服务配置
    omnivoicePort = ConfigItem(
        group=ConfigGroup.OMNIVOICE_SERVICE,
        name=ConfigKey.OMNIVOICE_PORT,
        default=8017,
        validator=IntValidator(),
    )

    omnivoiceHfEndpoint = OptionsConfigItem(
        group=ConfigGroup.OMNIVOICE_SERVICE,
        name=ConfigKey.OMNIVOICE_HF_ENDPOINT,
        default='https://hf-mirror.com',
        validator=OptionsValidator(['https://hf-mirror.com', 'https://huggingface.co']),
    )

    # Edge TTS 服务配置
    edgeVoice = OptionsConfigItem(
        group=ConfigGroup.EDGE_SERVICE,
        name=ConfigKey.EDGE_VOICE,
        default='zh-CN-XiaoxiaoNeural',
        validator=OptionsValidator(EDGE_VOICES),
    )

    edgeRate = RangeConfigItem(
        group=ConfigGroup.EDGE_SERVICE,
        name=ConfigKey.EDGE_RATE,
        default=1.0,
        validator=RangeValidator(0.0, 3.0),
    )

    edgeVolume = RangeConfigItem(
        group=ConfigGroup.EDGE_SERVICE,
        name=ConfigKey.EDGE_VOLUME,
        default=1.0,
        validator=RangeValidator(0.0, 3.0),
    )

    edgePitch = RangeConfigItem(
        group=ConfigGroup.EDGE_SERVICE,
        name=ConfigKey.EDGE_PITCH,
        default=0,
        validator=RangeValidator(-300, 300),
    )

    # 播放器配置
    playerDevice = OptionsConfigItem(
        group=ConfigGroup.PLAYER,
        name=ConfigKey.PLAYER_DEVICE,
        default=audio_player.default_output_index,  # 在实际使用时会通过 validator 修正为有效值
        validator=OutputDeviceValidator(),
    )

    # 诊断
    telemetryEnabled = ConfigItem(
        group=ConfigGroup.DIAGNOSTICS,
        name=ConfigKey.TELEMETRY_ENABLED,
        default=True,
        validator=BoolValidator(),
    )

    @override
    def toDict(self, serialize: bool = True) -> dict[str, Any]:
        """导出配置，写入文件前加密敏感字段

        Args:
            serialize: 是否使用 ConfigItem 的序列化结果

        Returns:
            配置字典，敏感字段为密文
        """
        data = super().toDict(serialize)
        for item in SECRET_ITEMS:
            group = cast('dict[str, str]', data[item.group])
            value = group[item.name]
            if not value or is_encrypted(value):
                continue
            try:
                group[item.name] = encrypt(value)
            except Exception as e:
                # 加密失败不能丢配置，宁可这次写明文并留下告警
                logger.warning(f'敏感配置加密失败: {e!r}')
        return data


def _migrate_voice_dict_to_minimax(config_path: Path) -> None:
    """把旧 BiliService.VoiceDict 物理迁到 MinimaxService.VoiceDict

    幂等：迁移后从 BiliService 删除 VoiceDict 字段并写回；若 MinimaxService 已有
    VoiceDict，保留新值仅清理旧字段。
    """
    if not config_path.exists():
        return
    try:
        raw = json.loads(config_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return
    bili = raw.get('BiliService', {})
    if 'VoiceDict' not in bili:
        return
    minimax = raw.setdefault('MinimaxService', {})
    minimax.setdefault('VoiceDict', bili.pop('VoiceDict'))
    config_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=4),
        encoding='utf-8',
    )


_migrate_voice_dict_to_minimax(DATA_DIR / 'config.json')

# 创建全局配置实例
cfg = Config()


def _preload_voice_dict(config_path: Path) -> None:
    """qconfig.load 按 json 字段顺序反序列化，若 VoiceId 出现在 VoiceDict 之前，
    VoiceId 会被 VoiceIdValidator.correct 拿过期的（default）voiceDict 覆写成
    kinoko7_v1。这里在 load 之前先把 VoiceDict 拉到 cfg，保证后续 VoiceId 校验
    拿到完整的音色列表。
    """
    if not config_path.exists():
        return
    try:
        raw = json.loads(config_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return
    saved = raw.get('MinimaxService', {}).get('VoiceDict')
    if isinstance(saved, dict):
        cfg.voiceDict.value = saved


_preload_voice_dict(DATA_DIR / 'config.json')

# 加载配置文件
qconfig.load(str(DATA_DIR / 'config.json'), cfg)

SECRET_ITEMS = (Config.minimaxApiKey,)


def _decrypt_secrets() -> None:
    """把配置里的敏感字段解密回内存，并把遗留的明文重新加密保存"""
    plaintext = False
    for item in SECRET_ITEMS:
        value = cast('str', item.value)
        if not value:
            continue
        if is_encrypted(value):
            item.value = decrypt(value)
        else:
            plaintext = True
    if plaintext:
        qconfig.save()


_decrypt_secrets()
