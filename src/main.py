"""GUI 启动脚本"""

import asyncio
import atexit
import sys
from pathlib import Path

from bilibili_api.utils import network
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from qasync import QApplication, QEventLoop

from gui import MainWindow


def main() -> None:
    """主函数"""
    # 启用高 DPI 支持（Qt6 默认启用，这里只设置缩放策略）
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 创建应用（使用 qasync 的 QApplication）
    app = QApplication(sys.argv)
    app.setApplicationName("弹幕姬")
    app.setOrganizationName("弹幕姬")

    # 设置应用图标（任务栏图标）
    icon_path = Path.cwd() / "resource" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # 取消 bilibili_api 的 atexit 回调，因为 qasync 事件循环会在 atexit 前关闭
    # 导致 run_until_complete 失败
    atexit.unregister(network.__clean)
    # 创建 qasync 事件循环
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    # 创建主窗口
    window = MainWindow()
    window.show()

    # 使用事件循环运行应用
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
