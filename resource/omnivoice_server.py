"""OmniVoice 本地合成服务

由弹幕姬在 OmniVoice 运行时环境中启动：加载一次模型，对外提供 HTTP 合成接口。
仅依赖 OmniVoice 运行时自带的 numpy 与 torch。
"""

import argparse
import io
import json
import os
import threading
import time
import traceback
import wave

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import numpy as np
import torch

from omnivoice import OmniVoice

SAMPLE_RATE = 24000

_model: OmniVoice | None = None
_model_lock = threading.Lock()
_prompt_cache: dict[tuple[str, float, str], Any] = {}
_state: dict[str, object] = {'ready': False, 'device': '', 'model': '', 'dtype': ''}


def encode_wav(samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    """把浮点音频编码为 16 位 PCM WAV

    Args:
        samples: 单声道浮点采样，取值 -1.0 ~ 1.0
        sample_rate: 采样率

    Returns:
        WAV 字节数据
    """
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767).astype('<i2')
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(pcm.tobytes())
    return buffer.getvalue()


def load_model(model_id: str, device: str, dtype: str) -> None:
    """加载模型并更新服务状态

    Args:
        model_id: 模型仓库名
        device: 加载设备
        dtype: 精度
    """
    global _model
    torch_dtype = {'float16': torch.float16, 'float32': torch.float32}[dtype]
    print(f'[omnivoice] 加载模型 {model_id} 到 {device} ({dtype})', flush=True)
    _model = OmniVoice.from_pretrained(model_id, device_map=device, dtype=torch_dtype)
    _state.update({'ready': True, 'device': device, 'model': model_id, 'dtype': dtype})
    print('[omnivoice] 模型已就绪', flush=True)


def get_prompt(ref_audio: str, ref_text: str) -> Any:
    """获取并缓存参考音频的音色提示

    Args:
        ref_audio: 参考音频路径
        ref_text: 参考文本

    Returns:
        音色提示对象
    """
    key = (ref_audio, os.path.getmtime(ref_audio), ref_text)
    if key not in _prompt_cache:
        assert _model is not None
        _prompt_cache.clear()
        _prompt_cache[key] = _model.create_voice_clone_prompt(ref_audio=ref_audio, ref_text=ref_text or None)
    return _prompt_cache[key]


def synthesize(payload: dict[str, Any]) -> bytes:
    """执行一次合成

    Args:
        payload: 请求参数

    Returns:
        WAV 字节数据
    """
    assert _model is not None
    text = str(payload['text'])
    ref_audio = str(payload.get('ref_audio') or '')
    ref_text = str(payload.get('ref_text') or '')
    instruct = str(payload.get('instruct') or '')
    num_step = int(payload.get('num_step') or 32)
    speed = float(payload.get('speed') or 1.0)

    kwargs: dict[str, Any] = {'num_step': num_step, 'speed': speed}
    if instruct:
        kwargs['instruct'] = instruct
        voice = f'instruct={instruct!r}'
    elif ref_audio and os.path.exists(ref_audio):
        kwargs['voice_clone_prompt'] = get_prompt(ref_audio, ref_text)
        voice = f'voice_clone={ref_audio} ref_text={ref_text!r}'
    else:
        voice = '模型默认音色'
        if ref_audio:
            print(f'[omnivoice] 参考音频不存在，改用默认音色: {ref_audio}', flush=True)

    print(
        f'[omnivoice] 合成请求: text={text!r} num_step={num_step} speed={speed} 音色={voice}',
        flush=True,
    )
    started = time.monotonic()
    audio = _model.generate(text=text, **kwargs)
    print(f'[omnivoice] 合成完成，耗时 {time.monotonic() - started:.2f}s', flush=True)
    return encode_wav(audio[0])


class Handler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    def log_message(self, *_args: object) -> None:
        """关闭默认访问日志"""

    def _json(self, status: int, data: dict[str, Any]) -> None:
        """返回 JSON 响应

        Args:
            status: HTTP 状态码
            data: 响应数据
        """
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        """健康检查"""
        if self.path != '/health':
            self._json(404, {'error': 'not found'})
            return
        self._json(200, dict(_state))

    def do_POST(self) -> None:
        """合成接口"""
        if self.path != '/tts':
            self._json(404, {'error': 'not found'})
            return

        length = int(self.headers.get('Content-Length') or 0)
        payload = json.loads(self.rfile.read(length) or b'{}')
        try:
            with _model_lock:
                audio = synthesize(payload)
        except Exception as e:
            traceback.print_exc()
            self._json(500, {'error': f'{type(e).__name__}: {e}'})
            return

        self.send_response(200)
        self.send_header('Content-Type', 'audio/wav')
        self.send_header('Content-Length', str(len(audio)))
        self.end_headers()
        self.wfile.write(audio)


def main() -> None:
    """启动服务"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--model', default='k2-fsa/OmniVoice')
    parser.add_argument('--device', default='cuda:0')
    parser.add_argument('--dtype', default='float16')
    args = parser.parse_args()

    load_model(args.model, args.device, args.dtype)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'[omnivoice] 服务已启动: 127.0.0.1:{args.port}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
