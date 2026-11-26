"""数据模型：枚举和数据类"""

from enum import StrEnum

from pydantic import BaseModel, Field


class ServiceType(StrEnum):
    """TTS 服务类型枚举"""

    MINIMAX = 'minimax'
    OMNIVOICE = 'omnivoice'
    EDGE = 'edge'


class ServiceDetail(BaseModel):
    """TTS 服务详情"""

    name: ServiceType = Field(..., description='服务名称')
    description: str = Field(..., description='服务描述')
