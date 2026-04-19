import threading
from dataclasses import dataclass

@dataclass
class ChaosState:
    drop_rate: int = 0  # Percentage of packets to drop (0-100)
    #delay_ms: int = 0 

class ChaosController:
    def __init__(self):
        self._lock = threading.Lock()
        self._state = ChaosState()

    def get_drop_rate(self) -> int:
        with self._lock:
            return self._state.drop_rate

    def set_drop_rate(self, rate: int):
        with self._lock:
            self._state.drop_rate = max(0, min(100, rate))

chaos_config = ChaosController()