# StreamDeck Controller

Eine Python-Anwendung zur Steuerung deines Elgato Stream Deck mit konfigurierbaren Hotkeys und mehreren Seiten.

Experimental-Branch:
- Ergänzung eines GUIs

## Funktionen

- Konfigurierbare Tasten mit Hotkey-Funktionalität
- Unterstützung für mehrere Seiten (Pages) mit unterschiedlichen Layouts
- Anpassbare Grafiken für jede Taste
- Page-Wechsel-Funktion
- Exit-Funktion mit eleganter Abschaltung

## Voraussetzungen

- Python 3.6 oder höher
- Elgato Stream Deck
- Installierte Python-Pakete (siehe Installation)

## Installation

1. Klone dieses Repository oder lade die Dateien herunter
2. Installiere die benötigten Pakete:

```bash
pip install pillow streamdeck pyautogui
```

## Dateistruktur

- `streamd4.py` - Hauptprogramm
- `Daten/button_config.json` - Konfigurationsdatei für die Tasten und Seiten
- `Daten/KEY1-1.png` bis `KEYn-m.png` - Grafiken für die Tasten (wobei n die Seitennummer und m die Tastennummer ist)
- `Daten/KEY-pressed.png` - Grafik für gedrückte Tasten

## Konfigurationsdatei

Die Konfigurationsdatei `button_config.json` hat folgendes Format:

```json
{
  "current_page": 1,
  "total_pages": 3,
  "pages": [
    {
      "page_number": 1,
      "buttons": [
        {
          "index": 1,
          "type": "action exit",
          "keys": []
        },
        {
          "index": 2,
          "type": "hotkey",
          "keys": ["ctrl", "shift", "alt", "2"]
        },
        ...
        {
          "index": 15,
          "type": "action page",
          "next_page": 2
        }
      ]
    },
    ...
  ]
}
```

### Konfigurationsfelder

- `current_page`: Startet auf dieser Seite
- `total_pages`: Gesamtanzahl der verfügbaren Seiten
- `pages`: Array mit Seitendefinitionen
  - `page_number`: Seitennummer (beginnend bei 1)
  - `buttons`: Array mit Tastendefinitionen
    - `index`: Tastenindex (1-32)
    - `type`: Tastentyp (siehe unten)
    - `keys`: Array mit Tasten für Hotkey-Aktionen
    - `next_page`: Zielseite für Seitenwechsel-Aktionen

### Tastentypen

- `hotkey`: Sendet Tastenkombination
- `action exit`: Beendet das Programm
- `action page`: Wechselt zur angegebenen Seite

## Grafiken

Die Grafiken für die Tasten sollten folgendes Format haben:

- Dateiname: `KEY{page}-{key}.png`
  - `{page}` ist die Seitennummer (1, 2, 3, ...)
  - `{key}` ist die Tastennummer (1, 2, 3, ..., 32)
- Für gedrückte Tasten: `KEY-pressed.png`
- Größe: Es wird empfohlen, Bilder mit einer Auflösung von 72x72 Pixeln zu verwenden
- Format: PNG (transparentes PNG wird unterstützt)

Beispiele:
- `KEY1-1.png` - Taste 1 auf Seite 1
- `KEY2-15.png` - Taste 15 auf Seite 2

Wenn keine Grafikdatei für eine Taste existiert, wird diese schwarz angezeigt.

## Verwendung

Starte das Programm mit:

```bash
python streamd4.py
```

## Tastenbelegung anpassen

Um die Tastenbelegung anzupassen:

1. Bearbeite die `button_config.json` Datei
2. Ändere die Tastendefinitionen wie gewünscht
3. Füge neue Seiten hinzu, indem du neue Einträge im `pages`-Array erstellst
4. Stelle entsprechende Grafikdateien im richtigen Format bereit

## Fehlerbehebung

Wenn keine StreamDeck erkannt wird:
- Überprüfe die USB-Verbindung
- Stelle sicher, dass keine andere Anwendung das StreamDeck verwendet

Bei fehlenden Grafiken:
- Überprüfe, ob die Dateien im richtigen Format und an der richtigen Stelle sind
- Tastennamen sollten dem Muster `KEY{page}-{key}.png` entsprechen

## Lizenz

Dieses Projekt verwendet die Python StreamDeck Library, die unter der MIT-Lizenz veröffentlicht wurde. 
