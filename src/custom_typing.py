from typing import Union

import blivedm.blivedm as blivedm
import blivedm.blivedm.models.web as web_models

Client = blivedm.BLiveClient
DanmakuMessage = web_models.DanmakuMessage
GiftMessage = web_models.GiftMessage
GuardBuyMessage = web_models.GuardBuyMessage
SuperChatMessage = web_models.SuperChatMessage
Message = Union[DanmakuMessage, GiftMessage, GuardBuyMessage, SuperChatMessage]
