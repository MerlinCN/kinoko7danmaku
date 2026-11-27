"""GUI 启动脚本"""

import asyncio
import atexit
import multiprocessing
import sys

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from bilibili_api.utils import network
from loguru import logger
from qasync import QApplication, QEventLoop

from core.const import DATA_DIR
from core.selftest import SELFTEST, write_report
from core.telemetry import TELEMETRY_FILE, init_telemetry, install_loop_hook
from gui import MainWindow


def run_selftest() -> int:
    """构建主窗口并绘制一帧，验证打包产物的依赖与资源

    不跑事件循环、不显示窗口，所以不会触发登录恢复、房间信息、更新检查等网络请求。

    Returns:
        进程退出码，0 表示通过；失败时 traceback 由 `core.selftest` 的钩子写进报告
    """
    _app = QApplication([sys.argv[0]])
    window = MainWindow()
    window.grab()
    write_report(f'ok\ntelemetry: {"已注入" if TELEMETRY_FILE.exists() else "未注入"}')
    return 0


def main() -> None:
    """主函数"""

    # 创建日志目录
    log_dir = DATA_DIR / 'logs'
    log_dir.mkdir(exist_ok=True)

    # 添加文件处理器
    logger.add(
        sink=str(log_dir / '{time:YYYY-MM-DD_HH}.log'),
        rotation='1 hour',  # 每小时轮转一次
        retention='30 days',  # 保留 30 天的日志
        level='INFO',  # 只记录 INFO 及以上级别
        encoding='utf-8',  # UTF-8 编码
        format='{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}',
        enqueue=True,  # 异步写入,避免阻塞
        compression='zip',  # 压缩旧日志文件
    )

    # 初始化错误上报（未配置 DSN 或用户关闭开关时自动跳过）
    init_telemetry()

    # 启用高 DPI 支持（Qt6 默认启用，这里只设置缩放策略）
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # 创建应用（使用 qasync 的 QApplication）
    app = QApplication(sys.argv)
    app.setApplicationName('弹幕姬')
    app.setOrganizationName('弹幕姬')

    # 设置应用图标（任务栏图标）
    icon_path = Path.cwd() / 'resource' / 'icon.ico'
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # 取消 bilibili_api 的 atexit 回调，因为 qasync 事件循环会在 atexit 前关闭
    # 导致 run_until_complete 失败
    atexit.unregister(network.__clean)
    # 创建 qasync 事件循环
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    install_loop_hook(loop)
    # 创建主窗口
    window = MainWindow()
    window.show()

    # 使用事件循环运行应用
    with loop:
        loop.run_forever()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    sys.exit(run_selftest() if SELFTEST else main())
