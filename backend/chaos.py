import threading
from dataclasses import dataclass

@dataclass
class ChaosState:
    drop_rate: int = 0  # Percentage of packets to drop (0-100)
    delay_ms: int = 0   # Artificial latency to add (not implemented yet, but good to have)

class ChaosController:
    def __init__(self):
        self._lock = threading.Lock()
        self._state = ChaosState()

    def get_drop_rate(self) -> int:
        with self._lock:
            return self._state.drop_rate

    def set_drop_rate(self, rate: int):
        with self._lock:
            # Clamp between 0 and 100
            self._state.drop_rate = max(0, min(100, rate))

# Our global singleton, just like the telemetry queue
chaos_config = ChaosController()