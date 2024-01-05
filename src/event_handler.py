from typing import List, Callable, Coroutine

from blivedm.blivedm.models.open_live import DanmakuMessage
from blivedm.blivedm.models.web import DanmakuMessage
from custom_typing import Client, DanmakuMessage, GiftMessage, GuardBuyMessage, SuperChatMessage


class EventHandler:
    def __init__(self):
        self._client_init_handlers: List[Callable[[Client], Coroutine]] = []
        self._danmaku_handlers: List[Callable[[Client, DanmakuMessage], Coroutine]] = []
        self._gift_handlers: List[Callable[[Client, GiftMessage], Coroutine]] = []
        self._guard_buy_handlers: List[Callable[[Client, GuardBuyMessage], Coroutine]] = []
        self._super_chat_handlers: List[Callable[[Client, SuperChatMessage], Coroutine]] = []

    def on_client_init(self, func: Callable[[Client], Coroutine]) -> Callable[[Client], Coroutine]:
        self._client_init_handlers.append(func)
        return func

    async def trigger_client_init(self, client: Client):
        for handler in self._client_init_handlers:
            await handler(client)

    def on_danmaku(self, func: Callable[[Client, DanmakuMessage], Coroutine]) -> Callable[
        [Client, DanmakuMessage], Coroutine]:
        self._danmaku_handlers.append(func)
        return func

    async def trigger_danmaku(self, client: Client, message: DanmakuMessage):
        for handler in self._danmaku_handlers:
            await handler(client, message)

    def on_gift(self, func: Callable[[Client, GiftMessage], Coroutine]) -> Callable[
        [Client, GiftMessage], Coroutine]:
        self._gift_handlers.append(func)
        return func

    async def trigger_gift(self, client: Client, message: GiftMessage):
        for handler in self._gift_handlers:
            await handler(client, message)

    def on_guard_buy(self, func: Callable[[Client, GuardBuyMessage], Coroutine]) -> Callable[
        [Client, GuardBuyMessage], Coroutine]:
        self._guard_buy_handlers.append(func)
        return func

    async def trigger_guard_buy(self, client: Client, message: GuardBuyMessage):
        for handler in self._guard_buy_handlers:
            await handler(client, message)

    def on_super_chat(self, func: Callable[[Client, SuperChatMessage], Coroutine]) -> Callable[
        [Client, SuperChatMessage], Coroutine]:
        self._super_chat_handlers.append(func)
        return func

    async def trigger_super_chat(self, client: Client, message: SuperChatMessage):
        for handler in self._super_chat_handlers:
            await handler(client, message)


if "gEventHandler" not in globals():
    gEventHandler = EventHandler()
