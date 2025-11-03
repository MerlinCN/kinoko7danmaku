"""通用字典编辑设置卡片"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    ConfigItem,
    ExpandGroupSettingCard,
    LineEdit,
    ToolButton,
)
from qfluentwidgets import FluentIcon as FIF

from core.qconfig import cfg


class DictItemWidget(QWidget):
    """字典项组件

    包含键和值的输入框，以及添加/删除按钮。
    """

    # 信号
    deleteRequested = Signal(QWidget)  # 删除请求信号
    addRequested = Signal()  # 添加请求信号
    valueChanged = Signal()  # 值改变信号

    def __init__(
        self,
        key: str = "",
        value: str = "",
        key_label: str = "键",
        value_label: str = "值",
        key_placeholder: str = "输入键",
        value_placeholder: str = "输入值",
        parent: QWidget | None = None,
    ) -> None:
        """初始化字典项组件

        Args:
            key: 字典键
            value: 字典值
            key_label: 键标签文本
            value_label: 值标签文本
            key_placeholder: 键输入框占位符
            value_placeholder: 值输入框占位符
            parent: 父组件
        """
        super().__init__(parent=parent)
        self._init_ui(
            key, value, key_label, value_label, key_placeholder, value_placeholder
        )

    def _init_ui(
        self,
        key: str,
        value: str,
        key_label: str,
        value_label: str,
        key_placeholder: str,
        value_placeholder: str,
    ) -> None:
        """初始化 UI

        Args:
            key: 字典键
            value: 字典值
            key_label: 键标签文本
            value_label: 值标签文本
            key_placeholder: 键输入框占位符
            value_placeholder: 值输入框占位符
        """
        # 主布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(48, 12, 48, 12)
        layout.setSpacing(12)

        # 键标签
        self.key_label = BodyLabel(f"{key_label}：", self)
        layout.addWidget(self.key_label)

        # 键输入框
        self.key_edit = LineEdit(self)
        self.key_edit.setText(key)
        self.key_edit.setPlaceholderText(key_placeholder)
        self.key_edit.setFixedWidth(150)
        self.key_edit.textChanged.connect(self._on_value_changed)
        layout.addWidget(self.key_edit)

        layout.addSpacing(16)

        # 值标签
        self.value_label = BodyLabel(f"{value_label}：", self)
        layout.addWidget(self.value_label)

        # 值输入框
        self.value_edit = LineEdit(self)
        self.value_edit.setText(value)
        self.value_edit.setPlaceholderText(value_placeholder)
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
        """获取字典键"""
        return self.key_edit.text().strip()

    def get_value(self) -> str:
        """获取字典值"""
        return self.value_edit.text().strip()

    def set_button_mode(self, show_add: bool, show_delete: bool) -> None:
        """设置按钮显示模式

        Args:
            show_add: 是否显示添加按钮
            show_delete: 是否显示删除按钮
        """
        self.add_btn.setVisible(show_add)
        self.delete_btn.setVisible(show_delete)


class DictEditCard(ExpandGroupSettingCard):
    """通用字典编辑设置卡片

    使用可展开的组设置卡片显示和管理字典。
    """

    def __init__(
        self,
        config_item: ConfigItem,
        icon,
        title: str,
        content: str,
        key_label: str = "键",
        value_label: str = "值",
        key_placeholder: str = "输入键",
        value_placeholder: str = "输入值",
        parent: QWidget | None = None,
    ) -> None:
        """初始化字典编辑卡片

        Args:
            config_item: 配置项（必须是字典类型）
            icon: 图标
            title: 标题
            content: 描述
            key_label: 键标签文本
            value_label: 值标签文本
            key_placeholder: 键输入框占位符
            value_placeholder: 值输入框占位符
            parent: 父组件
        """
        super().__init__(
            icon=icon,
            title=title,
            content=content,
            parent=parent,
        )
        self.config_item = config_item
        self.key_label = key_label
        self.value_label = value_label
        self.key_placeholder = key_placeholder
        self.value_placeholder = value_placeholder
        self.dict_items = []  # 存储字典项组件
        self._load_dict()

    def _load_dict(self) -> None:
        """从配置加载字典并创建组件"""
        # 获取字典
        dict_value = self.config_item.value

        # 清空现有组件
        self._clear_items()

        # 为每个键值对创建组件
        if dict_value:
            for key, value in dict_value.items():
                self._add_dict_item(key, value)
        else:
            # 如果字典为空，添加一个空项
            self._add_dict_item("", "")

        # 更新按钮状态
        self._update_button_states()

    def _add_dict_item(self, key: str, value: str) -> None:
        """添加一个字典项

        Args:
            key: 字典键
            value: 字典值
        """
        item = DictItemWidget(
            key,
            value,
            self.key_label,
            self.value_label,
            self.key_placeholder,
            self.value_placeholder,
            self,
        )
        # 连接信号
        item.deleteRequested.connect(self._on_delete_item)
        item.addRequested.connect(self._on_add_item)
        item.valueChanged.connect(self._on_value_changed)

        self.dict_items.append(item)
        self.addGroupWidget(item)

    def _on_add_item(self) -> None:
        """添加按钮点击事件"""
        # 添加一个新的空项
        self._add_dict_item("", "")
        # 更新按钮状态
        self._update_button_states()
        # 保存到配置
        self._save_to_config()

    def _on_delete_item(self, item: QWidget) -> None:
        """删除按钮点击事件

        Args:
            item: 要删除的字典项
        """
        if item in self.dict_items:
            self.dict_items.remove(item)
            self.removeGroupWidget(item)
            item.deleteLater()

            # 如果删除后没有项了，添加一个空项
            if not self.dict_items:
                self._add_dict_item("", "")

            # 更新按钮状态
            self._update_button_states()
            # 保存到配置
            self._save_to_config()

    def _on_value_changed(self) -> None:
        """值改变时保存到配置"""
        self._save_to_config()

    def _update_button_states(self) -> None:
        """更新所有字典项的按钮状态"""
        count = len(self.dict_items)

        for i, item in enumerate(self.dict_items):
            is_last = i == count - 1
            show_delete = count > 1  # 只有一条时不显示删除按钮
            show_add = is_last  # 只有最后一条显示添加按钮

            item.set_button_mode(show_add, show_delete)

    def _save_to_config(self) -> None:
        """保存字典到配置

        只保存键和值都不为空的项。
        """
        # 收集所有有效的键值对（键和值都不为空）
        dict_value = {}
        for item in self.dict_items:
            key = item.get_key()
            value = item.get_value()
            if key and value:  # 两者都不为空才保存
                dict_value[key] = value

        # 保存到配置
        cfg.set(self.config_item, dict_value)

    def _clear_items(self) -> None:
        """清空所有字典项"""
        for item in self.dict_items:
            self.removeGroupWidget(item)
            item.deleteLater()
        self.dict_items.clear()

    def reload(self) -> None:
        """重新加载字典"""
        self._load_dict()
