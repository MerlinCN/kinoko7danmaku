"""OmniVoice 合成参数持久化"""

from loguru import logger

from core.const import DATA_DIR
from models.omnivoice import OmniVoiceSettings

SETTINGS_PATH = DATA_DIR / 'omnivoice.json'


def load_settings() -> OmniVoiceSettings:
    """读取合成参数

    Returns:
        合成参数，文件缺失或损坏时返回默认值
    """
    if not SETTINGS_PATH.exists():
        return OmniVoiceSettings()
    try:
        return OmniVoiceSettings.model_validate_json(SETTINGS_PATH.read_text(encoding='utf-8'))
    except ValueError as e:
        logger.warning(f'读取 OmniVoice 参数失败: {e!r}')
        return OmniVoiceSettings()


def save_settings(settings: OmniVoiceSettings) -> None:
    """保存合成参数

    Args:
        settings: 合成参数
    """
    SETTINGS_PATH.write_text(settings.model_dump_json(indent=2), encoding='utf-8')
