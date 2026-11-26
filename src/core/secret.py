"""配置文件敏感字段的本地加密

用机器相关的派生密钥做 AES-GCM：config.json 单独泄露或被上传时不含明文密钥。
密文换到别的机器上解不开，按空值处理，用户重新填写即可。
"""

import base64
import hashlib
import os
import platform
import subprocess
import uuid

from functools import lru_cache

from Cryptodome.Cipher import AES
from loguru import logger

PREFIX = 'enc:v1:'
_SALT = b'k7d-config-v1'
_NONCE_SIZE = 12
_TAG_SIZE = 16


@lru_cache(maxsize=1)
def _machine_id() -> str:
    """读取本机标识，用于派生密钥

    Returns:
        机器唯一标识；取不到时退回主机名 + MAC
    """
    try:
        system = platform.system()
        if system == 'Windows':
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography') as key:
                return str(winreg.QueryValueEx(key, 'MachineGuid')[0])
        if system == 'Darwin':
            output = subprocess.run(
                ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                capture_output=True,
                text=True,
            ).stdout
            for line in output.splitlines():
                if 'IOPlatformUUID' in line:
                    return line.split('"')[3]
    except OSError as e:
        logger.warning(f'读取本机标识失败，使用主机名代替: {e!r}')
    return f'{platform.node()}-{uuid.getnode():x}'


@lru_cache(maxsize=1)
def _key() -> bytes:
    """用机器标识派生 32 字节密钥"""
    return hashlib.blake2b(_machine_id().encode(), salt=_SALT, digest_size=32).digest()


def is_encrypted(value: str) -> bool:
    """判断字符串是否为加密后的值

    Args:
        value: 配置值

    Returns:
        是否带加密前缀
    """
    return value.startswith(PREFIX)


def encrypt(value: str) -> str:
    """加密配置值

    Args:
        value: 明文

    Returns:
        带前缀的密文
    """
    nonce = os.urandom(_NONCE_SIZE)
    cipher = AES.new(_key(), AES.MODE_GCM, nonce=nonce)
    payload, tag = cipher.encrypt_and_digest(value.encode())
    return PREFIX + base64.b64encode(nonce + tag + payload).decode()


def decrypt(value: str) -> str:
    """解密配置值

    Args:
        value: 带前缀的密文；未加密时原样返回

    Returns:
        明文；解密失败时返回空串
    """
    if not is_encrypted(value):
        return value
    try:
        raw = base64.b64decode(value[len(PREFIX) :])
        nonce = raw[:_NONCE_SIZE]
        tag = raw[_NONCE_SIZE : _NONCE_SIZE + _TAG_SIZE]
        payload = raw[_NONCE_SIZE + _TAG_SIZE :]
        return AES.new(_key(), AES.MODE_GCM, nonce=nonce).decrypt_and_verify(payload, tag).decode()
    except ValueError as e:
        logger.warning(f'敏感配置解密失败，按空值处理: {e!r}')
        return ''
