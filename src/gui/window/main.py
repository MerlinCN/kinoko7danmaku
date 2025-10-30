"""主窗口"""

from pathlib import Path

from PySide6.QtWidgets import QApplication
from qfluentwidgets import (
    FluentIcon as FIF,
    FluentWindow,
    NavigationItemPosition,
    isDarkTheme,
    qconfig,
)

from .settings import SettingsInterface


class MainWindow(FluentWindow):
    """主窗口类

    使用 Fluent Design 风格的主窗口，包含侧边导航栏。
    """

    def __init__(self) -> None:
        super().__init__()
        self.init_ui()
        self.init_navigation()
        self._set_qss()
        self._connect_signals()

    def init_ui(self) -> None:
        """初始化 UI"""
        self.setWindowTitle("Kinoko7 弹幕姬")
        self.resize(1200, 800)

        # 设置窗口居中
        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

    def init_navigation(self) -> None:
        """初始化导航栏"""
        # 创建子界面
        self.settingsInterface = SettingsInterface(self)

        self.settingsInterface.setObjectName("settingsInterface")

        # 添加设置页面到底部
        self.addSubInterface(
            self.settingsInterface, FIF.SETTING, "设置", NavigationItemPosition.BOTTOM
        )

    def _set_qss(self) -> None:
        """设置样式表

        根据当前主题加载对应的 QSS 文件，应用到整个应用。
        """
        # 根据当前主题加载对应的 qss 文件
        theme = "dark" if isDarkTheme() else "light"
        qss_path = Path.cwd() / "resource" / "qss" / theme / "main_window.qss"

        if qss_path.exists():
            with open(qss_path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _on_theme_changed(self) -> None:
        """主题改变时的回调"""
        self._set_qss()

    def _connect_signals(self) -> None:
        """连接信号"""
        # 连接主题切换信号
        qconfig.themeChanged.connect(self._on_theme_changed)
