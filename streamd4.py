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
import tkinter as tk
from tkinter import Label, Frame, StringVar, GROOVE, RAISED, RIDGE, TOP, LEFT, RIGHT, BOTTOM, X, Y, BOTH, FLAT
from PIL import Image, ImageDraw, ImageTk
import queue

# Unterdrücke die IMK-Meldungen unter macOS
if sys.platform == 'darwin':
    os.environ['NSUnbufferedIO'] = 'YES'
    os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
    # Leite stderr in eine Null-Datei um, wenn wir nicht im Debug-Modus sind
    if not os.environ.get('DEBUG_MODE'):
        sys.stderr = open(os.devnull, 'w')

from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

import pyautogui

pyautogui.PAUSE = 0.003
pyautogui.FAILSAFE = False

# Folder location of image assets used by this example.
ASSETS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Daten")

# Global variables for paging
current_page = 1

# Global variables for the UI
root = None
title_label = None
info_frame = None
key_image_label = None
current_key_image = None
ui_queue = queue.Queue()
last_normal_key_style = None  # Speichert den letzten normalen Tastenstil
cached_images = {}  # Cache für die geladenen Bilder
info_vars = {}  # StringVars für die Informationen

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

# Preload images
def preload_images():
    global cached_images
    
    # Create directory for all pages and all buttons
    for page_num in range(1, button_config.get('total_pages', 2) + 1):
        for key_num in range(1, 33):  # Assuming max 32 keys
            normal_path = os.path.join(ASSETS_PATH, f"KEY{page_num}-{key_num}.png")
            if os.path.exists(normal_path):
                try:
                    img = Image.open(normal_path)
                    img = img.resize((200, 200), Image.LANCZOS)
                    cached_images[f"KEY{page_num}-{key_num}"] = ImageTk.PhotoImage(img)
                except Exception as e:
                    print(f"Error preloading image {normal_path}: {e}")
    
    # Also load pressed key
    pressed_path = os.path.join(ASSETS_PATH, "KEY-pressed.png")
    if os.path.exists(pressed_path):
        try:
            img = Image.open(pressed_path)
            img = img.resize((200, 200), Image.LANCZOS)
            cached_images["KEY-pressed"] = ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error preloading pressed image: {e}")

