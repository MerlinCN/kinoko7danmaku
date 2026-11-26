"""OmniVoice 本地服务数据模型"""

from pydantic import BaseModel, Field


class OmniVoiceSettings(BaseModel):
    """OmniVoice 合成参数

    独立保存在 `~/.kinoko7danmaku/omnivoice.json`，与运行时配置分开。
    """

    ref_audio: str = Field(default='', description='参考音频文件路径')
    ref_text: str = Field(default='', description='参考音频对应的文本')
    speed: float = Field(default=1.0, description='语速倍率')
