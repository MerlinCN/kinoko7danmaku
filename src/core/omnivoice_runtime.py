"""OmniVoice 本地运行时管理

在用户目录下维护一套独立的 Python 环境，按显卡后端安装 PyTorch 与 OmniVoice，
并以子进程形式启动常驻合成服务。
"""

import asyncio
import hashlib
import os
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import zipfile

from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import IO

import httpx

from loguru import logger
from pydantic import BaseModel, Field

from core.const import DATA_DIR, get_resource_dir

UV_VERSION = '0.13.10'
PYTHON_VERSION = '3.12'
MODEL_ID = 'k2-fsa/OmniVoice'
SERVER_SCRIPT_NAME = 'omnivoice_server.py'
STARTUP_TIMEOUT = 3600.0

if sys.platform == 'win32':
    CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW
else:
    CREATE_NO_WINDOW = 0


class Backend(StrEnum):
    """推理后端"""

    CUDA = 'cuda'
    MPS = 'mps'


class RuntimeStatus(StrEnum):
    """运行时状态"""

    NOT_INSTALLED = 'not_installed'
    INSTALLED = 'installed'
    RUNNING = 'running'


class BackendInfo(BaseModel):
    """推理后端信息"""

    kind: Backend = Field(..., description='后端类型')
    device_map: str = Field(..., description='模型加载设备')
    dtype: str = Field(..., description='模型精度')
    torch_index_url: str = Field(default='', description='PyTorch 安装索引，为空表示使用 PyPI')
    description: str = Field(..., description='界面展示说明')


class RuntimeState(BaseModel):
    """运行时状态"""

    status: RuntimeStatus = Field(default=RuntimeStatus.NOT_INSTALLED, description='运行状态')
    detail: str = Field(default='', description='状态补充说明')


class RuntimeProgress(BaseModel):
    """安装或启动进度"""

    message: str = Field(..., description='阶段说明')
    percent: int | None = Field(default=None, description='0-100 的百分比，None 表示无法确定')


def _cuda_backend(driver: tuple[int, int]) -> BackendInfo:
    """根据驱动版本选择 CUDA 后端

    Args:
        driver: 驱动版本主次号

    Returns:
        后端信息

    Raises:
        RuntimeError: 驱动版本过低
    """
    if driver >= (580, 0):
        return BackendInfo(
            kind=Backend.CUDA,
            device_map='cuda:0',
            dtype='float16',
            torch_index_url='https://download.pytorch.org/whl/cu130',
            description='NVIDIA GPU · CUDA 13.0 · float16',
        )
    if driver >= (570, 0):
        return BackendInfo(
            kind=Backend.CUDA,
            device_map='cuda:0',
            dtype='float16',
            torch_index_url='https://download.pytorch.org/whl/cu128',
            description='NVIDIA GPU · CUDA 12.8 · float16',
        )
    if driver >= (560, 0):
        return BackendInfo(
            kind=Backend.CUDA,
            device_map='cuda:0',
            dtype='float16',
            torch_index_url='https://download.pytorch.org/whl/cu126',
            description='NVIDIA GPU · CUDA 12.6 · float16',
        )
    raise RuntimeError('显卡驱动版本过低，请先升级到 560 以上再安装')


