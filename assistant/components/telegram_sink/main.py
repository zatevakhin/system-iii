import asyncio
import threading
from typing import List
import pathlib

from assistant.core.component import Component
from .events import (
    TELEGRAM_MESSAGE_RECEIVED,
    TELEGRAM_CHAT_HISTORY_DOWNLOAD_REQUEST,
    TELEGRAM_CHAT_HISTORY_DOWNLOAD_FINISHED,
)

# FIXME: how do we add new python dependencies to the nix-shell?
import telethon

# import types # NOTE: (Architecture) in system-iii, we have high potential for namespace clashes.
#  For example, `types.py` module conflicts with `types` module from Python standard library and crashes telethon library.


_SESSIONS_CACHE_DIR = pathlib.Path(__file__).parent / "sessions_cache"


class TelegramSink(Component):
    @property
    def version(self) -> str:
        # NOTE: easy to forget to update this value
        return "0.0.1"

    @property
    def events(self) -> List[str]:
        # NOTE: (Architecture) can automatically generate this list from the events module. But should we?
        return [
            TELEGRAM_MESSAGE_RECEIVED,
            TELEGRAM_CHAT_HISTORY_DOWNLOAD_REQUEST,
            TELEGRAM_CHAT_HISTORY_DOWNLOAD_FINISHED,
        ]

    def initialize(self) -> None:
        # NOTE: (Architecture) No protection against forgetting to call super().initialize()
        # NOTE: (Architecture) No protection from calling any method before initialization is complete
        # NOTE: (Architecture) It's better to initialize variables in the constructor?
        super().initialize()

        self.logger.setLevel(self.get_config("log_level", "DEBUG"))
        self._monitor_telegram_chat = self.get_config("monitor_telegram_chat", False)
        # NOTE: in this implementation, we only monitor one chat.
        #  Currently this component mainly needed to monitor "Saved Messages" chat in Telegram.
        #  Might change in the future.
        self._chat_name = self.get_config("telegram_chat_name", "me")
        self._session_name = self.get_config("telegram_session_name", None)

        # App credentials
        self._api_id = self.get_config("telegram_api_id", None)
        self._api_hash = self.get_config("telegram_api_hash", None)

        self._session_path = pathlib.Path(_SESSIONS_CACHE_DIR / self._session_name).resolve()
        self.logger.info(f"Session path: {self._session_path}")

        # FIXME: This shit doesn't work. When we have 2 clients simultaneously with the same session,
        #  they both start using the same session file and we get errors.
        # if self._monitor_telegram_chat:
        #     # NOTE: Should I init asyncio loop here or in main_sinks.py? TelegramClient won't work properly without it.
        #     self._monitoring_client = telethon.TelegramClient(session=self._session_path, api_id=self._api_id, api_hash=self._api_hash)
        #     self._monitoring_client.start()    
        #     self._monitoring_client.add_event_handler(self._on_message, telethon.events.NewMessage)

        # NOTE: Messy locgic
        self._download_messages_thread = None
        self._stop_download = threading.Event()

        self.logger.info(f"Plugin '{self.name}' initialized and ready")

    async def _on_message(self, event: telethon.events.NewMessage):
        if event.message.peer_id.user_id == self._chat_name:
            self.logger.debug(f"Received message: {event.message.message}")
            self.proxy(TELEGRAM_MESSAGE_RECEIVED)(event.message)

    def shutdown(self) -> None:
        # NOTE: (Architecture)In current implementation, if the component crashes, it will crash the whole application and won't be shutdown gracefully.
        super().shutdown()

        if self._download_messages_thread and self._download_messages_thread.is_alive():
            self._stop_download.set()  # Signal thread to stop
            self._download_messages_thread.join(timeout=5.0)  # Wait up to 5 seconds
            if self._download_messages_thread.is_alive():
                self.logger.warning("Download thread did not stop gracefully")

        # if self._monitor_telegram_chat:
        #     self._monitoring_client.remove_event_handler(self._on_message)
        #     self._monitoring_client.disconnect()

        self.logger.info(f"Plugin '{self.name}' shutdown done.")

    # NOTE: (Architecture) If not careful, such callbacks can block the main thread.
    def on_telegram_chat_history_download_request(self, limit: int):
        self.logger.info(f"Downloading chat history for {self._chat_name} with limit {limit}")

        # TODO: Figure out if we need to use here @service decorator or maybe an `observe` mechanism?
        async def download(client: telethon.TelegramClient):
            messages = []            
            async for message in client.iter_messages(self._chat_name, limit=limit):
                messages.append(message)
                if self._stop_download.is_set():
                    self.logger.info("Download stopped by request")
                    break
            self._on_telegram_chat_history_download_finished(messages)

        def run_download():
            # Initialize event loop for this thread... NOTE: Is this legal code?
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            with telethon.TelegramClient(session=self._session_path, api_id=self._api_id, api_hash=self._api_hash) as client:
                client.loop.run_until_complete(download(client))



        # Reset stop event before starting new download
        self._stop_download.clear()
        self._download_messages_thread = threading.Thread(target=run_download)
        self._download_messages_thread.start()

    def _on_telegram_chat_history_download_finished(self, messages: List[telethon.types.Message]):
        self.logger.info(f"Downloaded {len(messages)} messages")
        self.logger.debug(f"Messages: {messages}")

        # NOTE: (Architecture) any subscriber can corrupt the messages list.
        self.proxy(TELEGRAM_CHAT_HISTORY_DOWNLOAD_FINISHED)(messages)
