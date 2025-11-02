"""主窗口"""

import asyncio
import sys
from pathlib import Path

from bilibili_api.utils import network
from loguru import logger
from PySide6.QtCore import QEvent, Qt, QTimer, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)
from qasync import asyncSlot
from qfluentwidgets import (
    Action,
    FluentWindow,
    IndeterminateProgressRing,
    InfoBar,
    InfoBarPosition,
    NavigationItemPosition,
    SystemTrayMenu,
    TitleLabel,
    ToolButton,
    isDarkTheme,
    qconfig,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from bilibili import bili_service
from core.const import AUTHOR_BILIBILI_URL, GITHUB_URL
from core.player import audio_player
from core.update_checker import UpdateChecker

from ..components import HomePanel, LoginPanel
from .audio_test import AudioTestInterface
from .settings import SettingsInterface


def get_resource_path(relative_path: str) -> Path:
    """获取资源文件的绝对路径（支持 PyInstaller 打包）

    Args:
        relative_path: 相对于 resource 目录的路径

    Returns:
        资源文件的绝对路径
    """
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后，资源在 _MEIPASS 临时目录
        base_path = Path(sys._MEIPASS)  # type: ignore
    else:
        # 开发环境，资源在项目根目录
        base_path = Path.cwd()
    return base_path / "resource" / relative_path


class MainInterface(QWidget):
    """主界面

    包含登录面板和主页面板的切换。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._setup_ui()
        self._connect_bili_signals()
        self._check_login_status()

    def _setup_ui(self) -> None:
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        self.title_label = TitleLabel("登录", self)
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

    def _connect_bili_signals(self) -> None:
        """连接 B 站服务的信号到消息显示卡片"""
        message_card = self.home_panel.message_display_card

        # 连接各种消息信号到消息显示卡片
        bili_service.danmaku_received.connect(message_card.add_message)
        bili_service.gift_received.connect(message_card.add_message)
        bili_service.guard_received.connect(message_card.add_message)
        bili_service.superchat_received.connect(message_card.add_message)

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
        self._setup_system_tray()
        self._set_qss()
        self._connect_signals()
        # 延迟启动音频播放队列（等待事件循环运行）
        QTimer.singleShot(0, self._start_audio_worker)
        QTimer.singleShot(0, self._on_update)

    def _start_audio_worker(self) -> None:
        """启动音频播放队列"""
        audio_player.start_worker()
        logger.info("应用启动，音频播放队列已启动")

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.setWindowTitle("弹幕姬")
        self.setWindowIcon(QIcon(str(get_resource_path("icon.ico"))))
        self.resize(1200, 800)

        # 设置窗口居中
        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        self.progress_ring = IndeterminateProgressRing(self)
        self.progress_ring.setFixedSize(20, 20)
        # 右上角
        self.progress_ring.move(
            self.width() - self.progress_ring.width() - 10,
            self.height() - self.progress_ring.height() - 10,
        )
        self.progress_ring.stop()

    def _setup_interfaces(self) -> None:
        """设置界面"""
        # 创建主界面
        self.main_interface = MainInterface(self)
        self.main_interface.setObjectName("mainInterface")

        # 创建音频测试界面
        self.audio_test_interface = AudioTestInterface(self)
        self.audio_test_interface.setObjectName("audioTestInterface")

        # 创建设置界面
        self.settings_interface = SettingsInterface(self)
        self.settings_interface.setObjectName("settingsInterface")

        # 添加主界面到导航栏
        self.addSubInterface(
            self.main_interface, FIF.HOME, "主页", NavigationItemPosition.TOP
        )

        # 添加音频测试界面到导航栏
        self.addSubInterface(
            self.audio_test_interface, FIF.MUSIC, "音频测试", NavigationItemPosition.TOP
        )

        self.navigationInterface.addItem(
            routeKey="update",
            icon=FIF.UPDATE,
            text="更新",
            onClick=self._on_update,
            selectable=False,
            tooltip="更新",
            position=NavigationItemPosition.BOTTOM,
        )

        self.navigationInterface.addItem(
            routeKey="author_bilibili",
            icon=FIF.VIDEO,
            text="B站",
            onClick=lambda: QDesktopServices.openUrl(QUrl(AUTHOR_BILIBILI_URL)),
            selectable=False,
            tooltip="B站",
            position=NavigationItemPosition.BOTTOM,
        )

        self.navigationInterface.addItem(
            routeKey="github",
            icon=FIF.GITHUB,
            text="GitHub",
            onClick=lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL)),
            selectable=False,
            tooltip="GitHub",
            position=NavigationItemPosition.BOTTOM,
        )
        # 添加设置界面到导航栏
        self.addSubInterface(
            self.settings_interface, FIF.SETTING, "设置", NavigationItemPosition.BOTTOM
        )

    @asyncSlot()
    async def _on_update(self) -> None:
        """更新"""
        self.progress_ring.start()
        version_info = await asyncio.to_thread(UpdateChecker.check_update)
        self.progress_ring.stop()
        if version_info:
            w = InfoBar.new(
                icon=FIF.GITHUB,
                title="版本检测",
                content=f"当前版本: v{UpdateChecker.get_current_version()}，最新版本: {version_info.version}，是否下载？",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM,
                duration=5000,
                parent=self,
            )
            download_button = ToolButton(FIF.DOWNLOAD)
            download_button.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(version_info.download_url))
            )
            w.addWidget(download_button)
        else:
            w = InfoBar.new(
                icon=FIF.GITHUB,
                title="版本检测",
                content="没有发现新版本",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM,
                duration=2000,
                parent=self,
            )

    def _set_qss(self) -> None:
        """设置样式表

        根据当前主题加载对应的 QSS 文件，应用到整个应用。
        """
        # 根据当前主题加载对应的 qss 文件
        theme = "dark" if isDarkTheme() else "light"
        qss_path = get_resource_path(f"qss/{theme}/main_window.qss")

        if qss_path.exists():
            with open(qss_path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _on_theme_changed(self) -> None:
        """主题改变时的回调"""
        self._set_qss()

    def _setup_system_tray(self) -> None:
        """设置系统托盘图标"""
        # 创建系统托盘图标
        self.system_tray_icon = QSystemTrayIcon(self)
        self.system_tray_icon.setIcon(self.windowIcon())
        self.system_tray_icon.setToolTip("弹幕姬")

        # 创建托盘菜单
        self.tray_menu = SystemTrayMenu(parent=self)
        self.show_action = Action(FIF.VIEW, "显示主窗口", triggered=self._show_window)
        self.quit_action = Action(FIF.CLOSE, "退出", triggered=self.close)

        self.tray_menu.addAction(self.show_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.quit_action)

        self.system_tray_icon.setContextMenu(self.tray_menu)

        # 双击托盘图标显示窗口
        self.system_tray_icon.activated.connect(self._on_tray_icon_activated)

        # 显示系统托盘图标
        self.system_tray_icon.show()

    def _on_tray_icon_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """托盘图标点击事件处理

        Args:
            reason: 激活原因（单击、双击等）
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self) -> None:
        """显示主窗口"""
        self.show()
        self.raise_()
        self.activateWindow()

    def changeEvent(self, event: QEvent) -> None:
        """窗口状态改变事件

        当窗口最小化时，隐藏到系统托盘。

        Args:
            event: 事件对象
        """
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                # 使用 QTimer 延迟隐藏窗口，确保窗口状态完全更新
                QTimer.singleShot(0, self.hide)
        super().changeEvent(event)

    @asyncSlot()
    async def closeEvent(self, event: QCloseEvent) -> None:
        """关闭事件处理

        关闭窗口时退出应用。

        Args:
            event: 关闭事件对象
        """
        # 隐藏系统托盘图标
        self.system_tray_icon.hide()

        # 停止音频播放队列
        logger.info("应用退出，正在停止音频播放队列")
        await audio_player.stop_worker()

        # run_forever() 返回后（QApplication.quit() 被调用后）
        # 在事件循环关闭前，手动清理 bilibili_api 的 session
        async def cleanup_bilibili_sessions():
            for _, pool in network.session_pool.items():
                for _, client in pool.items():
                    await client.close()

        await cleanup_bilibili_sessions()
        # 关闭应用
        QApplication.quit()
        event.accept()

    def _connect_signals(self) -> None:
        """连接信号"""
        # 连接主题切换信号
        qconfig.themeChanged.connect(self._on_theme_changed)
