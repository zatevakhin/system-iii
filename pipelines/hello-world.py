from time import sleep
from assistant.core import EventBus

from assistant.components.hello_world import events as hw

from assistant.components.hello_world.hello import Hello
from assistant.components.hello_world.world import World

import logging

from rich.logging import RichHandler
from assistant.core.config_manager import ConfigManager

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - [yellow]%(threadName)-10s[/] - %(message)s",
    handlers=[RichHandler(show_time=False, markup=True)],
)


def main():
    event_bus = EventBus()
    config = ConfigManager()


    hello = Hello(name="hello", config=config)
    world = World(name="world", config=config)

    event_bus.register(hello)
    event_bus.register(world)

    hello.on(hw.HELLO_WORLD_EVENT, world.on_hello_event)

    hello.initialize()
    world.initialize()

    while True:
        try:
            sleep(1)
        except KeyboardInterrupt:
            print(end="\r")
            break

    hello.shutdown()
    world.shutdown()


if "__main__" == __name__:
    main()
