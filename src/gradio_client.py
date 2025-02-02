import logging
import base64

import aiohttp

from audio_player import gAudioPlayer
from config import gConfig
from format import pre_format

logger = logging.getLogger("kinoko7danmaku")


async def predict(text: str):
    url = gConfig.api_url
    text = pre_format(text)
    if gConfig.api_mode == "gpt-sovits":
        predict_url = f"{url}synthesize"
        data = {
            "target_text": text,
            "target_speed": gConfig.target_speed
        }
    else:
        predict_url = f"{url}run/predict"
        data = {
            "data": [
                text,
                gConfig.voice_name,
                0.5,
                0.6,
                0.9,
                1,
                "auto",
                None,
                "Happy",
                "Text prompt",
                "",
                0.7
            ],
            "event_data": None,
            "fn_index": 0
        }
    async with aiohttp.ClientSession() as s:
        async with s.post(predict_url, json=data) as resp:
            if resp.status != 200:
                logger.error(f"请求失败，状态码：{resp.status} text: {text}")
                return
            if gConfig.api_mode == "gpt-sovits":
                audio_bytes = await resp.read()
                b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                wav_url = f"data:audio/wav;base64,{b64_audio}"
            else:
                ret = await resp.json()
                if "data" not in ret:
                    logger.error(f"返回数据格式错误，text:{text} ret: {ret}")
                    return
                wav_url = f'{url}file={ret["data"][1]["name"]}'
            await gAudioPlayer.play_online_wav(wav_url)
