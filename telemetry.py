from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
import json


class EventType(str, Enum):
    SESSION_STARTED   = "session_started"
    PACKET_SENT       = "packet_sent"
    ACK_RECEIVED      = "ack_received"
    PACKET_TIMEOUT    = "packet_timeout"
    RETRANSMIT        = "retransmit"
    TRANSFER_COMPLETE = "transfer_complete"
    ERROR             = "error"


@dataclass
class TelemetryEvent:
    session_id: str
    event:      EventType
    seq:        int          = -1
    ts:         float        = field(default_factory=time.time)
    size_bytes: Optional[int]   = None
    checksum:   Optional[str]   = None
    attempt:    Optional[int]   = None
    rtt_ms:     Optional[float] = None

    def to_json(self) -> str:
        d = asdict(self)
        d["event"] = self.event.value
        if isinstance(d["checksum"], bytes):
            d["checksum"] = d["checksum"].hex()
        return json.dumps(d)