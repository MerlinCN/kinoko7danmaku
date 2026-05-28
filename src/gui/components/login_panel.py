"""登录面板 - 未登录界面"""

import asyncio
import hashlib
import json
import time
import urllib.parse

from io import BytesIO

import httpx
import qrcode as qr
import stream_gears

from PySide6.QtCore import QSize, QTimer, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from faker import Faker
from loguru import logger
from qasync import asyncSlot
from qfluentwidgets import BodyLabel, ImageLabel, PushButton

from bilibili import bili_service
from core.const import COOKIES_PATH


class LoginPanel(QWidget):
    """登录面板

    未登录时显示二维码，用户扫描二维码完成登录。
    """

    # 登录成功信号
    login_success = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._qr_data = None
        self._login_timer = None  # 登录轮询定时器
        self._init_ui()
        self._load_qr_code()

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.setSpacing(16)
        # 二维码容器
        qr_container_layout = QHBoxLayout()
        qr_container_layout.setAlignment(Qt.AlignCenter)

        self.qr_label = ImageLabel()
        qr_container_layout.addWidget(self.qr_label)
        self.main_layout.addLayout(qr_container_layout)

        # 提示文本
        self.hint_label = BodyLabel('用 B 站 App 进行登录')
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.hint_label)

        # 按钮和勾选框
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.setSpacing(12)

        self.refresh_btn = PushButton('刷新二维码')
        self.refresh_btn.clicked.connect(self._on_refresh_qr)
        button_layout.addWidget(self.refresh_btn)
        self.main_layout.addLayout(button_layout)

        # 状态标签
        self.status_label = BodyLabel('登录状态: 未登录 ❌')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.status_label)

        # 弹性空间
        self.main_layout.addStretch()

    @asyncSlot()
    async def _load_qr_code(self) -> None:
        """加载二维码"""
        if COOKIES_PATH.exists():
            # 检查 cookies 是否有效
            try:
                stream_gears.login_by_cookies(str(COOKIES_PATH), proxy=None)
                logger.info('检测到有效的登录信息')
                self._on_login_success()
            except RuntimeError as e:
                logger.warning(f'登录信息过期: {e}')
                if COOKIES_PATH.exists():
                    COOKIES_PATH.unlink()
            else:
                return

        # 获取新的二维码
        logger.info('获取二维码...')
        qrcode_response = stream_gears.get_qrcode(proxy=None)
        self._qr_data = json.loads(qrcode_response)

        if self._qr_data.get('code') != 0:
            self.status_label.setText(f'获取二维码失败: {self._qr_data}')
            return

        # 获取二维码 URL 并转换为图片
        qr_url = self._qr_data['data']['url']
        logger.info(f'二维码 URL: {qr_url}')

        # 使用 qrcode 库生成二维码
        qr_img = qr.make(qr_url)
        # 通过 BytesIO 转换
        buf = BytesIO()
        qr_img.save(buf, format='PNG')
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())

        # 直接使用
        self.qr_label.setImage(pixmap)
        self.qr_label.setScaledSize(QSize(280, 280))

        self.status_label.setText('登录状态: 等待扫描 ⏳')

        # 使用 QTimer 定时轮询（不阻塞界面）
        self._start_polling_timer()

    def _on_refresh_qr(self) -> None:
        """刷新二维码"""
        if self._login_timer is not None:
            self._login_timer.stop()
        self._load_qr_code()

    def _start_polling_timer(self) -> None:
        """启动定时轮询"""
        if self._login_timer is not None:
            self._login_timer.stop()

        self._login_timer = QTimer(self)
        self._login_timer.timeout.connect(self._check_login_status)
        self._login_timer.start(2000)  # 每 2 秒检查一次
        logger.info('开始定时轮询登录状态...')

    def _sync_check_qrcode(self, params: dict, headers: dict) -> dict:
        """同步检查二维码状态（在线程中执行）

        Args:
            params: 请求参数
            headers: 请求头

        Returns:
            B站 API 响应结果
        """
        with httpx.Client() as client:
            response = client.post(
                'https://passport.bilibili.com/x/passport-tv-login/qrcode/poll',
                params=params,
                headers=headers,
                timeout=5,
            )
            return response.json()

    @asyncSlot()
    async def _check_login_status(self) -> None:
        """检查登录状态（单次检查，不阻塞）"""
        if self._qr_data is None:
            return

        try:
            # 构建请求参数
            params = {
                'appkey': '4409e2ce8ffd12b8',
                'auth_code': self._qr_data['data']['auth_code'],
                'local_id': '0',
                'ts': int(time.time()),
            }
            params['sign'] = hashlib.md5(
                f'{urllib.parse.urlencode(params)}59b43e04ad6965f34319062b478f83dd'.encode()
            ).hexdigest()

            fake = Faker()
            headers = {
                'User-Agent': fake.chrome(),
                'Referer': 'https://passport.bilibili.com/',
            }

            # 在线程池中执行网络请求（不阻塞事件循环）
            result = await asyncio.to_thread(self._sync_check_qrcode, params, headers)

        except httpx.TimeoutException:
            logger.warning('请求超时，将在下次轮询重试')
            return
        except Exception as e:
            logger.error(f'检查登录状态失败: {e}')
            return

        code = result.get('code')
        data = result.get('data')
        if code == 0:  # 登录成功
            logger.info('登录成功!')
            # 立即清空二维码数据，防止后续触发的定时器继续执行
            self._qr_data = None
            if self._login_timer is not None:
                self._login_timer.stop()

            # 保存登录信息
            if COOKIES_PATH.exists():
                COOKIES_PATH.unlink()
            COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
            content = json.dumps(data, indent=4, ensure_ascii=False)
            await asyncio.to_thread(COOKIES_PATH.write_text, content, encoding='utf-8')

            self._on_login_success()

        elif code == 86038:  # 二维码已过期
            logger.warning('二维码已过期')
            self._qr_data = None
            if self._login_timer is not None:
                self._login_timer.stop()
            self.status_label.setText('登录状态: 二维码已过期 ❌')

        elif code == 86090:  # 已扫描未确认
            logger.info('二维码已扫描，等待确认')
            self.status_label.setText('登录状态: 已扫描，请确认 📱')

        elif code == 86039:  # 未扫描
            logger.debug('等待扫描...')

        else:
            logger.warning(f'未知状态码: {code}, 响应: {result}')

    def _on_login_success(self) -> None:
        """登录成功"""
        self.status_label.setText('登录状态: 已登录 ✅')
        self.qr_label.setText('')
        self.qr_label.setPixmap(QPixmap())
        bili_service.load_credential()
        # 延迟发送信号，让 UI 更新
        QTimer.singleShot(500, lambda: self.login_success.emit())
