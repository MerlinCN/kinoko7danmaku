"""登录面板 - 未登录界面"""

import asyncio
import hashlib
import json
import time
import urllib.parse

from io import BytesIO
from typing import Any

import httpx
import qrcode as qr
import stream_gears

from PySide6.QtCore import QSize, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from faker import Faker
from loguru import logger
from qasync import asyncSlot
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    ImageLabel,
    SubtitleLabel,
    TransparentPushButton,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from bilibili import bili_service
from core.const import COOKIES_PATH
from gui.components.status_pill import StatusPill

_MUTED_COLOR = '#8a8a8a'
_WARN_COLOR = '#d99100'
_OK_COLOR = '#2fa84f'
_ERROR_COLOR = '#d64545'


class LoginPanel(QWidget):
    """登录面板

    未登录时展示登录二维码，用户使用 B 站手机客户端扫码完成登录。
    """

    login_success = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化登录面板

        Args:
            parent: 父组件
        """
        super().__init__(parent=parent)
        self._auth_code: str | None = None
        self._login_timer: QTimer | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI"""
        outer_layout = QVBoxLayout(self)
        outer_layout.setSpacing(12)

        self.card = CardWidget(self)
        self.card.setFixedWidth(400)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(36, 32, 36, 28)
        card_layout.setSpacing(16)

        title_label = SubtitleLabel('扫码登录', self.card)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_label)

        hint_label = CaptionLabel('使用 B 站手机客户端扫描二维码', self.card)
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(hint_label)

        self.qr_box = QWidget(self.card)
        self.qr_box.setFixedSize(236, 236)
        self.qr_box.setStyleSheet('background-color: #ffffff; border-radius: 8px;')
        qr_box_layout = QVBoxLayout(self.qr_box)
        qr_box_layout.setContentsMargins(8, 8, 8, 8)

        self.qr_pages = QStackedWidget(self.qr_box)
        self.qr_label = ImageLabel(self.qr_pages)
        self.qr_label.setFixedSize(220, 220)
        self.qr_label.setScaledSize(QSize(220, 220))
        self.qr_placeholder = BodyLabel('正在获取二维码', self.qr_pages)
        self.qr_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_placeholder.setTextColor(QColor(_MUTED_COLOR), QColor(_MUTED_COLOR))
        self.qr_pages.addWidget(self.qr_label)
        self.qr_pages.addWidget(self.qr_placeholder)
        qr_box_layout.addWidget(self.qr_pages)
        card_layout.addWidget(self.qr_box, 0, Qt.AlignmentFlag.AlignHCenter)

        self.status_pill = StatusPill(self.card)
        card_layout.addWidget(self.status_pill, 0, Qt.AlignmentFlag.AlignHCenter)

        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.refresh_btn = TransparentPushButton('刷新二维码', self.card)
        self.refresh_btn.setIcon(FIF.SYNC)
        self.refresh_btn.clicked.connect(self._on_refresh_qr)
        button_layout.addWidget(self.refresh_btn)
        card_layout.addLayout(button_layout)

        outer_layout.addStretch(1)
        outer_layout.addWidget(self.card, 0, Qt.AlignmentFlag.AlignHCenter)

        footer_label = CaptionLabel('登录信息仅保存在本机', self)
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer_layout.addWidget(footer_label, 0, Qt.AlignmentFlag.AlignHCenter)
        outer_layout.addStretch(1)

        self._show_status('等待二维码', _MUTED_COLOR)
        self._show_qr_placeholder('正在获取二维码')

    async def load_qr_code(self) -> None:
        """获取并展示登录二维码"""
        self._auth_code = None
        self._stop_polling()
        self._show_status('正在获取二维码', _MUTED_COLOR)
        self._show_qr_placeholder('正在获取二维码')
        self.refresh_btn.setEnabled(False)

        try:
            qrcode_response = await asyncio.to_thread(stream_gears.get_qrcode, proxy=None)
        except Exception as e:
            logger.error(f'获取二维码失败: {e!r}')
            self._show_status('获取二维码失败', _ERROR_COLOR)
            self._show_qr_placeholder('获取失败')
            self.refresh_btn.setEnabled(True)
            return

        data: dict[str, Any] = json.loads(qrcode_response)
        if data.get('code') != 0:
            logger.error(f'获取二维码失败: {data}')
            self._show_status('获取二维码失败', _ERROR_COLOR)
            self._show_qr_placeholder('获取失败')
            self.refresh_btn.setEnabled(True)
            return

        qr_data: dict[str, Any] = data['data']
        self._auth_code = qr_data['auth_code']

        qr_img = qr.make(qr_data['url'])
        buf = BytesIO()
        qr_img.save(buf, format='PNG')
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())

        self.qr_label.setImage(pixmap)
        self.qr_label.setScaledSize(QSize(220, 220))
        self.qr_pages.setCurrentWidget(self.qr_label)
        self.refresh_btn.setEnabled(True)
        self._show_status('等待扫描', _MUTED_COLOR)
        self._start_polling_timer()

    def _show_status(self, text: str, color: str) -> None:
        """更新登录状态提示

        Args:
            text: 状态文案
            color: 状态颜色
        """
        self.status_pill.set_status(text, color)

    def _show_qr_placeholder(self, text: str) -> None:
        """在二维码区域展示占位文案

        Args:
            text: 占位文案
        """
        self.qr_placeholder.setText(text)
        self.qr_pages.setCurrentWidget(self.qr_placeholder)

    @asyncSlot()
    async def _on_refresh_qr(self) -> None:
        """刷新二维码"""
        await self.load_qr_code()

    def _stop_polling(self) -> None:
        """停止登录状态轮询"""
        if self._login_timer is not None:
            self._login_timer.stop()

    def _start_polling_timer(self) -> None:
        """启动登录状态轮询"""
        if self._login_timer is not None:
            self._login_timer.stop()

        self._login_timer = QTimer(self)
        self._login_timer.timeout.connect(self._poll_login_status)
        self._login_timer.start(2000)  # 每 2 秒检查一次
        logger.info('开始定时轮询登录状态...')

    def _sync_check_qrcode(self, params: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
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
    async def _poll_login_status(self) -> None:
        """轮询一次登录状态"""
        if self._auth_code is None:
            return

        try:
            params: dict[str, Any] = {
                'appkey': '4409e2ce8ffd12b8',
                'auth_code': self._auth_code,
                'local_id': '0',
                'ts': int(time.time()),
            }
            params['sign'] = hashlib.md5(
                f'{urllib.parse.urlencode(params)}59b43e04ad6965f34319062b478f83dd'.encode()
            ).hexdigest()

            headers = {
                'User-Agent': Faker().chrome(),
                'Referer': 'https://passport.bilibili.com/',
            }

            # 在线程池中执行网络请求（不阻塞事件循环）
            result = await asyncio.to_thread(self._sync_check_qrcode, params, headers)

        except httpx.TimeoutException:
            logger.warning('请求超时，将在下次轮询重试')
            return
        except Exception as e:
            logger.error(f'检查登录状态失败: {e!r}')
            return

        code = result.get('code')
        if code == 0:
            logger.info('登录成功!')
            self._auth_code = None
            self._stop_polling()
            await self._save_login_info(result['data'])
            self._on_login_success()
        elif code == 86038:
            logger.warning('二维码已过期')
            self._auth_code = None
            self._stop_polling()
            self._show_status('二维码已过期', _WARN_COLOR)
        elif code == 86090:
            self._show_status('已扫描，请在手机上确认', _WARN_COLOR)
        elif code == 86039:
            logger.debug('等待扫描...')
        else:
            logger.warning(f'未知状态码: {code}, 响应: {result}')

    async def _save_login_info(self, login_data: dict[str, Any]) -> None:
        """保存登录信息到本地

        Args:
            login_data: 登录接口返回的数据
        """
        COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(login_data, indent=4, ensure_ascii=False)
        await asyncio.to_thread(COOKIES_PATH.write_text, content, encoding='utf-8')

    def _on_login_success(self) -> None:
        """登录成功"""
        self._show_status('已登录', _OK_COLOR)
        self._show_qr_placeholder('已登录')
        bili_service.load_credential()
        # 延迟发送信号，让状态提示先更新
        QTimer.singleShot(500, self.login_success.emit)