# Setup the UI window
def setup_ui():
    global root, title_label, info_frame, key_image_label, info_vars
    
    root = tk.Tk()
    root.title("Stream Deck Viewer")
    root.geometry("500x650")
    root.configure(bg="#2C2C2C")
    # Fenster nicht skalierbar machen
    root.resizable(False, False)
    
    # Icon für das Fenster (Tastatur-Symbol)
    try:
        iconpath = os.path.join(ASSETS_PATH, "app_icon.png")
        if os.path.exists(iconpath):
            img = Image.open(iconpath)
            app_icon = ImageTk.PhotoImage(img)
            root.iconphoto(True, app_icon)
    except Exception as e:
        print(f"Error loading app icon: {e}")
    
    # Titel mit Schatten-Effekt
    title_frame = Frame(root, bg="#252525", relief=RAISED, bd=0)
    title_frame.pack(fill=X, padx=0, pady=0)
    
    title_inner_frame = Frame(title_frame, bg="#3D3D3D", padx=0, pady=10)
    title_inner_frame.pack(fill=X)
    
    title_label = Label(title_inner_frame, text="STREAM DECK VIEWER", font=("Arial", 20, "bold"), 
                       bg="#3D3D3D", fg="#FFFFFF", pady=5)
    title_label.pack()
    
    separator = Frame(root, height=2, bg="#5A92FF")
    separator.pack(fill=X, padx=0, pady=0)
    
    # Container für Bild und Info
    content_frame = Frame(root, bg="#2C2C2C")
    content_frame.pack(fill=BOTH, expand=True, padx=15, pady=15)
    
    # Bereich für das Tastenbild mit Schatten-Effekt
    image_outer_frame = Frame(content_frame, bg="#222222", padx=3, pady=3)
    image_outer_frame.pack(pady=10, padx=10)
    
    image_frame = Frame(image_outer_frame, bg="#2C2C2C", relief=RIDGE, bd=1, padx=1, pady=1)
    image_frame.pack()
    
    # Platzhalter für Tastenbild (mit fester Größe)
    key_image_label = Label(image_frame, width=200, height=200, bg="#2C2C2C")
    key_image_label.pack(padx=10, pady=10)
    
    # Info-Rahmen mit vordefinierten Feldern und Schatten-Effekt
    info_outer_frame = Frame(content_frame, bg="#222222", padx=3, pady=3)
    info_outer_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    
    info_frame = Frame(info_outer_frame, bg="#2A2A2A", relief=FLAT, bd=0)
    info_frame.pack(fill=BOTH, expand=True)
    
    # Vordefinierte Info-Felder
    info_vars = {
        "key": StringVar(value="---"),
        "state": StringVar(value="---"),
        "page": StringVar(value="---"),
        "type": StringVar(value="---"),
        "action": StringVar(value="---")
    }
    
    # Info-Header
    info_header = Label(info_frame, text="BUTTON INFORMATION", font=("Arial", 14, "bold"), 
                       bg="#3A3A3A", fg="#FFFFFF", pady=8)
    info_header.pack(fill=X)
    
    # Inneres Frame für Info-Felder
    fields_frame = Frame(info_frame, bg="#2A2A2A", padx=10, pady=10)
    fields_frame.pack(fill=BOTH, expand=True)
    
    # Erstelle Labels für jedes Info-Feld mit abgerundeten Rahmen
    info_fields = [
        {"name": "Key"},
        {"name": "State"},
        {"name": "Page"},
        {"name": "Type"},
        {"name": "Action"}
    ]
    
    for idx, field_info in enumerate(info_fields):
        field_name = field_info["name"].lower()
        field_frame = Frame(fields_frame, bg="#2A2A2A")
        field_frame.pack(fill=X, pady=5)
        
        # Bezeichnung
        label_frame = Frame(field_frame, bg="#2A2A2A")
        label_frame.pack(side=LEFT, padx=(0, 5))
        
        label = Label(label_frame, text=f"{field_info['name']}:", font=("Arial", 14, "bold"), 
                      bg="#2A2A2A", fg="#9EAEFF", width=10, anchor='w')
        label.pack(side=LEFT)
        
        # Wert in einem eigenen Frame mit Hintergrund
        value_frame = Frame(field_frame, bg="#333333", bd=1, relief=GROOVE, padx=8, pady=3)
        value_frame.pack(side=LEFT, fill=X, expand=True)
        
        value_label = Label(value_frame, textvariable=info_vars[field_name], font=("Arial", 14), 
                           bg="#333333", fg="#FFFFFF")
        value_label.pack(fill=X)
    
    # Status-Bar mit Farbverlauf
    status_frame = Frame(root, height=25, bg="#1E1E1E", relief=FLAT)
    status_frame.pack(fill=X, side=BOTTOM)
    
    status_label = Label(status_frame, text="Ready", font=("Arial", 10), 
                        bg="#1E1E1E", fg="#AAAAAA", pady=3)
    status_label.pack(side=LEFT, padx=10)
    
    # Aktuelles Datum auf der rechten Seite
    from datetime import datetime
    date_label = Label(status_frame, text=datetime.now().strftime("%d.%m.%Y"), 
                      font=("Arial", 10), bg="#1E1E1E", fg="#AAAAAA", pady=3)
    date_label.pack(side=RIGHT, padx=10)
    
    # Configure the close event
    root.protocol("WM_DELETE_WINDOW", on_close)
    
    return root

# Handle window close
def on_close():
    global root
    if root:
        root.destroy()
    sys.exit(0)

# Process UI queue to update UI from the main thread
def process_ui_queue():
    global root, ui_queue
    
    try:
        while True:
            # Get item from queue without blocking
            item = ui_queue.get_nowait()
            
            if item["type"] == "update_info":
                _update_ui_info_internal(item["key"], item["state"], item["page"], item["button_data"])
            elif item["type"] == "change_page":
                if info_vars["page"]:
                    info_vars["page"].set(str(item['page']))
                title_label.config(text=f"Stream Deck Viewer - Page {item['page']}")
    except queue.Empty:
        pass
    
    # Schedule to check queue again
    if root and root.winfo_exists():
        root.after(100, process_ui_queue)

