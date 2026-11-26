"""主窗口"""

import asyncio

from pathlib import Path

from PySide6.QtCore import QEvent, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)
from bilibili_api.utils import network
from loguru import logger
from qasync import asyncSlot
from qfluentwidgets import (
    Action,
    BodyLabel,
    FluentWindow,
    ImageLabel,
    IndeterminateProgressRing,
    InfoBar,
    InfoBarPosition,
    NavigationItemPosition,
    StateToolTip,
    SystemTrayMenu,
    ToolButton,
    isDarkTheme,
    qconfig,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from bilibili import bili_service
from core import updater
from core.const import AUTHOR_BILIBILI_URL, GITHUB_URL, RESOURCE_DIR
from core.player import audio_player
from core.update_checker import UpdateChecker, VersionInfo
from gui.components import HomePanel, LoginPanel
from gui.icons import CustomIcon

from .audio_test import AudioTestInterface
from .minimax import (
    MinimaxHomeInterface,
    MinimaxVoiceCloneInterface,
    MinimaxVoiceListInterface,
)
from .settings import SettingsInterface


def get_resource_path(relative_path: str) -> Path:
    """获取资源文件的绝对路径（支持 PyInstaller 打包）

    Args:
        relative_path: 相对于 resource 目录的路径

    Returns:
        资源文件的绝对路径
    """
    return RESOURCE_DIR / relative_path


class StartupPanel(QWidget):
    """启动加载面板

    应用启动后在检查登录状态期间展示，避免出现空白界面。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化启动加载面板

        Args:
            parent: 父组件
        """
        super().__init__(parent=parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        self.icon_label = ImageLabel(self)
        self.icon_label.setImage(QIcon(str(get_resource_path('icon.ico'))).pixmap(72, 72))
        self.icon_label.setFixedSize(72, 72)
        layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.ring = IndeterminateProgressRing(self)
        self.ring.setFixedSize(32, 32)
        self.ring.setStrokeWidth(3)
        layout.addWidget(self.ring, 0, Qt.AlignmentFlag.AlignHCenter)

        self.hint_label = BodyLabel('正在检查登录状态', self)
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint_label)

        self.ring.start()


class MainInterface(QWidget):
    """主界面

    包含启动加载、扫码登录与直播控制台三个页面，按登录状态切换。
    """

    open_settings = Signal()
    open_audio_test = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        self.stacked_widget = QStackedWidget(self)
        layout.addWidget(self.stacked_widget)

        self.startup_panel = StartupPanel(self.stacked_widget)

        self.login_panel = LoginPanel(self.stacked_widget)
        self.login_panel.login_success.connect(self._on_login_success)

        self.home_panel = HomePanel(self.stacked_widget)
        self.home_panel.logout_requested.connect(self._on_logout)
        self.home_panel.open_settings.connect(self.open_settings.emit)
        self.home_panel.open_audio_test.connect(self.open_audio_test.emit)

        self.stacked_widget.addWidget(self.startup_panel)
        self.stacked_widget.addWidget(self.login_panel)
        self.stacked_widget.addWidget(self.home_panel)

    @asyncSlot()
    async def start(self) -> None:
        """启动时恢复登录状态，未登录则获取登录二维码"""
        restored = await bili_service.restore_credential()
        self.startup_panel.ring.stop()

        if restored:
            self._show_home()
            return

        self.stacked_widget.setCurrentWidget(self.login_panel)
        await self.login_panel.load_qr_code()

    def _show_home(self) -> None:
        """切换到直播控制台"""
        self.stacked_widget.setCurrentWidget(self.home_panel)
        self.home_panel.refresh()

    def _on_login_success(self) -> None:
        """登录成功的回调"""
        logger.info('登录成功，切换到主页面')
        self._show_home()

    @asyncSlot()
    async def _on_logout(self) -> None:
        """退出登录的回调"""
        await bili_service.logout()

        self.stacked_widget.setCurrentWidget(self.login_panel)
        await self.login_panel.load_qr_code()


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
        QTimer.singleShot(0, self.main_interface.start)
        QTimer.singleShot(0, self._on_update)

    def _start_audio_worker(self) -> None:
        """启动音频播放队列"""
        audio_player.start_worker()
        logger.info('应用启动，音频播放队列已启动')

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.setWindowTitle('弹幕姬')
        self.setWindowIcon(QIcon(str(get_resource_path('icon.ico'))))
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
        self.main_interface.setObjectName('mainInterface')

        # 创建音频测试界面
        self.audio_test_interface = AudioTestInterface(self)
        self.audio_test_interface.setObjectName('audioTestInterface')
        self.audio_test_interface.open_settings.connect(self._open_settings_page)

        # 创建 MiniMax 音色相关界面
        self.minimax_interface = MinimaxHomeInterface(self)
        self.minimax_interface.setObjectName('minimaxInterface')
        self.minimax_interface.open_voice_list.connect(lambda: self.switchTo(self.minimax_voice_list_interface))
        self.minimax_interface.open_voice_clone.connect(lambda: self.switchTo(self.minimax_voice_clone_interface))

        self.minimax_voice_list_interface = MinimaxVoiceListInterface(self)
        self.minimax_voice_list_interface.setObjectName('minimaxVoiceListInterface')

        self.minimax_voice_clone_interface = MinimaxVoiceCloneInterface(self)
        self.minimax_voice_clone_interface.setObjectName('minimaxVoiceCloneInterface')

        # 创建设置界面
        self.settings_interface = SettingsInterface(self)
        self.settings_interface.setObjectName('settingsInterface')

        # 主页快捷入口
        self.main_interface.open_settings.connect(self._open_settings_page)
        self.main_interface.open_audio_test.connect(self._open_audio_test_page)

        # 添加主界面到导航栏
        self.addSubInterface(self.main_interface, FIF.HOME, '主页', NavigationItemPosition.TOP)

        # 添加音频测试界面到导航栏
        self.addSubInterface(self.audio_test_interface, FIF.MUSIC, '音频测试', NavigationItemPosition.TOP)

        # 添加 MiniMax 父菜单和子菜单
        self.addSubInterface(
            self.minimax_interface,
            CustomIcon.MINIMAX,
            'MiniMax',
            NavigationItemPosition.TOP,
        )
        self.addSubInterface(
            self.minimax_voice_list_interface,
            FIF.LIBRARY,
            '音色列表',
            parent=self.minimax_interface,
        )
        self.addSubInterface(
            self.minimax_voice_clone_interface,
            FIF.MICROPHONE,
            '音色克隆',
            parent=self.minimax_interface,
        )

        # 启用 MiniMax 菜单的展开状态记忆
        self.navigationInterface.widget('minimaxInterface').setRememberExpandState(True)

        self.navigationInterface.addItem(
            routeKey='update',
            icon=FIF.UPDATE,
            text='更新',
            onClick=lambda: self._on_update(is_force=True),
            selectable=False,
            tooltip='更新',
            position=NavigationItemPosition.BOTTOM,
        )

        self.navigationInterface.addItem(
            routeKey='author_bilibili',
            icon=CustomIcon.BILIBILI,
            text='B站',
            onClick=lambda: QDesktopServices.openUrl(QUrl(AUTHOR_BILIBILI_URL)),
            selectable=False,
            tooltip='B站',
            position=NavigationItemPosition.BOTTOM,
        )

        self.navigationInterface.addItem(
            routeKey='github',
            icon=FIF.GITHUB,
            text='GitHub',
            onClick=lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL)),
            selectable=False,
            tooltip='GitHub',
            position=NavigationItemPosition.BOTTOM,
        )
        # 添加设置界面到导航栏
        self.addSubInterface(self.settings_interface, FIF.SETTING, '设置', NavigationItemPosition.BOTTOM)

    def _open_settings_page(self) -> None:
        """打开设置页"""
        self.switchTo(self.settings_interface)

    def _open_audio_test_page(self) -> None:
        """打开音频测试页"""
        self.switchTo(self.audio_test_interface)

    @asyncSlot()
    async def _on_update(self, is_force: bool = False) -> None:
        """检查更新

        Args:
            is_force: 是否强制检查（忽略检查间隔）
        """
        self.progress_ring.start()
        version_info = await asyncio.to_thread(UpdateChecker.check_update, is_force)
        self.progress_ring.stop()

        if not version_info:
            InfoBar.success(
                title='版本检测',
                content='没有发现新版本',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM,
                duration=2000,
                parent=self,
            )
            return

        bar = InfoBar.new(
            icon=FIF.UPDATE,
            title='发现新版本',
            content=f'当前版本 v{UpdateChecker.get_current_version()}，最新版本 {version_info.version}',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM,
            duration=-1,
            parent=self,
        )
        download_button = ToolButton(FIF.DOWNLOAD)
        download_button.setToolTip('自动更新' if self._can_auto_update(version_info) else '打开下载页面')
        download_button.clicked.connect(lambda: self._start_update(version_info))
        bar.addWidget(download_button)

    @staticmethod
    def _can_auto_update(version_info: VersionInfo) -> bool:
        """判断当前环境能否自动更新

        Args:
            version_info: 版本信息

        Returns:
            支持自动更新且安装目录可写时返回 True
        """
        return (
            updater.is_supported()
            and bool(version_info.asset_url and version_info.checksum_url)
            and updater.can_write_install_dir()
        )

    def _start_update(self, version_info: VersionInfo) -> None:
        """开始更新，无法自动更新时打开下载页面

        Args:
            version_info: 版本信息
        """
        if not self._can_auto_update(version_info):
            QDesktopServices.openUrl(QUrl(version_info.download_url))
            return
        self._download_and_apply(version_info)

    @asyncSlot()
    async def _download_and_apply(self, version_info: VersionInfo) -> None:
        """下载更新包，完成后退出并重启

        Args:
            version_info: 版本信息
        """
        tooltip = StateToolTip('正在下载更新', '0%', self)
        tooltip.move(tooltip.getSuitablePos())
        tooltip.show()

        try:
            new_exe = await updater.download_update(
                version_info.asset_url,
                version_info.checksum_url,
                lambda percent: tooltip.setContent(f'{percent}%'),
            )
        except Exception as e:
            logger.warning(f'下载更新失败: {e!r}')
            tooltip.setState(False)
            tooltip.setTitle('更新失败')
            tooltip.setContent(str(e))
            return

        tooltip.setState(True)
        tooltip.setTitle('更新已就绪')
        tooltip.setContent('应用将退出并重启完成更新')
        updater.apply_update(new_exe)
        QTimer.singleShot(1200, self.close)

    def _set_qss(self) -> None:
        """设置样式表

        根据当前主题加载对应的 QSS 文件，应用到整个应用。
        """
        # 根据当前主题加载对应的 qss 文件
        theme = 'dark' if isDarkTheme() else 'light'
        qss_path = get_resource_path(f'qss/{theme}/main_window.qss')

        if qss_path.exists():
            self.setStyleSheet(qss_path.read_text(encoding='utf-8'))

    def _on_theme_changed(self) -> None:
        """主题改变时的回调"""
        self._set_qss()

    def _setup_system_tray(self) -> None:
        """设置系统托盘图标"""
        # 创建系统托盘图标
        self.system_tray_icon = QSystemTrayIcon(self)
        self.system_tray_icon.setIcon(self.windowIcon())
        self.system_tray_icon.setToolTip('弹幕姬')

        # 创建托盘菜单
        self.tray_menu = SystemTrayMenu(parent=self)
        self.show_action = Action(FIF.VIEW, '显示主窗口', triggered=self._show_window)
        self.quit_action = Action(FIF.CLOSE, '退出', triggered=self.close)

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
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized():
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
        logger.info('应用退出，正在停止音频播放队列')
        await audio_player.stop_worker()

        # run_forever() 返回后（QApplication.quit() 被调用后）
        # 在事件循环关闭前，手动清理 bilibili_api 的 session
        async def cleanup_bilibili_sessions() -> None:
            for pool in network.session_pool.values():
                for client in pool.values():
                    await client.close()

        await cleanup_bilibili_sessions()
        # 关闭应用
        QApplication.quit()
        event.accept()

    def _connect_signals(self) -> None:
        """连接信号"""
        # 连接主题切换信号
        qconfig.themeChanged.connect(self._on_theme_changed)
