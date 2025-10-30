from enum import Enum

from pydantic import BaseModel, Field


class ServiceType(str, Enum):
    FISH_SPEECH = "fish_speech"
    GPT_SOVITS = "gpt_sovits"
    MINIMAX = "minimax"


class ServiceDetail(BaseModel):
    name: ServiceType = Field(..., description="服务名称")
    description: str = Field(..., description="服务描述")


SUPPORTED_SERVICES = {
    ServiceType.MINIMAX: ServiceDetail(
        name=ServiceType.MINIMAX, description="MiniMax（推荐）"
    ),
    ServiceType.GPT_SOVITS: ServiceDetail(
        name=ServiceType.GPT_SOVITS, description="GPT-SoVITS"
    ),
    ServiceType.FISH_SPEECH: ServiceDetail(
        name=ServiceType.FISH_SPEECH, description="Fish Speech"
    ),
}
