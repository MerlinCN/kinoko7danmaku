"""自定义 Fluent 图标

通过继承 FluentIconBase 接入 qfluentwidgets 的主题反色机制：
每个图标需要在 resource/icons/ 下放置 `{value}_black.svg` 和 `{value}_white.svg` 两个文件。
"""

from enum import Enum

from qfluentwidgets import FluentIconBase, Theme, getIconColor

from core.const import RESOURCE_DIR


class CustomIcon(FluentIconBase, Enum):
    """项目自定义图标，跟随主题在黑/白两种 SVG 之间切换"""

    BILIBILI = "bilibili"
    MINIMAX = "minimax"
    YUAN = "yuan"
    MERGE = "merge"
    KEY = "key"
    FORMAT_QUOTE = "format_quote"
    THERMOSTAT = "thermostat"
    STAIRS = "stairs"

    def path(self, theme: Theme = Theme.AUTO) -> str:
        """根据主题返回对应颜色版本的 SVG 路径

        Args:
            theme: 主题，AUTO 时由 qfluentwidgets 根据当前主题自行决定

        Returns:
            str: SVG 文件的绝对路径
        """
        return str(RESOURCE_DIR / "icons" / f"{self.value}_{getIconColor(theme)}.svg")
