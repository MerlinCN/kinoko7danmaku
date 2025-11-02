from pydantic import BaseModel, Field

class OutputDevice(BaseModel):
    index: int = Field(..., description="设备索引")
    name: str = Field(..., description="设备名称")