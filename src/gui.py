"""GUI 启动脚本"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
# 导入主窗口
from gui import MainWindow

def main() -> None:
    """主函数"""
    # 启用高 DPI 支持（Qt6 默认启用，这里只设置缩放策略）
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("Kinoko7 弹幕姬")
    app.setOrganizationName("Kinoko7")


    # 创建主窗口
    window = MainWindow()

    window.show()
    app.exec()

if __name__ == "__main__":
    main()
