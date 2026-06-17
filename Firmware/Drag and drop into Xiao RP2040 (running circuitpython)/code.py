# code.py — Macropad firmware for Seeed XIAO RP2040

import board
import busio
import digitalio
import neopixel
import rotaryio
import time
import usb_hid
import usb_cdc

import adafruit_ssd1306
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

# ── HID ──────────────────────────────────────────────────────────────────
cc     = ConsumerControl(usb_hid.devices)
kbd    = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)

# ── MACRO KEYS ────────────────────────────────────────────────────────────
KEY_PINS = (
    board.A0,
    board.A1,
    board.A2,
    board.A3,
    board.TX,
    board.RX,
)

KEY_ACTIONS = (
    ("key", (Keycode.CONTROL, Keycode.C)),   # Copy
    ("cc",  ConsumerControlCode.SCAN_PREVIOUS_TRACK),
    ("key", (Keycode.CONTROL, Keycode.V)),   # Paste
    ("cc",  ConsumerControlCode.PLAY_PAUSE),
    ("cc",  ConsumerControlCode.SCAN_NEXT_TRACK),
    ("toggle_led", None),
)

KEY_LABELS = {
    (Keycode.CONTROL, Keycode.C): "Copy",
    (Keycode.CONTROL, Keycode.V): "Paste",
    (Keycode.CONTROL, Keycode.Z): "Undo",
    ConsumerControlCode.SCAN_PREVIOUS_TRACK: "Prev Track",
    ConsumerControlCode.SCAN_NEXT_TRACK: "Next Track",
    ConsumerControlCode.PLAY_PAUSE: "Play / Pause",
}

_keys = []
for _p in KEY_PINS:
    _b = digitalio.DigitalInOut(_p)
    _b.direction = digitalio.Direction.INPUT
    _b.pull = digitalio.Pull.UP
    _keys.append(_b)

_key_prev = [False] * len(_keys)

def _send_key(action):
    global _leds_enabled
    global _oled_sleep

    kind, val = action

    if kind == "cc":
        cc.send(val)
        show_overlay(KEY_LABELS.get(val, "Media"))

    elif kind == "key":
        kbd.press(*val)
        kbd.release_all()
        show_overlay(KEY_LABELS.get(val, "Key Combo"))

    elif kind == "toggle_led":
        _leds_enabled = not _leds_enabled

        if _leds_enabled:
            _oled_sleep = False
            show_overlay("LEDs ON")

        else:
            show_overlay("LEDs OFF")

            pixels.fill((0, 0, 0))
            pixels.show()

            onboard.fill((0, 0, 0))
            onboard.show()

            _oled_sleep = True

# ── ROTARY ENCODER ────────────────────────────────────────────────────────
encoder = rotaryio.IncrementalEncoder(board.MOSI, board.SCK)
_enc_last = encoder.position

# ── SK6812 MINI LEDs (macropad) ──────────────────────────────────────────
pixels = neopixel.NeoPixel(
    board.MISO,
    2,
    brightness=0.5,
    auto_write=False,
    pixel_order=neopixel.GRB
)

# ── Onboard XIAO RP2040 LED ──────────────────────────────────────────────
onboard = neopixel.NeoPixel(
    board.NEOPIXEL,
    1,
    brightness=0.2,
    auto_write=False,
    pixel_order=neopixel.GRB
)

def _wheel(pos):
    pos = pos % 255

    if pos < 85:
        return (255 - pos * 3, pos * 3, 0, 0)
    elif pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3, 0)
    else:
        pos -= 170
        return (pos * 3, 0, 255 - pos * 3, 0)

_hue = 0
_leds_enabled = True
_oled_sleep = False

# ── OLED SSD1306 128x32 ───────────────────────────────────────────────────
_i2c = busio.I2C(board.SCL, board.SDA)
oled  = adafruit_ssd1306.SSD1306_I2C(128, 32, _i2c)

_MAX_ARTIST = 21
_MAX_SONG   = 10

def _oled_refresh(artist, song):
    oled.fill(0)
    oled.text(song[:_MAX_SONG], 0, 0, 1)

    src_w = _MAX_SONG * 6
    pixels_on = []

    for y in range(8):
        for x in range(src_w):
            if oled.pixel(x, y):
                pixels_on.append((x, y))

    oled.fill(0)
    oled.text(artist[:_MAX_ARTIST], 0, 0, 1)

    for (x, y) in pixels_on:
        dx = x * 2
        dy = y * 2 + 16
        if dy + 1 < 32:
            oled.pixel(dx, dy, 1)
            oled.pixel(dx + 1, dy, 1)
            oled.pixel(dx, dy + 1, 1)
            oled.pixel(dx + 1, dy + 1, 1)

    oled.show()

