"""别名字典设置卡片"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QWidget
from qfluentwidgets import BodyLabel, ExpandGroupSettingCard, LineEdit, ToolButton
from qfluentwidgets import FluentIcon as FIF

from core.qconfig import cfg


class AliasItemWidget(QWidget):
    """别名项组件

    包含原词和替换词的输入框，以及添加/删除按钮。
    """

    # 信号
    deleteRequested = Signal(QWidget)  # 删除请求信号
    addRequested = Signal()  # 添加请求信号
    valueChanged = Signal()  # 值改变信号

    def __init__(
        self, key: str = "", value: str = "", parent: QWidget | None = None
    ) -> None:
        """初始化别名项组件

        Args:
            key: 别名键（原词）
            value: 别名值（替换为）
            parent: 父组件
        """
        super().__init__(parent=parent)
        self._init_ui(key, value)

    def _init_ui(self, key: str, value: str) -> None:
        """初始化 UI

        Args:
            key: 别名键
            value: 别名值
        """
        # 主布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(48, 12, 48, 12)
        layout.setSpacing(12)

        # 原词标签
        self.key_label = BodyLabel("原词：", self)
        layout.addWidget(self.key_label)

        # 原词输入框
        self.key_edit = LineEdit(self)
        self.key_edit.setText(key)
        self.key_edit.setPlaceholderText("输入原词")
        self.key_edit.setFixedWidth(150)
        self.key_edit.textChanged.connect(self._on_value_changed)
        layout.addWidget(self.key_edit)

        layout.addSpacing(16)

        # 替换为标签
        self.value_label = BodyLabel("替换为：", self)
        layout.addWidget(self.value_label)

        # 替换为输入框
        self.value_edit = LineEdit(self)
        self.value_edit.setText(value)
        self.value_edit.setPlaceholderText("输入替换词")
        self.value_edit.setFixedWidth(150)
        self.value_edit.textChanged.connect(self._on_value_changed)
        layout.addWidget(self.value_edit)

        layout.addStretch()

        # 删除/添加按钮（初始隐藏，由父组件控制）
        self.delete_btn = ToolButton(FIF.REMOVE, self)
        self.delete_btn.clicked.connect(lambda: self.deleteRequested.emit(self))
        layout.addWidget(self.delete_btn)

        self.add_btn = ToolButton(FIF.ADD, self)
        self.add_btn.clicked.connect(self.addRequested.emit)
        layout.addWidget(self.add_btn)
        self.add_btn.hide()  # 默认隐藏

        self.setFixedHeight(60)

    def _on_value_changed(self) -> None:
        """值改变时发射信号"""
        self.valueChanged.emit()

    def get_key(self) -> str:
        """获取别名键"""
        return self.key_edit.text().strip()

    def get_value(self) -> str:
        """获取别名值"""
        return self.value_edit.text().strip()

    def set_button_mode(self, show_add: bool, show_delete: bool) -> None:
        """设置按钮显示模式

        Args:
            show_add: 是否显示添加按钮
            show_delete: 是否显示删除按钮
        """
        self.add_btn.setVisible(show_add)
        self.delete_btn.setVisible(show_delete)


class AliasDictCard(ExpandGroupSettingCard):
    """别名字典设置卡片

    使用可展开的组设置卡片显示和管理别名字典。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化别名字典卡片

        Args:
            parent: 父组件
        """
        super().__init__(
            icon=FIF.BOOK_SHELF,
            title="别名字典",
            content="设置弹幕中的别名替换规则",
            parent=parent,
        )
        self.alias_items = []  # 存储别名项组件
        self._load_aliases()

    def _load_aliases(self) -> None:
        """从配置加载别名并创建组件"""
        # 获取别名字典
        alias_dict = cfg.aliasDict.value

        # 清空现有组件
        self._clear_items()

        # 为每个别名创建组件
        if alias_dict:
            for key, value in alias_dict.items():
                self._add_alias_item(key, value)
        else:
            # 如果没有别名，添加一个空项
            self._add_alias_item("", "")

        # 更新按钮状态
        self._update_button_states()

    def _add_alias_item(self, key: str, value: str) -> None:
        """添加一个别名项

        Args:
            key: 别名键
            value: 别名值
        """
        item = AliasItemWidget(key, value, self)
        # 连接信号
        item.deleteRequested.connect(self._on_delete_item)
        item.addRequested.connect(self._on_add_item)
        item.valueChanged.connect(self._on_value_changed)

        self.alias_items.append(item)
        self.addGroupWidget(item)

    def _on_add_item(self) -> None:
        """添加按钮点击事件"""
        # 添加一个新的空项
        self._add_alias_item("", "")
        # 更新按钮状态
        self._update_button_states()
        # 保存到配置
        self._save_to_config()

    def _on_delete_item(self, item: QWidget) -> None:
        """删除按钮点击事件

        Args:
            item: 要删除的别名项
        """
        if item in self.alias_items:
            self.alias_items.remove(item)
            self.removeGroupWidget(item)
            item.deleteLater()

            # 如果删除后没有项了，添加一个空项
            if not self.alias_items:
                self._add_alias_item("", "")

            # 更新按钮状态
            self._update_button_states()
            # 保存到配置
            self._save_to_config()

    def _on_value_changed(self) -> None:
        """值改变时保存到配置"""
        self._save_to_config()

    def _update_button_states(self) -> None:
        """更新所有别名项的按钮状态"""
        count = len(self.alias_items)

        for i, item in enumerate(self.alias_items):
            is_last = i == count - 1
            show_delete = count > 1  # 只有一条时不显示删除按钮
            show_add = is_last  # 只有最后一条显示添加按钮

            item.set_button_mode(show_add, show_delete)

    def _save_to_config(self) -> None:
        """保存别名字典到配置

        只保存原词和替换词都不为空的项。
        """
        # 收集所有有效的别名（原词和替换词都不为空）
        alias_dict = {}
        for item in self.alias_items:
            key = item.get_key()
            value = item.get_value()
            if key and value:  # 两者都不为空才保存
                alias_dict[key] = value

        # 保存到配置
        cfg.set(cfg.aliasDict, alias_dict)

    def _clear_items(self) -> None:
        """清空所有别名项"""
        for item in self.alias_items:
            self.removeGroupWidget(item)
            item.deleteLater()
        self.alias_items.clear()

    def reload(self) -> None:
        """重新加载别名字典"""
        self._load_aliases()
