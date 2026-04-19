import socket
from protocol import *

# --- Static Configuration ---
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000
TARGET_FILE = "test.txt"
MAX_RETRIES = 5

def request_file_transfer(server_ip, server_port, filename, max_retries=5):
    """Phase 1: Handshake"""
    request_packet = pack_p(TYPE_REQ, 0, calculate_md5(b""), filename.encode("utf-8"))
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[*] Requesting '{filename}' from {server_ip}:{server_port} (Attempt {attempt})...")
            client_socket.sendto(request_packet, (server_ip, server_port))
            client_socket.settimeout(2.0)
            initial_response, server_address = client_socket.recvfrom(2048)
            return initial_response, server_address, client_socket
        except socket.timeout:
            print("[!] Handshake timed out. Retrying...")
    
    return None, None, client_socket

def process_download(initial_response, server_address, client_socket, filename, session_id):
    """Phase 2: Reliable Data Reception (Dumb, Fast, Predictable)"""
    expected_sequence = 0
    current_packet = initial_response # The "Baton"
    client_socket.settimeout(5.0)
    output_filename = f"received_{filename}"

    print(f"[*] Connection established. Acting as a fast, reliable receiver.")

    with open(output_filename, "wb") as f:
        while True:
            # If baton is empty, wait for next packet
            if current_packet is None:
                try:
                    current_packet, _ = client_socket.recvfrom(2048)
                except socket.timeout:
                    print("[-] Connection lost. Server stopped responding.")
                    break

            # --- SIMULATED LOSS BLOCK ENTIRELY REMOVED ---

            p_type, seq, checksum, payload = unpack_p(current_packet)
            
            if calculate_md5(payload) != checksum:
                print(f"[!] Corruption in segment {seq}. Discarding.")
            else:
                if seq == expected_sequence:
                    if payload: # Data chunk
                        f.write(payload)
                        print(f"[+] Saved segment {seq}")
                        ack = pack_p(TYPE_ACK, seq, calculate_md5(b""), b"")
                        client_socket.sendto(ack, server_address)
                        expected_sequence += 1
                    else: # EOF
                        print("[*] EOF reached. Download successful!")
                        ack = pack_p(TYPE_ACK, seq, calculate_md5(b""), b"")
                        client_socket.sendto(ack, server_address)
                        break
                elif seq < expected_sequence:
                    print(f"[?] Duplicate {seq} received. Resending ACK.")
                    ack = pack_p(TYPE_ACK, seq, calculate_md5(b""), b"")
                    client_socket.sendto(ack, server_address)

            current_packet = None

def run_udp_transfer(session_id: str, target_file: str = "test.txt"):
    """
    Entrypoint for the API to trigger a native in-memory UDP transfer.
    """
    print(f"--- UTFPR Reliable UDP Client (Session: {session_id}) ---")
    
    try:
        init_pkt, srv_addr, sock = request_file_transfer(SERVER_IP, SERVER_PORT, target_file)
        
        if init_pkt:
            p_type, _, _, data = unpack_p(init_pkt)
            if p_type == TYPE_ERROR:
                print(f"[-] SERVER ERROR: {data.decode()}")
            else:
                process_download(init_pkt, srv_addr, sock, target_file, session_id)
        
        sock.close()
    except Exception as e:
        print(f"[-] Error in session {session_id}: {e}")
    finally:
        print(f"[*] Session {session_id} shutdown.")