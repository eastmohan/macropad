# boot.py — runs once at power-on, before code.py
# Enables a second USB serial port so the NowPlaying sender script
# can push track info to the macropad without interfering with the REPL.

import usb_cdc
usb_cdc.enable(console=True, data=True)
