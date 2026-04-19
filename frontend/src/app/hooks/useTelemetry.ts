import { useState, useEffect, useRef } from "react";

export interface TelemetryEvent {
  session_id: string;
  event: string;
  seq: number;
  ts: number;
  size_bytes: number | null;
  checksum: string | null;
  attempt: number | null;
  rtt_ms: number | null;
}

export type PacketStatus = "sent" | "lost" | "acked";

export interface Metrics {
  totalBytesAcked: number;
  packetsLost: number;
  retransmits: number;
}

export function useTelemetry(
  sessionId: string | null,
  maxEvents: number = 100,
) {
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [packetState, setPacketState] = useState<Record<number, PacketStatus>>(
    {},
  );
  const [metrics, setMetrics] = useState<Metrics>({
    totalBytesAcked: 0,
    packetsLost: 0,
    retransmits: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    // Reset board for a new transfer
    setEvents([]);
    setPacketState({});
    setMetrics({ totalBytesAcked: 0, packetsLost: 0, retransmits: 0 });

    // Connect using the specific session_id room
    const wsUrl = `ws://localhost:8000/api/ws?session_id=${sessionId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);

    ws.onmessage = (message) => {
      try {
        const data: TelemetryEvent = JSON.parse(message.data);

        setEvents((prev) => [data, ...prev].slice(0, maxEvents));

        setMetrics((prev) => {
          const newMetrics = { ...prev };

          if (
            data.seq === 0 &&
            data.event === "packet_sent" &&
            data.attempt === 1
          ) {
            return { totalBytesAcked: 0, packetsLost: 0, retransmits: 0 };
          }

          if (data.event === "ack_received" && data.size_bytes) {
            newMetrics.totalBytesAcked += data.size_bytes;
          }

          if (data.event === "retransmit") {
            newMetrics.packetsLost += 1;
            newMetrics.retransmits += 1;
          }

          if (data.event === "packet_timeout") {
            newMetrics.packetsLost += 1;
          }

          return newMetrics;
        });

        setPacketState((prev) => {
          const newState = { ...prev };
          if (
            data.seq === 0 &&
            data.event === "packet_sent" &&
            data.attempt === 1
          ) {
            return { 0: "sent" };
          }
          if (data.seq === -1) return prev;

          if (data.event === "ack_received") newState[data.seq] = "acked";
          else if (
            data.event === "packet_timeout" ||
            data.event === "retransmit"
          )
            newState[data.seq] = "lost";
          else if (
            data.event === "packet_sent" &&
            newState[data.seq] !== "acked"
          )
            newState[data.seq] = "sent";

          return newState;
        });
      } catch (err) {
        console.error("Parse error:", err);
      }
    };

    return () => ws.close();
  }, [sessionId, maxEvents]);

  return { events, isConnected, packetState, metrics };
}