_oled_refresh("Now Playing", "Waiting...")

# ── SCROLLING ─────────────────────────────────────────────────────────────
_SCROLL_SPD = 0.22
_PAUSE_LEN  = 1.8

_line1_txt    = "Now Playing"
_scroll_txt   = "Waiting..."
_scroll_pos   = 0
_scroll_state = "pause_start"
_scroll_ts    = 0.0

def _visible():
    if len(_scroll_txt) <= _MAX_SONG:
        return _scroll_txt
    return _scroll_txt[_scroll_pos:_scroll_pos + _MAX_SONG]

def set_now_playing(raw):
    global _line1_txt, _scroll_txt, _scroll_pos, _scroll_state, _scroll_ts

    raw = raw.strip()

    if " - " in raw:
        title, artist = raw.split(" - ", 1)
        _line1_txt  = artist[:_MAX_ARTIST]
        _scroll_txt = title
    else:
        _line1_txt  = "Now Playing"
        _scroll_txt = raw

    _scroll_pos   = 0
    _scroll_state = "pause_start"
    _scroll_ts    = time.monotonic()

    _oled_refresh(_line1_txt, _visible())

def _tick_scroll(now):
    global _scroll_pos, _scroll_state, _scroll_ts

    if len(_scroll_txt) <= _MAX_SONG:
        return

    max_pos = len(_scroll_txt) - _MAX_SONG

    if _scroll_state == "pause_start":
        if now - _scroll_ts >= _PAUSE_LEN:
            _scroll_state = "scrolling"
            _scroll_ts = now

    elif _scroll_state == "scrolling":
        if now - _scroll_ts >= _SCROLL_SPD:
            _scroll_pos = min(_scroll_pos + 1, max_pos)
            _oled_refresh(_line1_txt, _visible())
            _scroll_ts = now

            if _scroll_pos >= max_pos:
                _scroll_state = "pause_end"

    elif _scroll_state == "pause_end":
        if now - _scroll_ts >= _PAUSE_LEN:
            _scroll_pos = 0
            _scroll_state = "pause_start"
            _scroll_ts = now
            _oled_refresh(_line1_txt, _visible())

# ── OLED OVERLAY SYSTEM ───────────────────────────────────────────────────
_overlay_text = None
_overlay_until = 0
_overlay_active = False

def show_overlay(text):
    
    

    
    global _overlay_text, _overlay_until, _overlay_active

    _overlay_text = text
    _overlay_until = time.monotonic() + 1.5
    _overlay_active = True

    oled.fill(0)
    oled.text("KEY:", 0, 0, 1)
    oled.text(text[:21], 0, 16, 1)
    oled.show()

# ── SERIAL ────────────────────────────────────────────────────────────────
_serial = usb_cdc.data

# ── MAIN LOOP ─────────────────────────────────────────────────────────────
while True:
    _now = time.monotonic()

    # Rotary encoder → volume
    _pos = encoder.position
    if _pos != _enc_last:
        _delta = _pos - _enc_last
        _code  = (ConsumerControlCode.VOLUME_INCREMENT
                  if _delta > 0 else ConsumerControlCode.VOLUME_DECREMENT)

        for _ in range(min(abs(_delta), 5)):
            cc.send(_code)

        _enc_last = _pos

    # Macro keys
    for _i, _btn in enumerate(_keys):
        _pressed = not _btn.value
        if _pressed and not _key_prev[_i]:
            _send_key(KEY_ACTIONS[_i])
        _key_prev[_i] = _pressed

    # NowPlaying from PC
    if _serial and _serial.in_waiting:
        _line = _serial.readline()
        if _line:
            set_now_playing(_line.decode("utf-8"))

        # ── LEDs (rainbow synced) ───────────────────────────────────────────
    if _leds_enabled:
        _hue = (_hue + 1) % 255
        color = _wheel(_hue)

        pixels[0] = color
        pixels[1] = color
        pixels.show()

        onboard[0] = color
        onboard.show()

    # ── OLED update logic ────────────────────────────────────────────────
    if _overlay_active:
        if time.monotonic() >= _overlay_until:
            _overlay_active = False

            if _oled_sleep:
                oled.fill(0)
                oled.show()
            else:
                _oled_refresh(_line1_txt, _visible())

    elif _oled_sleep:
        pass

    else:
        _tick_scroll(_now)

    time.sleep(0.005)