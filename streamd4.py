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
import json
import sys

from PIL import Image, ImageDraw
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

import pyautogui

pyautogui.PAUSE = 0.003
pyautogui.FAILSAFE = False

# Folder location of image assets used by this example.
ASSETS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Daten")

# Global variables for paging
current_page = 1

# Read button configuration from JSON file
button_config = {}
try:
    with open('Daten/button_config.json', 'r') as config_file:
        button_config = json.load(config_file)
        current_page = button_config.get('current_page', 1)
except FileNotFoundError:
    print("Error: button_config.json not found.")
    exit(1)
except json.JSONDecodeError:
    print("Error: Invalid JSON format in button_config.json.")
    exit(1)

# Change to a new page
def change_page(deck, new_page):
    global current_page
    
    # Ensure page number is valid
    total_pages = button_config.get('total_pages', 1)
    if new_page < 1 or new_page > total_pages:
        new_page = 1
    
    print(f"Changing to page {new_page}")
    current_page = new_page
    
    # Update all button images for the new page
    for key in range(deck.key_count()):
        update_key_image(deck, key, False)

# Get current button configuration for a key
def get_button_config_for_key(key_index):
    # Add 1 to convert from 0-based to 1-based indexing
    real_key_index = key_index + 1
    
    # Find the current page data
    page_data = None
    for page in button_config.get('pages', []):
        if page.get('page_number') == current_page:
            page_data = page
            break
    
    if not page_data:
        return None
    
    # Find the button on the current page
    for button in page_data.get('buttons', []):
        if button.get('index') == real_key_index:
            return button
    
    return None

# Generates a custom tile with an image via the PIL module.
def render_key_image(deck, icon_filename):
    # Resize the source image asset to best-fit the dimensions of a single key
    try:
        icon = Image.open(icon_filename)
    except FileNotFoundError:
        # Create a blank black image if the file doesn't exist
        icon = Image.new('RGB', (72, 72), color=(0, 0, 0))
            
    image = PILHelper.create_scaled_image(deck, icon, margins=[0, 0, 0, 0])

    return PILHelper.to_native_format(deck, image)


# Returns styling information for a key based on its position and state.
def get_key_style(deck, key, state):
    # Get button configuration for this key
    button_data = get_button_config_for_key(key)
    
    # If no configuration is found for this key
    if not button_data:
        return {
            "name": str(key + 1),  # Display key + 1 (1-32 instead of 0-31)
            "icon": os.path.join(ASSETS_PATH, f"KEY{current_page}-{key + 1}.png")  # Use page-specific numbering
        }
    
    # For pressed state, always use KEY-pressed.png
    if state:
        icon = "KEY-pressed.png"
    else:
        icon = f"KEY{current_page}-{key + 1}.png"  # Use page-specific numbering
    
    name = str(key + 1)  # Display key + 1 (1-32 instead of 0-31)

    return {
        "name": name,
        "icon": os.path.join(ASSETS_PATH, icon)
    }


# Creates a new key image based on the key index, style and current key state and updates the image on the StreamDeck.
def update_key_image(deck, key, state):
    # Determine what icon to use on the generated key.
    key_style = get_key_style(deck, key, state)

    # Generate the custom key with the requested image.
    image = render_key_image(deck, key_style["icon"])

    # Use a scoped-with on the deck to ensure we're the only thread using it
    # right now.
    with deck:
        # Update requested key with the generated image.
        deck.set_key_image(key, image)


# Prints key state change information, updates the key image and performs any associated actions when a key is pressed.
def key_change_callback(deck, key, state):
    # Display key + 1 (1-32 instead of 0-31)
    print("Key {} = {} (Page {})".format(key + 1, state, current_page), flush=True)
    if state == False:
        print(" ")

    # Update the key image based on the new key state.
    update_key_image(deck, key, state)

    # Check if the key is changing to the pressed state.
    if state:
        # Get button configuration for this key
        button_data = get_button_config_for_key(key)
        
        if not button_data:
            return
            
        button_type = button_data.get('type', '')
        
        if button_type == "hotkey":
            # Handle hotkey actions
            keys = button_data.get('keys', [])
            print("control hotkey, keys:", len(keys))
            print("Executing hotkeys:", " + ".join(keys))
            
            # Press all keys
            for key_name in keys:
                pyautogui.keyDown(key_name)
            
            # Release all keys in reverse order
            for key_name in reversed(keys):
                pyautogui.keyUp(key_name)
        
        elif button_type == "action exit":
            print("Exit button pressed, shutting down...")
            # Make the StreamDeck go dark by setting all keys to black
            black_image = PILHelper.to_native_format(
                deck, 
                PILHelper.create_scaled_image(
                    deck, 
                    Image.new('RGB', (72, 72), color=(0, 0, 0)), 
                    margins=[0, 0, 0, 0]
                )
            )
            with deck:
                # Clear all the keys
                for key_index in range(deck.key_count()):
                    deck.set_key_image(key_index, black_image)
                
                # Set brightness to 0
                deck.set_brightness(0)
            
            # Close the current deck
            deck.close()
            # Exit the program
            sys.exit(0)
            
        elif button_type == "action page":
            # Handle page change
            next_page = button_data.get('next_page', 1)
            change_page(deck, next_page)


if __name__ == "__main__":
    streamdecks = DeviceManager().enumerate()

    print("Found {} Stream Deck(s).\n".format(len(streamdecks)))

    for index, deck in enumerate(streamdecks):
        deck.open()
        deck.reset()

        print("Opened '{}' device (serial number: '{}')".format(deck.deck_type(), deck.get_serial_number()))
        print(f"Current page: {current_page}")
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