from collections import deque

from fastapi import WebSocket

from src.models import ChannelConfig, DebugEntry, Platform
from src.settings import settings


class ChannelState:
    def __init__(self, platform: Platform):
        self.platform = platform
        self.config = ChannelConfig()
        self.websocket: WebSocket | None = None
        self.debug: deque[DebugEntry] = deque(maxlen=settings.max_debug_entries)

    @property
    def connected(self) -> bool:
        return self.websocket is not None

    def add_debug(self, entry: DebugEntry) -> None:
        self.debug.appendleft(entry)


class AppState:
    def __init__(self):
        self.channels: dict[Platform, ChannelState] = {
            Platform.WHATSAPP: ChannelState(Platform.WHATSAPP),
            Platform.INSTAGRAM: ChannelState(Platform.INSTAGRAM),
        }

    def get(self, platform: Platform) -> ChannelState:
        return self.channels[platform]


app_state = AppState()
