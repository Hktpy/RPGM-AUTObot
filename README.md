# RPGM-AUTObot

Automated helper for RPG Maker style games on macOS. The project provides
basic screen capture, OCR and simple heuristics to navigate a game window.

## Requirements

The code targets Python 3.9+ on macOS.  For a minimal setup on an Apple
Silicon (M1) machine with 8 GB RAM:

```bash
python -m pip install --upgrade pip
python -m pip install numpy pillow mss pynput pytesseract opencv-python
# Optional for the HUD overlay
python -m pip install PySide6
```

Tesseract itself must be installed separately, e.g. via Homebrew:

```bash
brew install tesseract
```

## Running

Run the main program in dry‑run mode to verify the installation:

```bash
python -m main --dry-run
```

Use `--window` to capture a specific game window or `--debug-windows` to list
available windows.  When `--dry-run` is omitted the bot will attempt to send
keyboard/mouse actions to the focused window.

## Testing

The project currently has no automated test-suite.  To ensure the code is
syntactically correct you can compile all modules:

```bash
python -m compileall RPGM_AUTObot
```

## License

MIT
