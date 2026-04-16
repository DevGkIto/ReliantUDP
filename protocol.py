import struct
import hashlib

# --- Packet Types ---
TYPE_REQ   = 0  # Client requesting a file
TYPE_DATA  = 1  # Server sending data
TYPE_ACK   = 2  # Client confirming receipt
TYPE_ERROR = 3  # File not found or other errors

# --- Format: Type (B), Sequence (I), Checksum (16s), Payload (Variable) ---
# 'B' = unsigned char (1 byte)
# 'I' = unsigned int (4 bytes)
# '16s' = 16-byte string (for MD5)
HEADER_FORMAT = "!BI16s"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

def calculate_md5(data):
    return hashlib.md5(data).digest()

def pack_p(p_type, seq, checksum, payload):
    header = struct.pack(HEADER_FORMAT, p_type, seq, checksum)
    return header + payload

def unpack_p(raw_packet):
    header = raw_packet[:HEADER_SIZE]
    payload = raw_packet[HEADER_SIZE:]
    p_type, seq, checksum = struct.unpack(HEADER_FORMAT, header)
    return p_type, seq, checksum, payload