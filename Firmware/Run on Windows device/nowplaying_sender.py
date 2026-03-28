#!/usr/bin/env python3
"""
nowplaying_sender.py — runs on your Windows PC in the background.
Watches Rainmeter's NowPlaying.txt and pushes updates to the macropad
over USB serial whenever the track changes.

Requirements:
    pip install pyserial watchdog

Run once at startup (add to Task Scheduler or your shell's startup script).
"""

import os
import sys
import time
import threading

import serial
import serial.tools.list_ports
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# ── Path to your Rainmeter NowPlaying file ────────────────────────────────
# This uses your Windows username automatically — no editing needed
# as long as Rainmeter is in the default Documents location.
NOWPLAYING_PATH = r"C:\Users\eastm\OneDrive\Documents\Rainmeter\Skins\NowPlayingToText\@Resources\NowPlaying.txt"

# ── Serial port settings ──────────────────────────────────────────────────
BAUD = 115200
# Leave as None to auto-detect, or hardcode e.g. "COM5" if auto-detect fails.
MANUAL_PORT = "COM8"


# ── Port detection ────────────────────────────────────────────────────────
def find_macropad_port() -> str | None:
    """
    CircuitPython with usb_cdc.enable(data=True) creates TWO serial ports.
    The data port (CDC2) is the one we want — it's usually the higher COM number.
    """
    ports = sorted(serial.tools.list_ports.comports(), key=lambda p: p.device)
    cp_ports = [p for p in ports if "CircuitPython" in (p.description or "")]

    if not cp_ports:
        return None

    print("Found CircuitPython port(s):")
    for p in cp_ports:
        print(f"  {p.device}  —  {p.description}")

    # CDC2 (data port) is typically described with "CDC2" or is the last/higher port
    data_ports = [p for p in cp_ports if "CDC2" in (p.description or "")]
    if data_ports:
        return data_ports[0].device

    # Fallback: if there are two ports, the second one is the data port
    if len(cp_ports) >= 2:
        return cp_ports[1].device

    # Only one port found — use it (works if console is disabled or same port)
    return cp_ports[0].device


# ── Sender ────────────────────────────────────────────────────────────────
class NowPlayingSender:
    def __init__(self, port: str):
        self.port = port
        self.ser: serial.Serial | None = None
        self._lock = threading.Lock()
        self._connect()

    def _connect(self):
        try:
            self.ser = serial.Serial(self.port, BAUD, timeout=1)
            print(f"✓ Connected to macropad on {self.port}")
        except serial.SerialException as e:
            print(f"✗ Could not open {self.port}: {e}")
            self.ser = None

    def send(self, text: str):
        if not self.ser:
            self._connect()
            if not self.ser:
                return
        with self._lock:
            try:
                payload = (text.strip() + "\n").encode("utf-8")
                self.ser.write(payload)
                print(f"→ Sent: {text.strip()!r}")
            except serial.SerialException:
                print("Connection lost — will retry on next update.")
                self.ser = None

    def send_file(self):
        """Read NowPlaying.txt and send its contents."""
        if not os.path.exists(NOWPLAYING_PATH):
            print(f"File not found: {NOWPLAYING_PATH}")
            return
        try:
            with open(NOWPLAYING_PATH, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
            if content:
                self.send(content)
        except OSError as e:
            print(f"Could not read file: {e}")


# ── Watchdog event handler ────────────────────────────────────────────────
class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, sender: NowPlayingSender):
        super().__init__()
        self.sender = sender
        self._last_send = 0.0

    def on_modified(self, event):
        # Only react to our specific file
        if not event.is_directory and os.path.abspath(event.src_path) == os.path.abspath(NOWPLAYING_PATH):
            # Debounce: Rainmeter sometimes fires multiple events per update
            now = time.time()
            if now - self._last_send > 0.5:
                self._last_send = now
                time.sleep(0.1)   # tiny delay so Rainmeter finishes writing
                self.sender.send_file()


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    # 1. Validate file path
    if not os.path.exists(NOWPLAYING_PATH):
        print(f"\n⚠  NowPlaying.txt not found at:\n   {NOWPLAYING_PATH}")
        print("\nMake sure the Rainmeter NowPlayingToText skin is active.")
        print("If your Rainmeter folder is in a different location, edit NOWPLAYING_PATH in this script.")
        sys.exit(1)

    # 2. Find the macropad serial port
    port = MANUAL_PORT or find_macropad_port()
    if not port:
        print("\n⚠  Macropad not found on any serial port.")
        print("Make sure:")
        print("  1. The XIAO is plugged in via USB")
        print("  2. boot.py is on the CIRCUITPY drive (enables the data port)")
        print("  3. CircuitPython is installed on the XIAO")
        print("\nAvailable ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device}  —  {p.description}")
        print("\nIf you can see the port above, set  MANUAL_PORT = 'COMx'  at the top of this script.")
        sys.exit(1)

    # 3. Connect and send the current track immediately
    sender = NowPlayingSender(port)
    sender.send_file()

    # 4. Watch for future changes
    watch_dir = os.path.dirname(NOWPLAYING_PATH)
    handler   = FileChangeHandler(sender)
    observer  = Observer()
    observer.schedule(handler, path=watch_dir, recursive=False)
    observer.start()

    print(f"\nWatching: {NOWPLAYING_PATH}")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
        if sender.ser:
            sender.ser.close()
        print("Stopped.")


if __name__ == "__main__":
    main()
