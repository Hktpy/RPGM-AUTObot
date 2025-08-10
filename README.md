# rpgm_autoplay

Prototype skeleton for an RPG Maker autoplay tool.

## Requirements

- Python 3.11
- macOS ARM64

## macOS permissions

The bot needs access to capture the screen and send inputs. On macOS, grant the
terminal (or Python interpreter) the following rights in
**System Settings ➜ Privacy & Security**:

- **Accessibility** – allows keyboard and mouse control.
- **Screen Recording** – allows screen capture for OCR.

Restart the application after changing permissions.

## Manual testing

For manual smoke tests verify behaviour in these scenarios:

- Straight corridors
- Doors
- Angled corridors

These ensure movement, door interaction and turns work correctly.

TODO: Expand documentation with setup, usage, and design details.
