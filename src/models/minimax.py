from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VoiceSetting(BaseModel):
    """MiniMax 音色设置"""

    voice_id: str = Field(..., description="音色ID")
    speed: float = Field(default=1.0, description="语速", ge=0.5, le=2.0)
    vol: float = Field(default=1.0, description="音量", ge=0.0, le=2.0)
    pitch: int = Field(default=0, description="音调", ge=-12, le=12)


class PronunciationDict(BaseModel):
    """MiniMax 发音字典"""

    tone: List[str] = Field(
        default_factory=list, description="音调列表，格式: '文字/(拼音)'"
    )


class AudioSetting(BaseModel):
    """MiniMax 音频设置"""

    sample_rate: int = Field(default=32000, description="采样率")
    bitrate: int = Field(default=128000, description="比特率")
    format: str = Field(default="mp3", description="音频格式 (mp3/wav/pcm)")
    channel: int = Field(default=1, description="声道数")


class MinimaxTTSRequest(BaseModel):
    """MiniMax TTS 请求体"""

    model: str = Field(..., description="TTS模型")
    text: str = Field(..., description="要转换的文本")
    stream: bool = Field(default=False, description="是否流式输出")
    language_boost: str = Field(default="auto", description="语言增强模式")
    output_format: str = Field(default="hex", description="输出格式")
    voice_setting: VoiceSetting = Field(..., description="音色设置")
    pronunciation_dict: Optional[PronunciationDict] = Field(
        default=None, description="发音字典"
    )
    audio_setting: Optional[AudioSetting] = Field(default=None, description="音频设置")


class ExtraInfo(BaseModel):
    """MiniMax 响应额外信息"""

    audio_length: Optional[float] = Field(default=None, description="音频长度(秒)")
    audio_size: Optional[int] = Field(default=None, description="音频大小(字节)")
    audio_sample_rate: Optional[int] = Field(default=None, description="音频采样率")
    audio_channels: Optional[int] = Field(default=None, description="音频声道数")
    bitrate: Optional[int] = Field(default=None, description="比特率")


class AudioData(BaseModel):
    """MiniMax 音频数据"""

    audio: str = Field(..., description="音频数据")
    status: int = Field(..., description="状态码")
    ced: Optional[str] = Field(default=None, description="错误信息")


class MinimaxTTSResponse(BaseModel):
    """MiniMax TTS 响应体"""

    trace_id: Optional[str] = Field(default=None, description="追踪ID")
    audio_file: Optional[str] = Field(default=None, description="音频文件URL或hex编码")
    data: Optional[AudioData] = Field(default=None, description="音频数据")
    subtitle_file: Optional[str] = Field(default=None, description="字幕文件")
    extra_info: Optional[ExtraInfo] = Field(default=None, description="额外信息")
    base_resp: Optional[Dict[str, Any]] = Field(
        default=None, description="基础响应信息"
    )
