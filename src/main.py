import asyncio
import logging

from config import gConfig
from custom_typing import Client, DanmakuMessage, GiftMessage, SuperChatMessage, GuardBuyMessage
from danmaku_client import run_client
from event_handler import gEventHandler
from gradio_client import predict

logger = logging.getLogger("kinoko7danmaku")

if gConfig.debug:
    logger.setLevel(logging.DEBUG)
else:
    bilidm_logger = logging.getLogger("blivedm")
    bilidm_logger.setLevel(logging.ERROR)


@gEventHandler.on_client_init
async def _(_: Client):
    if gConfig.room_id != 0:
        logger.info(f"当前房间号为 {gConfig.room_id}")
    await predict("弹幕姬！启动！")


@gEventHandler.on_gift
async def _(_: Client, message: GiftMessage):
    is_paid = message.coin_type == "gold"
    gift_num = message.num
    if not is_paid:
        return
    total_coin = message.price * gift_num
    if total_coin < gConfig.gift_threshold * 1000:
        return
    msg = f"非常感谢 {message.uname} 赠送的 {gift_num}个{message.gift_name}!"
    logger.info(msg)
    await predict(msg)


@gEventHandler.on_guard_buy
async def _(_: Client, message: GuardBuyMessage):
    if not gConfig.guard_buy_on:
        return
    msg = f"非常感谢 {message.username} 赠送的 一个{message.gift_name}!"
    logger.info(msg)
    await predict(msg)


@gEventHandler.on_super_chat
async def _(_: Client, message: SuperChatMessage):
    if not gConfig.super_chat_on:
        return
    msg = f"{message.uname}发送了一条醒目留言 说 {message.message}"
    logger.info(msg)
    await predict(msg)


@gEventHandler.on_danmaku
async def _(_: Client, message: DanmakuMessage):
    if not gConfig.normal_danmaku_on:
        return
    msg = f"{message.uname}说 {message.msg}"
    logger.info(msg)
    await predict(msg)


async def main():
    await run_client()


if __name__ == '__main__':
    asyncio.run(main())
