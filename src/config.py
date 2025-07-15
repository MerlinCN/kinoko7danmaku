import json
from pathlib import Path
from typing import Dict

from loguru import logger
from pydantic import BaseModel, Field


class TTSConfig(BaseModel):
    """TTS 配置模型"""

    # 直播间配置
    room_id: int = Field(
        default=213,
        title="房间号",
        description="短号长号都可以",
    )
    gift_threshold: int = Field(
        default=5,
        title="礼物阈值（元）",
        description="≥这个值（单位：元）才会触发礼物",
    )

    # API 配置
    api_url: str = Field(
        default="http://localhost:8080/v1/tts",
        title="TTS API 服务地址",
        description="TTS API 服务地址",
    )

    # 触发开关
    normal_danmaku_on: bool = Field(default=False, title="普通弹幕是否触发")
    guard_on: bool = Field(default=True, title="舰长是否触发")
    super_chat_on: bool = Field(default=True, title="醒目留言是否触发")

    # 调试配置
    debug: bool = Field(
        default=False,
        title="调试模式",
        description="是否开启调试模式，不开启就行了",
    )

    alias: Dict[str, str] = Field(
        default={"Merlin": "么林"},
        title="别名",
    )

    class Config:
        json_encoders = {
            # 如果以后需要处理特殊类型的序列化
        }


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: Path = Path("config.json")):
        self.config_file = config_file
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
                json.dump(self._config.model_dump(), f, indent=4, ensure_ascii=False)
            logger.info(f"配置已保存到 {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def update_config(self, config: TTSConfig) -> bool:
        """更新配置"""
        self._config = config
        return self.save_config()

    @property
    def config(self) -> TTSConfig:
        """获取当前配置"""
        return self._config

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
