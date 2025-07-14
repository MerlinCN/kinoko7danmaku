import json
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field


class TTSConfig(BaseModel):
    """TTS 配置模型"""

    # 直播间配置
    room_id: int = Field(default=213, description="房间号")
    gift_threshold: int = Field(
        default=5, description="≥这个值（单位：元）才会触发礼物"
    )

    # API 配置
    api_url: str = Field(
        default="http://localhost:8080/v1/tts", description="TTS API 服务地址"
    )
    api_mode: str = Field(
        default="bert-vits", description="API模式，可选：bert-vits, gpt-sovits"
    )

    # 触发开关
    normal_danmaku_on: bool = Field(default=True, description="普通弹幕是否触发")
    guard_on: bool = Field(default=True, description="舰长是否触发")
    super_chat_on: bool = Field(default=True, description="醒目留言是否触发")

    # 语音配置
    voice_name: str = Field(default="C酱", description="模型名")
    voice_channel: int = Field(
        default=-1, description="声道，默认-1为系统输出，如果有声卡，可以自行修改"
    )
    target_speed: float = Field(default=1.1, description="合成语速设置")

    # 别名配置
    alias: dict = Field(
        default_factory=dict,
        description="别名，用于替换一些词语，例如：{'Merlin':'么林'}",
    )

    # 调试配置
    debug: bool = Field(default=False, description="是否开启调试模式，不开启就行了")

    class Config:
        json_encoders = {
            # 如果以后需要处理特殊类型的序列化
        }


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self._config: TTSConfig = TTSConfig()  # 初始化为默认配置
        self.load_config()

    def load_config(self) -> TTSConfig:
        """加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                self._config = TTSConfig(**config_data)
                logger.info(f"配置已从 {self.config_file} 加载")
            else:
                self._config = TTSConfig()
                logger.info("使用默认配置")
                self.save_config()  # 保存默认配置
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self._config = TTSConfig()
            logger.info("使用默认配置")

        return self._config

    def save_config(self) -> bool:
        """保存配置"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._config.model_dump(), f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到 {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def update_config(self, **kwargs) -> bool:
        """更新配置"""
        try:
            # 创建新的配置对象以验证数据
            current_data = self._config.model_dump()
            current_data.update(kwargs)
            new_config = TTSConfig(**current_data)

            self._config = new_config
            return self.save_config()
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False

    @property
    def config(self) -> TTSConfig:
        """获取当前配置"""
        return self._config

    def get_api_url(self) -> str:
        """获取 API URL"""
        return self.config.api_url

    def set_api_url(self, url: str) -> bool:
        """设置 API URL"""
        return self.update_config(api_url=url)

    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        try:
            self._config = TTSConfig()
            return self.save_config()
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            return False


# 全局配置管理器实例
config_manager = ConfigManager()
