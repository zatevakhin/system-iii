from typing import List
import threading

from assistant.core.component import Component

from . import events

class Hello(Component):
    @property
    def version(self) -> str:
        # NOTE: easy to forget to update this value
        return "0.0.1"

    @property
    def events(self) -> List[str]:
        # NOTE: can automatically generate this list from the events module. Should we?
        return [
            events.HELLO_WORLD_EVENT,
        ]

    def initialize(self) -> None:
        # NOTE: No protection against forgetting to call super().initialize()
        # NOTE: No protection from calling any method before initialization is complete
        # NOTE: It's better to initialize variables in the constructor?
        super().initialize()
        self.logger.setLevel(self.get_config("log_level", "DEBUG"))

        # Schedule the event using Timer
        TIME_TO_WAIT_SEC = 10
        self._timer = threading.Timer(TIME_TO_WAIT_SEC, self._hello_event)
        self._timer.start()
        
        self.logger.info(f"Plugin '{self.name}' initialized and ready")

    def _hello_event(self) -> None:
        self.logger.info("HELLO, ")
        self.proxy(events.HELLO_WORLD_EVENT)()

    def shutdown(self) -> None:
        super().shutdown()
        self.logger.info(f"Plugin '{self.name}' disconnection from server.")
