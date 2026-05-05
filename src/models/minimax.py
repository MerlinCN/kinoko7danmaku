from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FilePurpose(str, Enum):
    """MiniMax 文件上传用途

    - VOICE_CLONE: 源音频，用于 voice_clone 接口的 file_id 字段
    - PROMPT_AUDIO: 示例音频，用于 voice_clone 接口 clone_prompt.prompt_audio 字段（需 <8 秒）
    - T2A_ASYNC_INPUT: 异步长文本 TTS 的输入文本
    """

    VOICE_CLONE = "voice_clone"
    PROMPT_AUDIO = "prompt_audio"
    T2A_ASYNC_INPUT = "t2a_async_input"


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


class VoiceItem(BaseModel):
    """MiniMax 音色项"""

    voice_id: str = Field(..., description="音色ID")
    voice_name: str = Field(default="", description="音色名称")
    description: List[str] = Field(default_factory=list, description="描述")
    created_time: str = Field(..., description="创建时间")


class BaseResp(BaseModel):
    """MiniMax API 基础响应"""

    status_code: int = Field(..., description="状态码")
    status_msg: str = Field(..., description="状态信息")


class VoiceListResponse(BaseModel):
    """MiniMax 获取音色列表响应"""

    voice_cloning: List[VoiceItem] = Field(..., description="音色克隆列表")
    base_resp: BaseResp = Field(..., description="基础响应")


class ClonePrompt(BaseModel):
    """克隆提示配置（样本音频 + 对应台词转录）"""

    prompt_audio: int = Field(..., description="样本音频文件ID（int64，需 <8 秒）")
    prompt_text: str = Field(..., description="样本音频对应的台词转录")


class VoiceCloneRequest(BaseModel):
    """音色克隆请求"""

    file_id: int = Field(..., description="源音频文件ID（int64）")
    voice_id: str = Field(..., description="自定义音色ID")
    clone_prompt: ClonePrompt = Field(..., description="样本音频与转录（必填）")
    text: Optional[str] = Field(default=None, description="预览文本")
    model: Optional[str] = Field(default=None, description="预览合成模型")
    need_noise_reduction: bool = Field(default=False, description="是否去除背景噪音")
    need_volume_normalization: bool = Field(
        default=False, description="是否启用音量归一化"
    )


class MinimaxFile(BaseModel):
    """MiniMax 上传文件元信息"""

    file_id: int = Field(..., description="文件ID（int64）")
    bytes: int = Field(..., description="文件大小（字节）")
    created_at: int = Field(..., description="创建时间（Unix 秒）")
    filename: str = Field(..., description="文件名")
    purpose: str = Field(..., description="文件用途")


class FileUploadResponse(BaseModel):
    """文件上传响应"""

    file: MinimaxFile = Field(..., description="文件元信息")
    base_resp: BaseResp = Field(..., description="基础响应")


class VoiceCloneResponse(BaseModel):
    """音色克隆响应"""

    input_sensitive: bool = Field(default=False, description="是否触发内容安全检查")
    input_sensitive_type: int = Field(
        default=0,
        description="内容类别（0=正常，1=严重违规，2=色情，3=广告，4=禁止内容，5=辱骂，6=暴力/恐怖，7=其他）",
    )
    demo_audio: Optional[str] = Field(default=None, description="预览音频URL")
    base_resp: BaseResp = Field(..., description="基础响应")