# Internal function to update the UI (called from the main thread)
def _update_ui_info_internal(key, state, page, button_data=None):
    global key_image_label, current_key_image, last_normal_key_style, info_vars
    
    if not root or not root.winfo_exists():
        return
    
    # Update info text fields
    info_vars["key"].set(str(key + 1))
    info_vars["state"].set("Pressed" if state else "Released")
    info_vars["page"].set(str(page))
    
    # Update button type and action info
    if button_data and state:
        button_type = button_data.get('type', '')
        info_vars["type"].set(button_type.capitalize())
        
        if button_type == "hotkey":
            keys = button_data.get('keys', [])
            info_vars["action"].set(" + ".join(keys))
        elif button_type == "action page":
            next_page = button_data.get('next_page', 1)
            info_vars["action"].set(f"Go to page {next_page}")
        elif button_type == "action exit":
            info_vars["action"].set("Exit program")
        else:
            info_vars["action"].set("---")
    else:
        # Wenn keine Taste gedrückt ist
        if not state:
            info_vars["type"].set("---")
            info_vars["action"].set("---")
    
    # Versuche, das Tastenbild zu aktualisieren
    try:
        # Hol den Tastenstil
        key_style = get_key_style(None, key, False)  # Immer den normalen Stil holen
        
        # Speichere den letzten normalen Tastenstil
        if state:  # Wenn die Taste gedrückt wurde
            last_normal_key_style = key_style
        
        # Entscheide, welches Bild angezeigt werden soll
        display_style = last_normal_key_style if last_normal_key_style else key_style
        
        # Versuche, das Bild aus dem Cache zu laden
        image_key = os.path.basename(display_style["icon"]).replace(".png", "")
        if image_key in cached_images:
            key_image_label.config(image=cached_images[image_key])
            current_key_image = cached_images[image_key]
        else:
            # Wenn nicht im Cache, lade und speichere es
            if os.path.exists(display_style["icon"]):
                img = Image.open(display_style["icon"])
                img = img.resize((200, 200), Image.LANCZOS)
                current_key_image = ImageTk.PhotoImage(img)
                cached_images[image_key] = current_key_image
                key_image_label.config(image=current_key_image)
    except Exception as e:
        print(f"Error updating image: {e}")

# Thread-safe function to update the UI info (called from any thread)
def update_ui_info(key, state, page, button_data=None):
    global ui_queue
    
    # Add request to the queue
    ui_queue.put({
        "type": "update_info",
        "key": key,
        "state": state,
        "page": page,
        "button_data": button_data
    })

# Change to a new page
def change_page(deck, new_page):
    global current_page, ui_queue
    
    # Ensure page number is valid
    total_pages = button_config.get('total_pages', 1)
    if new_page < 1 or new_page > total_pages:
        new_page = 1
    
    # print(f"Changing to page {new_page}")
    current_page = new_page
    
    # Update UI via queue
    ui_queue.put({
        "type": "change_page",
        "page": new_page
    })
    
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
    # Get button configuration for this key
    button_data = get_button_config_for_key(key)
    
    # Update the UI
    update_ui_info(key, state, current_page, button_data)
    
    # Update the key image based on the new key state.
    update_key_image(deck, key, state)

    # Check if the key is changing to the pressed state.
    if state:
        if not button_data:
            return
            
        button_type = button_data.get('type', '')
        
        if button_type == "hotkey":
            # Handle hotkey actions
            keys = button_data.get('keys', [])
            
            # Press all keys
            for key_name in keys:
                pyautogui.keyDown(key_name)
            
            # Release all keys in reverse order
            for key_name in reversed(keys):
                pyautogui.keyUp(key_name)
        
        elif button_type == "action exit":
            # print("Exit button pressed, shutting down...")
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
            if root:
                root.destroy()
            sys.exit(0)
            
        elif button_type == "action page":
            # Handle page change
            next_page = button_data.get('next_page', 1)
            change_page(deck, next_page)


if __name__ == "__main__":
    # Setup the UI
    setup_ui()
    
    # Preload images AFTER setting up the UI (tkinter root window must exist first)
    preload_images()
    
    streamdecks = DeviceManager().enumerate()

    # print("Found {} Stream Deck(s).\n".format(len(streamdecks)))

    for index, deck in enumerate(streamdecks):
        deck.open()
        deck.reset()

        print("Opened '{}' device (serial number: '{}')".format(deck.deck_type(), deck.get_serial_number()))
        # print(f"Current page: {current_page}")

        # Set initial screen brightness.
        deck.set_brightness(55)

        # Set initial key images.
        for key in range(deck.key_count()):
            update_key_image(deck, key, False)

        # Register callback function for when a key state changes.
        deck.set_key_callback(key_change_callback)

        # Update the UI with initial information
        info_vars["page"].set(str(current_page))
        title_label.config(text=f"Stream Deck Viewer - Page {current_page}")

    # Start the tkinter main loop
    if root:
        # Start processing the UI queue
        process_ui_queue()
        
        # Start the main loop
        root.mainloop()
