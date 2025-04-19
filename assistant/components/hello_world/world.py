from typing import List
import sched
import time

from assistant.core.component import Component

from . import events

class World(Component):
    @property
    def version(self) -> str:
        # NOTE: easy to forget to update this value
        return "0.0.1"

    @property
    def events(self) -> List[str]:
        # NOTE: can automatically generate this list from the events module
        return []

    def initialize(self) -> None:
        # NOTE: No protection against forgetting to call super().initialize()
        # NOTE: No protection from calling any method before initialization is complete
        # NOTE: It's better to initialize variables in the constructor?
        super().initialize()
        self.logger.setLevel(self.get_config("log_level", "DEBUG"))

        self.logger.info(f"Plugin '{self.name}' initialized and ready")

    def on_hello_event(self) -> None:
        self.logger.info("WORLD!")

    def shutdown(self) -> None:
        super().shutdown()
        self.logger.info(f"Plugin '{self.name}' disconnection from server.")
