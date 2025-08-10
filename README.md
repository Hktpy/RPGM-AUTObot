# rpgm_autoplay

Prototype skeleton for an RPG Maker autoplay tool.

## Requirements

- Python 3.11
- macOS ARM64

### macOS permissions

The autoplay loop synthesises keyboard input and captures the game window. On
macOS, the host process must be granted **Accessibility** rights (for input) and
**Screen Recording** permission (for capture). These can be enabled in
``System Settings → Privacy & Security``.

TODO: Expand documentation with setup, usage, and design details.
