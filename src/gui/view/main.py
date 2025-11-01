"""主窗口"""

from pathlib import Path

from loguru import logger
from PySide6.QtWidgets import QApplication, QStackedWidget, QVBoxLayout, QWidget
from qasync import asyncSlot
from qfluentwidgets import (
    FluentIcon as FIF,
)
from qfluentwidgets import (
    FluentWindow,
    NavigationItemPosition,
    TitleLabel,
    isDarkTheme,
    qconfig,
)

from bilibili import bili_service

from ..components import HomePanel, LoginPanel
from .settings import SettingsInterface


class MainInterface(QWidget):
    """主界面

    包含登录面板和主页面板的切换。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._setup_ui()
        self._check_login_status()

    def _setup_ui(self) -> None:
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 10, 36, 0)
        self.title_label = TitleLabel("登录", self)
        self.title_label.move(36, 30)
        layout.addWidget(self.title_label)
        # 创建 stacked widget 来切换登录/主界面
        self.stacked_widget = QStackedWidget()

        # 创建登录面板
        self.login_panel = LoginPanel()
        self.login_panel.login_success.connect(self._on_login_success)

        # 创建主页面板
        self.home_panel = HomePanel()
        self.home_panel.user_info_card.logout_btn.clicked.connect(self._on_logout)

        # 将面板添加到 stacked widget
        self.stacked_widget.addWidget(self.login_panel)
        self.stacked_widget.addWidget(self.home_panel)

        layout.addWidget(self.stacked_widget)

    def _check_login_status(self) -> None:
        """检查登录状态"""
        if bili_service.is_logged_in():
            self.stacked_widget.setCurrentWidget(self.home_panel)
            self.title_label.setText("主页")
        else:
            self.stacked_widget.setCurrentWidget(self.login_panel)
            self.title_label.setText("登录")

    def _on_login_success(self) -> None:
        """登录成功的回调"""
        logger.info("登录成功，切换到主页面")
        self._check_login_status()
        # 刷新用户信息
        self.home_panel.user_info_card._load_user_info()

    @asyncSlot()
    async def _on_logout(self) -> None:
        """退出登录的回调"""
        await bili_service.logout()

        # 切换回登录界面
        self.login_panel._load_qr_code()
        self.stacked_widget.setCurrentWidget(self.login_panel)


class MainWindow(FluentWindow):
    """主窗口类

    使用 Fluent Design 风格的主窗口。
    包含主界面和设置界面。
    """

    def __init__(self) -> None:
        super().__init__()
        self._init_ui()
        self._setup_interfaces()
        self._set_qss()
        self._connect_signals()

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.setWindowTitle("弹幕姬")
        self.resize(1200, 800)

        # 设置窗口居中
        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

    def _setup_interfaces(self) -> None:
        """设置界面"""
        # 创建主界面
        self.main_interface = MainInterface(self)
        self.main_interface.setObjectName("mainInterface")

        # 创建设置界面
        self.settings_interface = SettingsInterface(self)
        self.settings_interface.setObjectName("settingsInterface")

        # 添加主界面到导航栏
        self.addSubInterface(
            self.main_interface, FIF.HOME, "主页", NavigationItemPosition.TOP
        )

        # 添加设置界面到导航栏
        self.addSubInterface(
            self.settings_interface, FIF.SETTING, "设置", NavigationItemPosition.BOTTOM
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
