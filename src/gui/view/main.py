"""主窗口"""

import json
from pathlib import Path

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QStackedWidget
from qfluentwidgets import (
    FluentIcon as FIF,
    FluentWindow,
    NavigationItemPosition,
    isDarkTheme,
    qconfig,
)
from loguru import logger

from .settings import SettingsInterface
from .login_panel import LoginPanel
from .home_panel import HomePanel


class MainWindow(FluentWindow):
    """主窗口类

    使用 Fluent Design 风格的主窗口。
    未登录时显示登录界面，登录成功后显示主界面。
    """

    def __init__(self) -> None:
        super().__init__()
        self.init_ui()
        self._setup_panels()
        self._check_login_status()
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

    def _setup_panels(self) -> None:
        """设置两个主面板"""
        # 创建中央 widget 用来承载 stacked widget
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)

        # 创建 stacked widget 来切换登录/主界面
        self.stacked_widget = QStackedWidget()

        # 创建登录面板
        self.login_panel = LoginPanel()
        self.login_panel.login_success.connect(self._on_login_success)

        # 创建主页面板
        self.home_panel = HomePanel()
        self.home_panel.logout_btn.clicked.connect(self._on_logout)

        # 创建设置界面
        self.settings_interface = SettingsInterface(self)
        self.settings_interface.setObjectName("settingsInterface")

        # 将面板添加到 stacked widget
        self.stacked_widget.addWidget(self.login_panel)
        self.stacked_widget.addWidget(self.home_panel)

        central_layout.addWidget(self.stacked_widget)

        # 设置为中央 widget
        self.addCentralWidget(central_widget)

        # 添加设置界面到导航栏
        self.addSubInterface(
            self.settings_interface, FIF.SETTING, "设置", NavigationItemPosition.BOTTOM
        )

    def _check_login_status(self) -> None:
        """检查登录状态"""
        cookies_path = Path("cookies.json")
        if cookies_path.exists():
            try:
                with open(cookies_path, "r", encoding="utf-8") as f:
                    json.load(f)
                # 如果 cookies.json 存在，尝试进入已登录状态
                self.stacked_widget.setCurrentWidget(self.home_panel)
            except Exception as e:
                logger.error(f"检查登录状态失败: {e}")
                self.stacked_widget.setCurrentWidget(self.login_panel)
        else:
            self.stacked_widget.setCurrentWidget(self.login_panel)

    def _on_login_success(self) -> None:
        """登录成功的回调"""
        logger.info("登录成功，切换到主页面")
        self.stacked_widget.setCurrentWidget(self.home_panel)

    def _on_logout(self) -> None:
        """退出登录的回调"""
        cookies_path = Path("cookies.json")
        if cookies_path.exists():
            cookies_path.unlink()
            logger.info("已删除 cookies，返回登录界面")

        # 清空弹幕列表
        self.home_panel.danmaku_control_card.clear_danmaku()

        # 切换回登录界面
        self.login_panel._load_qr_code()
        self.stacked_widget.setCurrentWidget(self.login_panel)

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
