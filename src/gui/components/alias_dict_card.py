"""别名字典设置卡片"""

from PySide6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon as FIF

from core.qconfig import cfg

from .dict_edit_card import DictEditCard


class AliasDictCard(DictEditCard):
    """别名字典设置卡片

    继承自 DictEditCard，使用通用的字典编辑功能。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化别名字典卡片

        Args:
            parent: 父组件
        """
        super().__init__(
            config_item=cfg.aliasDict,
            icon=FIF.BOOK_SHELF,
            title="别名字典",
            content="设置弹幕中的别名替换规则",
            key_label="原词",
            value_label="替换为",
            key_placeholder="输入原词",
            value_placeholder="输入替换词",
            parent=parent,
        )
