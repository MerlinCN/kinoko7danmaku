from pydantic import BaseModel, Field


class OutputDevice(BaseModel):
    """音频输出设备"""

    index: int = Field(..., description='设备索引')
    name: str = Field(..., description='设备名称')
    sample_rate: int = Field(default=0, description='默认采样率（Hz）')
    channels: int = Field(default=0, description='最大输出声道数')
