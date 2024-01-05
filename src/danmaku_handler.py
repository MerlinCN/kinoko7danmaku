import asyncio

import blivedm.blivedm as blivedm
import blivedm.blivedm.models.web as web_models
from event_handler import gEventHandler


class BliveHandler(blivedm.BaseHandler):
    def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        asyncio.create_task(gEventHandler.trigger_danmaku(client, message))

    def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        asyncio.create_task(gEventHandler.trigger_gift(client, message))

    def _on_buy_guard(self, client: blivedm.BLiveClient, message: web_models.GuardBuyMessage):
        asyncio.create_task(gEventHandler.trigger_guard_buy(client, message))

    def _on_super_chat(self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage):
        asyncio.create_task(gEventHandler.trigger_super_chat(client, message))
