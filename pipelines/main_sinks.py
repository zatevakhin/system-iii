import asyncio
from time import sleep

import logging

from rich.logging import RichHandler

from assistant.core import EventBus
from assistant.components.telegram_sink import events as tl
from assistant.components.telegram_sink.main import TelegramSink
from assistant.core.config_manager import ConfigManager

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - [yellow]%(threadName)-10s[/] - %(message)s",
    handlers=[RichHandler(show_time=False, markup=True)],
)


def main():
    event_bus = EventBus()
    config = ConfigManager()

    telegram = TelegramSink(config=config)

    event_bus.register(telegram)

    telegram.on(tl.TELEGRAM_CHAT_HISTORY_DOWNLOAD_REQUEST, telegram.on_telegram_chat_history_download_request)

    telegram.initialize()

    # # NOTE: (Architecture) it seems that this method is not working.
    # #  I've added those lines only for testing purposes.
    # test_params = {"limit": 5}
    # event_bus.publish(tl.TELEGRAM_CHAT_HISTORY_DOWNLOAD_REQUEST, test_params)

    telegram.on_telegram_chat_history_download_request(5)

    while True:
        try:
            sleep(1)
        except KeyboardInterrupt:
            print(end="\r")
            break

    telegram.shutdown()


if "__main__" == __name__:
    main()
