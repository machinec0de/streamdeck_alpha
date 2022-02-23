#!/usr/bin/env python3

#         Python Stream Deck Library
#      Released under the MIT license
#
#   dean [at] fourwalledcubicle [dot] com
#         www.fourwalledcubicle.com
#

# Example script showing basic library usage - updating key images with new
# tiles generated at runtime, and responding to button state change events.

import os
import threading

from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

import pyautogui

pyautogui.PAUSE = 0.003
pyautogui.FAILSAFE = False

# Folder location of image assets used by this example.
ASSETS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Daten\Buttons")

# Read button labels and actions from file
button_control = []
with open ('Daten/button_control.txt', 'rt') as myfile:
    for myline in myfile:
        button_control.append(myline)
button_control = [x.strip('\n') for x in button_control]
button_control_parse = []

# Set toggle switch for brightness-button
brightness_switch = 1
record_switch = 0

# Generates a custom tile with run-time generated text and custom image via the
# PIL module.
def render_key_image(deck, icon_filename, font_filename, label_text):
    # Resize the source image asset to best-fit the dimensions of a single key,
    # leaving a margin at the bottom so that we can draw the key title
    # afterwards.
    icon = Image.open(icon_filename)
    image = PILHelper.create_scaled_image(deck, icon, margins=[0, 0, 5, 0])

    # Load a custom TrueType font and use it to overlay the key index, draw key
    # label onto the image.
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_filename, 14)
    label_w, label_h = draw.textsize(label_text, font=font)
    label_pos = ((image.width - label_w) // 2, image.height - 20)
    draw.text(label_pos, text=label_text, font=font, fill="white")

    return PILHelper.to_native_format(deck, image)


# Returns styling information for a key based on its position and state.
def get_key_style(deck, key, state):
    # Set exit button.
    exit_key_index = 77

    button_control_parse = button_control[key]              # prepare to split data in button_control.text
    button_control_parse = button_control_parse.split('+')  # split data at "+"
    button_labels = button_control_parse[0]                 # first entry up to "+" -> button-label

    if button_control_parse[1] == "EXIT":
        name = "exit"
        icon = "{}.png".format("KEY{}p".format(key) if state else "KEY{}".format(key))
        #icon = "{}.png".format("KEYp" if state else "KEY{}".format(key))
        font = "Roboto-Regular.ttf"
        label = "Bye" if state else "Exit"
    else:
        if button_control_parse[1] == "_toggle":
            global record_switch
            if record_switch == 1:
                icon = "{}.png".format("KEY{}p".format(key) if state else "KEY{}_1".format(key))
                record_switch = 0
            else:
                icon = "{}.png".format("KEY{}p".format(key) if state else "KEY{}_0".format(key))
                record_switch = 1
        else:
            icon = "{}.png".format("KEY{}p".format(key) if state else "KEY{}".format(key))
            #icon = "{}.png".format("KEYp" if state else "KEY{}".format(key))

        name = key
        font = "Roboto-Regular.ttf"
        label = button_labels

    return {
        "name": name,
        "icon": os.path.join(ASSETS_PATH, icon),
        "font": os.path.join(ASSETS_PATH, font),
        "label": label
    }


# Creates a new key image based on the key index, style and current key state
# and updates the image on the StreamDeck.
def update_key_image(deck, key, state):
    # Determine what icon and label to use on the generated key.
    key_style = get_key_style(deck, key, state)

    # Generate the custom key with the requested image and label.
    image = render_key_image(deck, key_style["icon"], key_style["font"], key_style["label"])

    # Use a scoped-with on the deck to ensure we're the only thread using it
    # right now.
    with deck:
        # Update requested key with the generated image.
        deck.set_key_image(key, image)


# Prints key state change information, updates rhe key image and performs any
# associated actions when a key is pressed.
def key_change_callback(deck, key, state):

    # Print new key state
    ### print("Deck {} Key {} = {}".format(deck.id(), key, state), flush=True)
    print("Key {} = {}".format(key, state), flush=True)
    if state == False:
        print(" ")

    # Update the key image based on the new key state.
    update_key_image(deck, key, state)

    # Check if the key is changing to the pressed state.
    if state:
        key_style = get_key_style(deck, key, state)

        # When an exit button is pressed, close the application.
        if key_style["name"] == "exit":
            # Use a scoped-with on the deck to ensure we're the only thread
            # using it right now.
            with deck:
                # Reset deck, clearing all button images.
                deck.reset()
                # Close deck handle, terminating internal worker threads.
                deck.close()
        else:
            print("button_control raw data: {}".format(button_control[key]))
            button_control_parse = button_control[key]                  # prepare to split data in button_control.text
            button_control_parse = button_control_parse.split('+')      # split data at "+"

            global brightness_switch                                    # set toggle-variable to global
            if button_control_parse[1] == "_brightness":                # if action ist set to _brightness toggle between first and second value
                print("control brightness")
                if brightness_switch == 0:
                    deck.set_brightness(int(button_control_parse[2]))
                    brightness_switch = 1
                else:
                    deck.set_brightness(int(button_control_parse[3]))
                    brightness_switch = 0
            elif button_control_parse[1] == "_hotkey" or "_record":                   # use hotkey with up to 4 arguments
                print("control hotkey, keys:", len(button_control_parse)-2)
                for x in range(2, len(button_control_parse)):
                    pyautogui.keyDown(button_control_parse[x])
                    #print("_hotkey key-down:", button_control_parse[x])

                for x in reversed(range(2, len(button_control_parse))):
                    pyautogui.keyUp(button_control_parse[x])
                    #print("_hotkey key-up:", button_control_parse[x])

if __name__ == "__main__":
    streamdecks = DeviceManager().enumerate()

    print("Found {} Stream Deck(s).\n".format(len(streamdecks)))

    for index, deck in enumerate(streamdecks):
        deck.open()
        deck.reset()

        print("Opened '{}' device (serial number: '{}')".format(deck.deck_type(), deck.get_serial_number()))
        print(" ")

        # Set initial screen brightness.
        deck.set_brightness(55)

        # Set initial key images.
        for key in range(deck.key_count()):
            update_key_image(deck, key, False)


        # Register callback function for when a key state changes.
        deck.set_key_callback(key_change_callback)

        # Wait until all application threads have terminated (for this example,
        # this is when all deck handles are closed).
        for t in threading.enumerate():
            if t is threading.current_thread():
                continue

            if t.is_alive():
                t.join()
