import asyncio

from bilibili import bili_service
from config import setting
from player import get_stream_player
from tts_service import get_tts_service


async def main():
    if setting.bili_service.welcome_on:
        tts_service = get_tts_service()
        audio = await tts_service.text_to_speech("弹幕姬启动！")
        player = get_stream_player()
        player.play_bytes(audio)
    await bili_service.run()
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
