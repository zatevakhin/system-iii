from datetime import datetime
import io
from queue import Queue
from typing import List, Optional

import requests
import soundfile as sf

from assistant.core import service
from assistant.core.component import Component
from assistant.components.mumble.mumble import SpeechSegment
from assistant.core.config_manager import ConfigManager
from assistant.utils.utils import observe
from .events import (
    TELEGRAM_MESSAGE_RECEIVED,
    TELEGRAM_CHAT_HISTORY_DOWNLOAD_REQUEST,
    TELEGRAM_CHAT_HISTORY_DOWNLOAD_FINISHED,
)

# FIXME: how do we add new python dependencies to the nix-shell?
import telethon

# import types # NOTE: in system-iii, we have high potential for namespace clashes.
#  For example, `types.py` module conflicts with `types` module from Python standard library and crashes telethon library.


class TelegramSink(Component):
    @property
    def version(self) -> str:
        # NOTE: easy to forget to update this value
        return "0.0.1"

    @property
    def events(self) -> List[str]:
        # NOTE: can automatically generate this list from the events module. But should we?
        return [
            TELEGRAM_MESSAGE_RECEIVED,
            TELEGRAM_CHAT_HISTORY_DOWNLOAD_REQUEST,
            TELEGRAM_CHAT_HISTORY_DOWNLOAD_FINISHED,
        ]

    def initialize(self) -> None:
        # NOTE: No protection against forgetting to call super().initialize()
        # NOTE: No protection from calling any method before initialization is complete
        # NOTE: It's better to initialize variables in the constructor?
        super().initialize()

        self.logger.setLevel(self.get_config("log_level", "DEBUG"))
        self._monitor_telegram_chat = self.get_config("monitor_telegram_chat", False)
        # NOTE: in this implementation, we only monitor one chat. 
        #  Currently this component mainly needed to monitor "Saved Messages" chat in Telegram.
        #  Might change in the future.
        self._chat_name = self.get_config("telegram_chat_name", "me")
        self._session_name = self.get_config("telegram_session_name", None)
        # NOTE: Should we save such secrets in the config.yaml? 
        self._api_id = self.get_config("telegram_api_id", None)
        self._api_hash = self.get_config("telegram_api_hash", None)

        self._client = telethon.TelegramClient(self._session_name, self._api_id, self._api_hash)

        self._client.start()
        if self._monitor_telegram_chat:
            self._client.add_event_handler(self._on_message, telethon.events.NewMessage)

        # TODO: check, maybe I can use this mechanism to make an async history download of messages
        # self.speech_segments = Queue()
        # self.speech_segments_observer = observe(self.speech_segments, self.transcribe_segment, threaded=True, max_workers=4)

        self.logger.info(f"Plugin '{self.name}' initialized and ready")


    async def _on_message(self, event: telethon.events.NewMessage):
        if event.message.peer_id.user_id == self._chat_name:
            self.logger.debug(f"Received message: {event.message.message}")
            self.proxy(TELEGRAM_MESSAGE_RECEIVED)(event.message)

    def shutdown(self) -> None:
        # NOTE: In current implementation, if the component crashes, it will crash the whole application and won't be shutdown gracefully.
        super().shutdown()
        
        # self._client.remove_event_handler(self._on_message)
        self._client.disconnect()

        self.logger.info(f"Plugin '{self.name}' shutdown done.")

    # FIXME: Most likely this method won't work like this. Not sure that we can create async callbacks.
    @service
    async def on_telegram_chat_history_download_request(self, limit: int):
        self.logger.info(f"Downloading chat history for {self._chat_name} with limit {limit}")

        messages = await self._client.get_messages(self._chat_name, limit=limit)
        self.proxy(TELEGRAM_CHAT_HISTORY_DOWNLOAD_FINISHED)(messages)
