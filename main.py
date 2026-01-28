# Imports
import board, busio, displayio, terminalio, usb_cdc
from adafruit_display_text import label
from kmk.kmk_keyboard import KMKKeyboard
from kmk.scanners.keypad import KeysScanner
from kmk.keys import KC
from kmk.modules.macros import Press, Release, Tap, Macros
from kmk.modules.encoder import EncoderHandler
from kmk.extensions.OLED import OLED

# Initialize keyboard
keyboard = KMKKeyboard()

# Modules
macros = Macros()
keyboard.modules.append(macros)

encoder_handler = EncoderHandler()
keyboard.modules.append(encoder_handler)

# Pins
PINS = [board.D26, board.D27, board.D28, board.D29, board.D0, board.D1]
encoder_handler.pins = ((board.D2, board.D3, None),)

keyboard.matrix = KeysScanner(pins=PINS, value_when_pressed=False)

# Keymap
keyboard.keymap = [
    [
        KC.MPRV,
        KC.LGUI(KC.N4),
        KC.MPLY,
        KC.Macro(Press(KC.LCTRL), Tap(KC.S), Release(KC.LCTRL)),
        KC.MNXT,
        KC.LGUI(KC.C),
    ]
]

# Encoder
encoder_handler.map = [
    ((KC.VOLD, KC.VOLU),),
]

# OLED render
def oled_render(oled):
    title = "Waiting..."
    artist = ""
    if usb_cdc.data.in_waiting > 0:
        line = usb_cdc.data.readline().decode("utf-8").strip()
        if " - " in line:
            parts = line.split(" - ", 1)
            title, artist = parts[0], parts[1]
        else:
            title = line
    oled.canvas.fill(0)
    oled.canvas.text(title, 0, 0, 1)
    oled.canvas.text(artist, 0, 16, 1)
    oled.canvas.show()

oled_ext = OLED(render_fn=oled_render)
keyboard.extensions.append(oled_ext)

# Start KMK
if __name__ == '__main__':
    keyboard.go()