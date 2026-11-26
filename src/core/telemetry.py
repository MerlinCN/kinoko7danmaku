"""错误上报

Sentry 只接收异常堆栈、日志面包屑与少量环境标签，发送前统一脱敏。
DSN 由打包脚本（build.ps1 / GitHub Actions）在打包时写入 `resource/telemetry.json`，
仓库里不保存；读不到 DSN 或用户在设置里关闭开关时，完全不上报。
"""

import asyncio
import json
import platform
import re
import sys

from functools import singledispatch
from typing import Any

import sentry_sdk

from loguru import logger
from sentry_sdk.integrations.loguru import LoggingLevels, LoguruIntegration

from .const import RESOURCE_DIR
from .qconfig import cfg
from .version import get_version, is_packaged

TELEMETRY_FILE = RESOURCE_DIR / 'telemetry.json'

# 上报前需要打码的内容：鉴权头、B 站登录态、各类密钥
_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r'(?i)(bearer\s+)[\w\-.=]+'), r'\1***'),
    (re.compile(r'(?i)(sessdata=)[^;&\s"\']+'), r'\1***'),
    (re.compile(r'(?i)(bili_jct=)[^;&\s"\']+'), r'\1***'),
    (
        re.compile(r'(?i)((?:api[_-]?key|api_?secret|token|password)["\']?\s*[:=]\s*)(["\']?)[^\s,}"\']*'),
        r'\1\2***',
    ),
    (re.compile(r'sk-[A-Za-z0-9_-]{12,}'), 'sk-***'),
)


def scrub(text: str) -> str:
    """对文本做敏感信息打码

    Args:
        text: 原始文本

    Returns:
        打码后的文本
    """
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


@singledispatch
def scrub_value(value: Any) -> Any:
    """递归打码任意结构里的字符串

    Args:
        value: 事件里的任意字段

    Returns:
        打码后的同结构数据
    """
    return value


@scrub_value.register(str)
def _(value: str) -> str:
    return scrub(value)


@scrub_value.register(dict)
def _(value: dict[str, Any]) -> dict[str, Any]:
    return {key: scrub_value(item) for key, item in value.items()}


@scrub_value.register(list)
def _(value: list[Any]) -> list[Any]:
    return [scrub_value(item) for item in value]


@scrub_value.register(tuple)
def _(value: tuple[Any, ...]) -> tuple[Any, ...]:
    return tuple(scrub_value(item) for item in value)


def _before_send(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    """事件发送前的最后一道脱敏"""
    return scrub_value(event)


def _before_breadcrumb(crumb: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    """面包屑发送前的脱敏"""
    return scrub_value(crumb)


def _load_dsn() -> str:
    """读取打包时注入的 DSN

    Returns:
        DSN 字符串；配置文件缺失或损坏时为空，调用方据此跳过上报
    """
    if not TELEMETRY_FILE.exists():
        return ''
    try:
        data = json.loads(TELEMETRY_FILE.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        logger.warning(f'读取上报配置失败: {e!r}')
        return ''
    return str(data.get('sentry_dsn') or '')


def init_telemetry() -> None:
    """按配置初始化 Sentry；没有 DSN 或用户关闭时不做任何事"""
    dsn = _load_dsn()
    if not dsn or not cfg.telemetryEnabled.value:
        return

    sentry_sdk.init(
        dsn=dsn,
        release=get_version(),
        environment='frozen' if is_packaged() else 'dev',
        traces_sample_rate=0.0,
        max_request_body_size='never',
        data_collection={
            'user_info': False,
            'cookies': {'mode': 'off'},
            'http_headers': {'request': {'mode': 'off'}},
            'http_bodies': [],
            'url_query_params': {'mode': 'off'},
            'stack_frame_variables': False,
        },
        integrations=[
            LoguruIntegration(
                event_level=LoggingLevels.ERROR,
                breadcrumb_level=LoggingLevels.WARNING,
            )
        ],
        before_send=_before_send,
        before_breadcrumb=_before_breadcrumb,
    )
    sentry_sdk.set_tag('os', sys.platform)
    sentry_sdk.set_tag('arch', platform.machine())
    sentry_sdk.set_tag('tts', str(cfg.activeTTS.value))
    logger.info('错误上报已启用')


def install_loop_hook(loop: asyncio.AbstractEventLoop) -> None:
    """把事件循环里未捕获的异常上报到 Sentry

    Args:
        loop: 应用事件循环
    """

    def handler(current: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        current.default_exception_handler(context)
        exception = context.get('exception')
        if exception is not None and sentry_sdk.is_initialized():
            sentry_sdk.capture_exception(exception)

    loop.set_exception_handler(handler)
