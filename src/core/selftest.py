"""打包产物自检的报告落地

PyInstaller 打出来的是窗口程序，启动时没有标准输出，异常也就无从查看。
带 `--selftest` 启动时把 `sys.excepthook` 换成写文件，连导入阶段的失败也能留下 traceback。
本模块必须比 `gui` 先导入，钩子才装得上。
"""

import sys
import traceback
import types

from pathlib import Path

REPORT = Path.cwd() / 'selftest.txt'
SELFTEST = '--selftest' in sys.argv


def write_report(text: str) -> None:
    """写入自检报告

    Args:
        text: 报告内容
    """
    REPORT.write_text(text, encoding='utf-8')


def _excepthook(exc_type: type[BaseException], exc: BaseException, tb: types.TracebackType | None) -> None:
    """把未捕获的异常写进报告文件

    Args:
        exc_type: 异常类型
        exc: 异常对象
        tb: 异常堆栈
    """
    write_report(''.join(traceback.format_exception(exc_type, exc, tb)))


if SELFTEST:
    sys.excepthook = _excepthook
