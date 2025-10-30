"""数据模型：枚举和数据类"""

from enum import Enum

from pydantic import BaseModel, Field


class ServiceType(str, Enum):
    """TTS 服务类型枚举"""

    FISH_SPEECH = "fish_speech"
    GPT_SOVITS = "gpt_sovits"
    MINIMAX = "minimax"


class ServiceDetail(BaseModel):
    """TTS 服务详情"""

    name: ServiceType = Field(..., description="服务名称")
    description: str = Field(..., description="服务描述")