class OmniVoiceRuntime:
    """OmniVoice 本地运行时"""

    def __init__(self) -> None:
        """初始化运行时管理器"""
        self._process: subprocess.Popen[bytes] | None = None
        self._log_file: IO[bytes] | None = None
        self._pump_thread: threading.Thread | None = None
        self._lock: asyncio.Lock | None = None
        self._backend: BackendInfo | None = None

    @property
    def lock(self) -> asyncio.Lock:
        """延迟创建的异步锁（必须在事件循环启动后使用）

        Returns:
            异步锁
        """
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def runtime_dir(self) -> Path:
        """运行时根目录

        Returns:
            目录路径
        """
        return DATA_DIR / 'runtimes' / 'omnivoice'

    def venv_dir(self) -> Path:
        """虚拟环境目录

        Returns:
            目录路径
        """
        return self.runtime_dir() / 'venv'

    def venv_python(self) -> Path:
        """虚拟环境中的解释器路径

        Returns:
            解释器路径
        """
        if sys.platform == 'win32':
            return self.venv_dir() / 'Scripts' / 'python.exe'
        return self.venv_dir() / 'bin' / 'python'

    def uv_path(self) -> Path:
        """uv 可执行文件路径

        Returns:
            uv 路径
        """
        name = 'uv.exe' if sys.platform == 'win32' else 'uv'
        return self.runtime_dir() / 'uv' / name

    def hub_cache_dir(self) -> Path:
        """HuggingFace 模型缓存目录

        优先使用 HF_HUB_CACHE / HF_HOME，否则与 huggingface_hub 一致落在用户缓存目录。

        Returns:
            目录路径
        """
        hub_cache = os.environ.get('HF_HUB_CACHE')
        if hub_cache:
            return Path(hub_cache)
        hf_home = os.environ.get('HF_HOME')
        if hf_home:
            return Path(hf_home) / 'hub'
        return Path.home() / '.cache' / 'huggingface' / 'hub'

    def model_dir(self) -> Path:
        """模型缓存目录

        Returns:
            目录路径
        """
        return self.hub_cache_dir() / f'models--{MODEL_ID.replace("/", "--")}'

    def server_script(self) -> Path:
        """服务脚本路径

        Returns:
            脚本路径
        """
        return self.runtime_dir() / SERVER_SCRIPT_NAME

    def log_path(self) -> Path:
        """服务日志路径

        Returns:
            日志文件路径
        """
        return self.runtime_dir() / 'server.log'

    def is_installed(self) -> bool:
        """是否已完成安装

        Returns:
            解释器与服务脚本都存在时返回 True
        """
        return self.venv_python().exists() and self.server_script().exists()

    def cached_model_bytes(self) -> int:
        """已缓存的模型体积

        Returns:
            字节数
        """
        root = self.model_dir()
        if not root.exists():
            return 0
        total = 0
        for path in root.rglob('*'):
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
        return total

    def backend(self) -> BackendInfo:
        """获取推理后端（结果缓存）

        Returns:
            后端信息

        Raises:
            RuntimeError: 没有受支持的后端
        """
        if self._backend is not None:
            return self._backend
        self._backend = self._detect_backend()
        return self._backend

    def _detect_backend(self) -> BackendInfo:
        """检测本机推理后端

        Returns:
            后端信息

        Raises:
            RuntimeError: 没有受支持的后端
        """
        if sys.platform == 'darwin' and platform.machine() == 'arm64':
            return BackendInfo(
                kind=Backend.MPS,
                device_map='mps',
                dtype='float32',
                description='Apple Silicon · MPS · float32',
            )

        if sys.platform not in ('win32', 'linux'):
            raise RuntimeError('当前系统不支持本地运行 OmniVoice')

        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW,
            )
        except OSError as e:
            raise RuntimeError('未检测到 NVIDIA 显卡，本地 OmniVoice 仅支持 NVIDIA 显卡与 Apple Silicon') from e

        versions = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if result.returncode != 0 or not versions:
            raise RuntimeError('未检测到 NVIDIA 显卡，本地 OmniVoice 仅支持 NVIDIA 显卡与 Apple Silicon')

        parts = versions[0].split('.')
        return _cuda_backend((int(parts[0]), int(parts[1]) if len(parts) > 1 else 0))

    def _build_env(self, hf_endpoint: str) -> dict[str, str]:
        """构造子进程环境变量

        Args:
            hf_endpoint: HuggingFace 镜像地址

        Returns:
            环境变量字典
        """
        env = os.environ.copy()
        env['UV_PYTHON_INSTALL_DIR'] = str(self.runtime_dir() / 'python')
        env['UV_CACHE_DIR'] = str(self.runtime_dir() / 'uv-cache')
        env['HF_HUB_DISABLE_TELEMETRY'] = '1'
        if hf_endpoint:
            env['HF_ENDPOINT'] = hf_endpoint
        return env

    def _ensure_uv(self, progress: Callable[[str], None]) -> Path:
        """下载并解压 uv

        Args:
            progress: 进度回调

        Returns:
            uv 可执行文件路径

        Raises:
            RuntimeError: 下载或校验失败
        """
        uv = self.uv_path()
        if uv.exists():
            return uv

        if sys.platform == 'win32':
            asset = 'uv-x86_64-pc-windows-msvc.zip'
        elif sys.platform == 'darwin':
            asset = 'uv-aarch64-apple-darwin.tar.gz'
        else:
            asset = 'uv-x86_64-unknown-linux-gnu.tar.gz'

        base_url = f'https://github.com/astral-sh/uv/releases/download/{UV_VERSION}'
        progress('正在下载安装工具')
        uv.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(dir=self.runtime_dir()) as tmp:
            archive_path = Path(tmp) / asset
            with httpx.stream('GET', f'{base_url}/{asset}', follow_redirects=True, timeout=60.0) as response:
                response.raise_for_status()
                with archive_path.open('wb') as f:
                    for chunk in response.iter_bytes(1024 * 256):
                        f.write(chunk)

            checksum = httpx.get(f'{base_url}/{asset}.sha256', follow_redirects=True, timeout=30.0)
            checksum.raise_for_status()
            expected = checksum.text.split()[0].strip().lower()
            if hashlib.sha256(archive_path.read_bytes()).hexdigest() != expected:
                raise RuntimeError('安装工具校验失败，请检查网络后重试')

            if asset.endswith('.zip'):
                with zipfile.ZipFile(archive_path) as zf:
                    member = next(name for name in zf.namelist() if name.endswith('/uv.exe'))
                    zf.extract(member, tmp)
                    Path(tmp, member).replace(uv)
            else:
                with tarfile.open(archive_path) as tf:
                    member = next(m for m in tf.getmembers() if m.name.endswith('/uv') and m.isfile())
                    tf.extract(member, tmp, filter='data')
                    Path(tmp, member.name).replace(uv)

        if sys.platform != 'win32':
            uv.chmod(0o755)
        logger.info(f'uv 已就绪: {uv}')
        return uv

    def _run(self, args: list[str], env: dict[str, str]) -> None:
        """执行安装命令

        Args:
            args: 命令与参数
            env: 环境变量

        Raises:
            RuntimeError: 命令执行失败
        """
        logger.info(f'执行: {" ".join(args)}')
        result = subprocess.run(args, capture_output=True, text=True, env=env, creationflags=CREATE_NO_WINDOW)
        if result.returncode != 0:
            tail = (result.stderr or result.stdout).strip().splitlines()[-5:]
            raise RuntimeError('安装失败: ' + ' | '.join(tail))

    def _install_deps(
        self,
        uv: Path,
        backend: BackendInfo,
        env: dict[str, str],
        progress: Callable[[str], None],
    ) -> None:
        """安装 PyTorch 与 OmniVoice

        Args:
            uv: uv 可执行文件
            backend: 推理后端
            env: 环境变量
            progress: 进度回调
        """
        python = str(self.venv_python())
        progress(f'正在安装 {backend.description} 所需的 PyTorch')
        torch_args = [str(uv), 'pip', 'install', '--python', python, 'torch', 'torchaudio']
        if backend.torch_index_url:
            torch_args += ['--index-url', backend.torch_index_url]
        self._run(torch_args, env)

        progress('正在安装 OmniVoice')
        self._run([str(uv), 'pip', 'install', '--python', python, 'omnivoice'], env)
        logger.info(f'OmniVoice 运行时安装完成: {backend.description}')

    def _write_server_script(self) -> None:
        """把随应用分发的服务脚本写入运行时目录

        Raises:
            FileNotFoundError: 资源文件中缺少服务脚本
        """
        self.server_script().write_text(
            (get_resource_dir() / SERVER_SCRIPT_NAME).read_text(encoding='utf-8'),
            encoding='utf-8',
        )

    async def install(self, hf_endpoint: str, on_progress: Callable[[RuntimeProgress], None]) -> None:
        """安装运行时

        Args:
            hf_endpoint: HuggingFace 镜像地址
            on_progress: 进度回调

        Raises:
            RuntimeError: 没有受支持的后端或安装失败
        """
        loop = asyncio.get_running_loop()

        def notify(message: str) -> None:
            loop.call_soon_threadsafe(on_progress, RuntimeProgress(message=message))

        backend = self.backend()
        async with self.lock:
            self.runtime_dir().mkdir(parents=True, exist_ok=True)
            env = self._build_env(hf_endpoint)
            uv = await asyncio.to_thread(self._ensure_uv, notify)
            notify('正在创建 Python 环境')
            await asyncio.to_thread(
                self._run,
                [str(uv), 'venv', '--python', PYTHON_VERSION, str(self.venv_dir())],
                env,
            )
            await asyncio.to_thread(self._install_deps, uv, backend, env, notify)
            await asyncio.to_thread(self._write_server_script)
            await asyncio.to_thread(shutil.rmtree, self.runtime_dir() / 'uv-cache', ignore_errors=True)
            on_progress(RuntimeProgress(message='安装完成'))

    async def _healthy(self, port: int) -> bool:
        """检查服务是否就绪

        Args:
            port: 服务端口

        Returns:
            服务健康时返回 True
        """
        try:
            async with httpx.AsyncClient(timeout=2.0, trust_env=False) as client:
                response = await client.get(f'http://127.0.0.1:{port}/health')
        except httpx.HTTPError:
            return False
        if response.status_code != 200:
            return False
        return bool(response.json().get('ready'))

    async def _model_total_bytes(self, hf_endpoint: str) -> int:
        """查询模型仓库的总体积

        Args:
            hf_endpoint: HuggingFace 镜像地址

        Returns:
            总字节数，查询失败时返回 0
        """
        base = (hf_endpoint or 'https://huggingface.co').rstrip('/')
        url = f'{base}/api/models/{MODEL_ID}/tree/main?recursive=true'
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                response = await client.get(url)
            response.raise_for_status()
            entries = response.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.warning(f'获取模型体积失败: {e!r}')
            return 0
        return sum(int(entry.get('size') or 0) for entry in entries if entry.get('type') == 'file')

    def _download_progress(self, total: int) -> RuntimeProgress:
        """构造模型下载阶段的进度

        Args:
            total: 模型总字节数，0 表示未知

        Returns:
            进度对象
        """
        downloaded = self.cached_model_bytes()
        if total <= 0 or downloaded <= 0:
            return RuntimeProgress(message='正在准备模型')
        if downloaded >= total:
            return RuntimeProgress(message='正在加载模型')
        percent = downloaded * 100 // total
        return RuntimeProgress(
            message=f'正在下载模型 {downloaded / 1024**3:.1f} / {total / 1024**3:.1f} GB',
            percent=percent,
        )

    async def start(
        self,
        port: int,
        hf_endpoint: str,
        on_progress: Callable[[RuntimeProgress], None],
    ) -> None:
        """启动常驻合成服务

        Args:
            port: 服务端口
            hf_endpoint: HuggingFace 镜像地址
            on_progress: 进度回调

        Raises:
            RuntimeError: 未安装或启动失败
        """
        async with self.lock:
            if await self._healthy(port):
                return
            if not self.is_installed():
                raise RuntimeError('尚未安装本地运行时')

            self._write_server_script()
            backend = self.backend()
            model_total = await self._model_total_bytes(hf_endpoint)
            self._log_file = self.log_path().open('ab')
            self._process = subprocess.Popen(
                [
                    str(self.venv_python()),
                    str(self.server_script()),
                    '--port',
                    str(port),
                    '--model',
                    MODEL_ID,
                    '--device',
                    backend.device_map,
                    '--dtype',
                    backend.dtype,
                ],
                cwd=str(self.runtime_dir()),
                env=self._build_env(hf_endpoint),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW,
            )
            self._pump_thread = threading.Thread(
                target=self._pump_output,
                args=(self._process, self._log_file),
                daemon=True,
            )
            self._pump_thread.start()

            deadline = time.monotonic() + STARTUP_TIMEOUT
            while time.monotonic() < deadline:
                if self._process.poll() is not None:
                    raise RuntimeError(f'本地服务启动失败: {self._log_tail()}')
                if await self._healthy(port):
                    self.pid_path().write_text(str(self._process.pid), encoding='utf-8')
                    on_progress(RuntimeProgress(message='服务已就绪', percent=100))
                    logger.info(f'OmniVoice 服务已启动: 127.0.0.1:{port}')
                    return
                on_progress(self._download_progress(model_total))
                await asyncio.sleep(2)

            raise RuntimeError('本地服务启动超时')

    def _pump_output(self, process: subprocess.Popen[bytes], log_file: IO[bytes]) -> None:
        """把服务进程的输出同时写到日志文件与应用控制台

        Args:
            process: 服务进程
            log_file: 日志文件
        """
        assert process.stdout is not None
        for raw in iter(process.stdout.readline, b''):
            log_file.write(raw)
            log_file.flush()
            if sys.stdout is None:
                continue
            sys.stdout.write(raw.decode('utf-8', errors='replace'))
            sys.stdout.flush()
        log_file.close()

    def _log_tail(self, lines: int = 5) -> str:
        """读取服务日志末尾

        Args:
            lines: 行数

        Returns:
            日志尾部文本
        """
        if not self.log_path().exists():
            return '没有日志'
        tail = self.log_path().read_text(encoding='utf-8', errors='replace').strip().splitlines()
        return ' | '.join(tail[-lines:]) or '没有日志'

    def pid_path(self) -> Path:
        """服务进程号文件路径

        Returns:
            文件路径
        """
        return self.runtime_dir() / 'server.pid'

    def _read_pid(self) -> int | None:
        """读取服务进程号

        Returns:
            进程号，缺失或无效时返回 None
        """
        path = self.pid_path()
        if not path.exists():
            return None
        text = path.read_text(encoding='utf-8').strip()
        return int(text) if text.isdigit() else None

    def _terminate(self, pid: int) -> None:
        """终止指定进程

        Args:
            pid: 进程号
        """
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return
        logger.info(f'已终止 OmniVoice 服务进程: {pid}')

    async def stop(self, port: int) -> None:
        """停止常驻合成服务

        Args:
            port: 服务端口
        """
        process = self._process
        self._process = None
        pid = process.pid if process is not None and process.poll() is None else self._read_pid()
        self.pid_path().unlink(missing_ok=True)
        if pid is None or not await self._healthy(port):
            await self._close_output()
            return

        await asyncio.to_thread(self._terminate, pid)
        for _ in range(20):
            if not await self._healthy(port):
                logger.info('OmniVoice 服务已停止')
                break
            await asyncio.sleep(0.25)
        else:
            logger.warning('OmniVoice 服务未能停止，请手动结束进程')
        await self._close_output()

    async def _close_output(self) -> None:
        """等待输出转发线程结束并关闭日志文件"""
        if self._pump_thread is not None:
            await asyncio.to_thread(self._pump_thread.join, 5.0)
            self._pump_thread = None
        if self._log_file is not None:
            if not self._log_file.closed:
                self._log_file.close()
            self._log_file = None

    async def ensure_running(self, port: int, hf_endpoint: str) -> str:
        """确保服务在运行并返回服务地址

        Args:
            port: 服务端口
            hf_endpoint: HuggingFace 镜像地址

        Returns:
            服务地址

        Raises:
            RuntimeError: 未安装或启动失败
        """
        if not await self._healthy(port):
            await self.start(port, hf_endpoint, lambda _progress: None)
        return f'http://127.0.0.1:{port}'

    async def state(self, port: int) -> RuntimeState:
        """获取运行时状态

        Args:
            port: 服务端口

        Returns:
            运行时状态
        """
        if not self.is_installed():
            return RuntimeState(status=RuntimeStatus.NOT_INSTALLED, detail='需要先安装本地运行时')
        if await self._healthy(port):
            return RuntimeState(status=RuntimeStatus.RUNNING, detail=f'{self.backend().description} · 服务已就绪')
        return RuntimeState(status=RuntimeStatus.INSTALLED, detail='服务未启动')


omnivoice_runtime = OmniVoiceRuntime()
