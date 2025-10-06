from typing import Dict, List

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from schema.const import ModelType


class BiliServiceConfig(BaseSettings):
    """Bilibili直播服务配置"""

    room_id: int = Field(default=213, title="房间号")
    gift_threshold: int = Field(default=5, title="礼物阈值（元）")
    normal_danmaku_on: bool = Field(default=False, title="普通弹幕是否触发")
    guard_on: bool = Field(default=True, title="舰长是否触发")
    super_chat_on: bool = Field(default=True, title="醒目留言是否触发")
    welcome_on: bool = Field(default=True, title="启动成功后语音播报")
    debug: bool = Field(default=False, title="调试模式")
    alias: Dict[str, str] = Field(
        default_factory=lambda: {"Merlin": "么林"}, title="别名"
    )
    gift_on_text: str = Field(
        default='"{user_name}" 赠送了{gift_num}个{gift_name}', title="礼物触发文本"
    )
    danmaku_on_text: str = Field(
        default='"{user_name}"说:"{message}"', title="弹幕触发文本"
    )
    guard_on_text: str = Field(
        default='感谢 "{user_name}" 赠送的{guard_name}，祝你熬夜不秃头，瞎吃不长胖！',
        title="舰长触发文本",
    )
    super_chat_on_text: str = Field(
        default='"{user_name}" 发送了一条醒目留言，他说"{message}"',
        title="醒目留言触发文本",
    )


class FishSpeechConfig(BaseSettings):
    """Fish Speech服务配置"""

    api_url: str = Field(
        default="http://localhost:8080/v1/tts", title="Fish Speech API 服务地址"
    )


class GPTSovitsConfig(BaseSettings):
    """GPTSovits服务配置"""

    api_url: str = Field(
        default="http://localhost:19874", title="GPTSovits API 服务地址"
    )
    sovits_model: str = Field("", description="SoVITS 模型权重")
    gpt_model: str = Field("", description="GPT 模型权重")
    text_lang: str = Field("auto", description="文本语言")
    ref_audio_path: str = Field("", description="参考音频路径")
    ref_text: str = Field("", description="参考文本")
    ref_text_lang: str = Field("auto", description="参考文本语言")
    top_k: int = Field(5, description="Top K")
    top_p: float = Field(1.0, description="Top P")
    temperature: float = Field(1.0, description="采样温度")
    text_split_method: str = Field("不切", description="文本切分方式")
    speed_factor: float = Field(1.0, description="语速调整")
    ref_text_free: bool = Field(False, description="无参考文本模式")
    sample_steps: int = Field(8, description="采样步数")
    super_sampling: bool = Field(False, description="超采样")
    pause_seconds: float = Field(0.3, description="句间停顿秒数")


class MinimaxConfig(BaseSettings):
    """MiniMax TTS服务配置"""

    api_url: str = Field(
        default="https://api.minimaxi.chat/v1/t2a_v2",
        description="MiniMax API 服务地址",
    )
    api_key: str = Field(default="", description="MiniMax API密钥")
    model: str = Field(default="speech-2.5-hd-preview", description="TTS模型")
    voice_id: str = Field(default="audiobook_male_1", description="音色ID")
    speed: float = Field(default=1.0, description="语速", ge=0.5, le=2.0)
    vol: float = Field(default=1.0, description="音量", ge=0.0, le=2.0)
    pitch: int = Field(default=0, description="音调", ge=-12, le=12)


class TTSServiceConfig(BaseSettings):
    """TTS服务配置"""

    active: List[ModelType] = Field(
        default=[ModelType.MINIMAX], title="激活的TTS服务类型"
    )

    fish_speech: FishSpeechConfig = Field(
        default_factory=FishSpeechConfig, title="Fish Speech服务配置"
    )
    gpt_sovits: GPTSovitsConfig = Field(
        default_factory=GPTSovitsConfig, title="GPTSovits服务配置"
    )
    minimax: MinimaxConfig = Field(
        default_factory=MinimaxConfig, title="MiniMax服务配置"
    )


class Setting(BaseSettings):
    """全局配置"""

    model_config = SettingsConfigDict(toml_file="config.toml")
    bili_service: BiliServiceConfig = Field(
        default_factory=BiliServiceConfig, title="Bilibili服务配置"
    )
    tts_service: TTSServiceConfig = Field(
        default_factory=TTSServiceConfig, title="TTS服务配置"
    )
    player_device: str = Field(default="", title="输出设备")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """自定义设置源，添加TOML配置源"""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


setting = Setting()
