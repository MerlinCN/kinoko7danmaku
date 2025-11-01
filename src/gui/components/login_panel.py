"""登录面板 - 未登录界面"""

import json
from pathlib import Path

import stream_gears
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
)
from qfluentwidgets import TitleLabel, BodyLabel, CaptionLabel
from qasync import asyncSlot
from loguru import logger


class LoginPanel(QWidget):
    """登录面板

    未登录时显示二维码，用户扫描二维码完成登录。
    """

    # 登录成功信号
    login_success = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._qr_data = None
        self._init_ui()
        self._load_qr_code()

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.setSpacing(16)

        # 标题
        self.title_label = TitleLabel("B 站登录")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.title_label)

        # 二维码容器
        qr_container_layout = QHBoxLayout()
        qr_container_layout.setAlignment(Qt.AlignCenter)

        self.qr_label = QLabel()
        self.qr_label.setFixedSize(300, 300)
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setStyleSheet(
            "border: 1px solid #cccccc; border-radius: 4px; background: white;"
        )
        qr_container_layout.addWidget(self.qr_label)
        self.main_layout.addLayout(qr_container_layout)

        # 提示文本
        self.hint_label = BodyLabel("扫描二维码用 B 站 App 进行登录")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.hint_label)

        # 按钮和勾选框
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.setSpacing(12)

        self.refresh_btn = QPushButton("刷新二维码")
        self.refresh_btn.setFixedWidth(120)
        self.refresh_btn.clicked.connect(self._on_refresh_qr)
        button_layout.addWidget(self.refresh_btn)

        self.auto_login_check = QCheckBox("自动登录")
        button_layout.addWidget(self.auto_login_check)

        self.main_layout.addLayout(button_layout)

        # 状态标签
        self.status_label = CaptionLabel("登录状态: 未登录 ❌")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.status_label)

        # 弹性空间
        self.main_layout.addStretch()

    @asyncSlot()
    async def _load_qr_code(self) -> None:
        """加载二维码"""
        try:
            cookies_path = Path("cookies.json")
            if cookies_path.exists():
                # 检查 cookies 是否有效
                try:
                    stream_gears.login_by_cookies(str(cookies_path), proxy=None)
                    logger.info("检测到有效的登录信息")
                    self._on_login_success()
                    return
                except RuntimeError as e:
                    logger.warning(f"登录信息过期: {e}")
                    cookies_path.unlink()

            # 获取新的二维码
            logger.info("获取二维码...")
            qrcode_response = stream_gears.get_qrcode(proxy=None)
            self._qr_data = json.loads(qrcode_response)

            if self._qr_data.get("code") != 0:
                self.status_label.setText(f"获取二维码失败: {self._qr_data}")
                return

            # 获取二维码 URL 并转换为图片
            qr_url = self._qr_data["data"]["url"]
            logger.info(f"二维码 URL: {qr_url}")

            # 使用 qrcode 库生成二维码
            try:
                import qrcode as qr

                qr_img = qr.make(qr_url)
                qr_img = qr_img.convert("RGB")

                # 转换为 QPixmap
                data = qr_img.tobytes("raw", "RGB")
                image = QImage(data, qr_img.width, qr_img.height, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(image)

                # 缩放到标签大小
                scaled_pixmap = pixmap.scaledToWidth(280, Qt.SmoothTransformation)
                self.qr_label.setPixmap(scaled_pixmap)

                self.status_label.setText("登录状态: 等待扫描 ⏳")

                # 开始轮询等待登录
                await self._start_login_polling(qrcode_response)
            except ImportError:
                logger.error("qrcode 库未安装")
                self.status_label.setText("错误: 未安装 qrcode 库")
        except Exception as e:
            logger.error(f"加载二维码失败: {e}")
            self.status_label.setText(f"加载失败: {str(e)}")

    def _on_refresh_qr(self) -> None:
        """刷新二维码"""
        self._load_qr_code()

    async def _start_login_polling(self, qrcode_response: str) -> None:
        """开始轮询等待登录"""
        try:
            logger.info("等待用户扫码...")
            login_response = stream_gears.login_by_qrcode(qrcode_response, proxy=None)
            login_info = json.loads(login_response)

            if login_info.get("code") == 0:
                logger.info("登录成功!")
                # 保存登录信息
                cookies_path = Path("cookies.json")
                with open(cookies_path, "w", encoding="utf-8") as f:
                    json.dump(login_info, f, indent=2, ensure_ascii=False)

                self._on_login_success()
            else:
                error_msg = login_info.get("message", "未知错误")
                logger.error(f"登录失败: {error_msg}")
                self.status_label.setText(f"登录失败: {error_msg}")
        except Exception as e:
            logger.error(f"轮询过程中出错: {e}")
            self.status_label.setText(f"错误: {str(e)}")

    def _on_login_success(self) -> None:
        """登录成功"""
        self.status_label.setText("登录状态: 已登录 ✅")
        self.qr_label.setText("")
        self.qr_label.setPixmap(QPixmap())

        # 延迟发送信号，让 UI 更新
        QTimer.singleShot(500, lambda: self.login_success.emit())
