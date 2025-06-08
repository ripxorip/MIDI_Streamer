#!/usr/bin/env python3

import socket
import mido

# === CONFIG ===
UDP_PORT = 8321
BUFFER_SIZE = 1024
MIDI_PORT_NAME = 'f_midi'
DEBUG = True  # Set True for extra logging of nulls etc.

# === INIT ===
print(f"[udp2midi] Listening on UDP port {UDP_PORT} → MIDI to '{MIDI_PORT_NAME}'")
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', UDP_PORT))

try:
    outport = mido.open_output(MIDI_PORT_NAME)
except IOError as e:
    print(f"[udp2midi] ❌ Could not open MIDI port '{MIDI_PORT_NAME}': {e}")
    exit(1)

# === MIDI PARSER ===
def midi_message_lengths(status_byte):
    high_nibble = status_byte & 0xF0
    if 0x80 <= status_byte <= 0xEF:
        if high_nibble in (0xC0, 0xD0):  # Program Change, Channel Pressure
            return 2
        else:
            return 3
    elif status_byte == 0xF0:  # SysEx (not handled here)
        return None
    else:
        return 1  # Simplified fallback

# === MAIN LOOP ===
while True:
    data, addr = sock.recvfrom(BUFFER_SIZE)
    idx = 0

    while idx < len(data):
        status = data[idx]

        if status == 0x00:
            if DEBUG:
                print(f"[udp2midi] Skipping null byte at index {idx}")
            idx += 1
            continue

        length = midi_message_lengths(status)

        if length is None or idx + length > len(data):
            if DEBUG:
                print(f"[udp2midi] ⚠️ Skipping incomplete/unknown MIDI message at {idx}: {data.hex()}")
            break

        msg_bytes = data[idx:idx + length]

        try:
            msg = mido.Message.from_bytes(msg_bytes)
            outport.send(msg)
            print(f"[udp2midi] ✅ {msg.type} {msg.bytes()}")
        except Exception as e:
            print(f"[udp2midi] ❌ Error parsing MIDI: {e} -> {msg_bytes.hex()}")

        idx += length

