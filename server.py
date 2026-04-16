import socket
import threading
import queue
import os
from protocol import *
import uuid
from telemetry import TelemetryEvent, EventType
from event_queue import telemetry_queue
import random
from chaos import chaos_config

# --- Configuration ---
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000
BUFFER_SIZE = 4096  # Larger than 1024 to accommodate headers
MAX_RETRIES = 10    # Safety valve for zombie threads

# Global dictionary to route ACKs to the correct thread
# Format: { (ip, port): queue.Queue() }
active_transfers = {}
dict_lock = threading.Lock()

chaos_config.set_drop_rate(10)

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((SERVER_IP, SERVER_PORT))

def stdout_telemetry_consumer():
    """Phase 1 test consumer: Drains the queue and prints to stdout"""
    print("[*] Telemetry stdout consumer started.")
    while True:
        event = telemetry_queue.get()
        # Using the awesome to_json() method you wrote!
        print(f"TELEMETRY: {event.to_json()}") 
        telemetry_queue.task_done()

def handle_file_transfer(filename, client_address, packet_queue):

    """Worker thread: Handles one specific file transfer."""
    print(f"[*] Thread started for {client_address} (File: {filename})")

    session_id = str(uuid.uuid4())
    telemetry_queue.put(TelemetryEvent(session_id = session_id, event = EventType.SESSION_STARTED))
    
    if not os.path.exists(filename):
        error_pkt = pack_p(TYPE_ERROR, 0, calculate_md5(b""), b"File not found")
        server_socket.sendto(error_pkt, client_address)
        return

    try:
        with open(filename, "rb") as f:
            current_sequence = 0
            while True:
                chunk = f.read(1024)
                is_eof = not chunk
                
                # Create the packet
                data_packet = pack_p(TYPE_DATA, current_sequence, calculate_md5(chunk), chunk)
                
                # --- STOP-AND-WAIT RETRANSMISSION LOOP ---
                retries = 0
                while True:

                    current_drop_rate = chaos_config.get_drop_rate()
                    if current_drop_rate > 0 and random.randint(1, 100) <= current_drop_rate:
                        print(f"[!] CHAOS: Dropping packet {current_sequence} intentionally.")
                        # We don't send to the socket, but we STILL emit the telemetry 
                        # so the UI knows we *tried* to send it (and it got lost in the void).
                    else:
                        # The normal path
                        server_socket.sendto(data_packet, client_address)

                    telemetry_queue.put(TelemetryEvent(
                                        session_id = session_id,
                                        event = EventType.PACKET_SENT,
                                        seq = current_sequence,
                                        size_bytes = len(chunk),
                                        checksum = calculate_md5(chunk),
                                        attempt = retries + 1 ))
                    
                    try:
                        # Wait for the ACK from the Main Thread's dispatcher
                        ack_buffer = packet_queue.get(timeout=1.0)
                        p_type, ack_seq, _, _ = unpack_p(ack_buffer)
                        
                        if p_type == TYPE_ACK and ack_seq == current_sequence:
                            telemetry_queue.put(TelemetryEvent(
                                                session_id = session_id,
                                                event = EventType.ACK_RECEIVED,
                                                seq = current_sequence,
                                                size_bytes = len(chunk),
                                                checksum = calculate_md5(chunk),
                                                attempt = retries + 1 ))
                            current_sequence += 1
                            break # Success! Move to next chunk
                        else:
                            print(f"[?] Unexpected ACK {ack_seq} for {client_address}")
                    
                    except queue.Empty:
                        retries += 1
                        if retries > MAX_RETRIES:
                            telemetry_queue.put(TelemetryEvent(
                                                session_id = session_id,
                                                event = EventType.PACKET_TIMEOUT,
                                                seq = current_sequence,
                                                size_bytes = len(chunk),
                                                checksum = calculate_md5(chunk),
                                                attempt = retries + 1 ))
                            print(f"[-] ERROR: {client_address} timed out too many times. Aborting.")
                            return

                        telemetry_queue.put(TelemetryEvent(
                                            session_id = session_id,
                                            event = EventType.RETRANSMIT,
                                            seq = current_sequence,
                                            size_bytes = len(chunk),
                                            checksum = calculate_md5(chunk),
                                            attempt = retries + 1 ))
                        print(f"[!] Timeout for {client_address}, seq {current_sequence}. Resending...")

                if is_eof:
                    break
        
        telemetry_queue.put(TelemetryEvent(
                            session_id = session_id,
                            event = EventType.TRANSFER_COMPLETE,
        ))
        print(f"[+] Transfer to {client_address} complete.")

    except Exception as e:
        print(f"[-] Error handling {client_address}: {e}")
    
    finally:

        # Cleanup dictionary so we don't leak memory
        with dict_lock:
            if client_address in active_transfers:
                del active_transfers[client_address]
        print(f"[*] Thread for {client_address} shut down.")

def start_udp_server():
    """Runs the main UDP dispatcher loop."""
    print(f"[*] Threaded UDP Server ready at: {SERVER_IP}:{SERVER_PORT}")
    while True:
        try:
            raw_data, addr = server_socket.recvfrom(BUFFER_SIZE)
            with dict_lock:
                if addr in active_transfers:
                    active_transfers[addr].put(raw_data)
                else:
                    p_type, _, _, payload = unpack_p(raw_data)
                    if p_type == TYPE_REQ:
                        filename = payload.decode('utf-8')
                        client_q = queue.Queue()
                        active_transfers[addr] = client_q
                        t = threading.Thread(target=handle_file_transfer, args=(filename, addr, client_q))
                        t.daemon = True
                        t.start()
        except Exception as e:
            print(f"[-] UDP Server Error: {e}")

if __name__ == "__main__":
    start_udp_server()