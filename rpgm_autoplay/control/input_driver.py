"""Keyboard input driver for RPG Maker automation.

This module provides a small wrapper around :mod:`pynput` to send
keyboard events to the operating system.  It is primarily intended for
macOS on Apple Silicon but should function on other platforms supported
by ``pynput``.
"""

from __future__ import annotations

import random
import time
from typing import Dict, Mapping, Optional

from pynput.keyboard import Controller, Key

# Default mapping from logical names to physical keys.  Consumers may provide
# a custom map when instantiating :class:`InputDriver` to override any of
# these values.
DEFAULT_KEYMAP: Dict[str, object] = {
    "UP": Key.up,
    "DOWN": Key.down,
    "LEFT": Key.left,
    "RIGHT": Key.right,
    "Z": "z",
    "ENTER": Key.enter,
    "SHIFT": Key.shift,
    "SPACE": Key.space,
}


class InputDriver:
    """Send keyboard input to the game window.

    Parameters
    ----------
    keymap:
        Optional custom key mapping.  Keys are case-insensitive and override
        entries in :data:`DEFAULT_KEYMAP`.
    delay_range:
        Minimum and maximum delay (in seconds) inserted between key events to
        avoid spamming the input system.  Defaults to ``(0.09, 0.12)`` which is
        roughly 90–120 ms.
    """

    def __init__(
        self,
        keymap: Optional[Mapping[str, object]] = None,
        delay_range: tuple[float, float] = (0.09, 0.12),
    ) -> None:
        self.keyboard = Controller()
        self.keymap: Dict[str, object] = dict(DEFAULT_KEYMAP)
        if keymap:
            # Normalize keys to uppercase for case-insensitive lookups.
            self.keymap.update({k.upper(): v for k, v in keymap.items()})
        self.delay_range = delay_range

    # ------------------------------------------------------------------
    # Internal utilities
    def _sleep(self) -> None:
        """Sleep for a short random interval to prevent key spam."""

        time.sleep(random.uniform(*self.delay_range))

    # ------------------------------------------------------------------
    # Public API
    def press(self, key: str) -> None:
        """Press and release ``key`` once."""

        mapped_key = self.keymap.get(key.upper(), key)
        self.keyboard.press(mapped_key)
        self._sleep()
        self.keyboard.release(mapped_key)
        self._sleep()

    def hold(self, key: str, dur: float) -> None:
        """Hold ``key`` for ``dur`` seconds."""

        mapped_key = self.keymap.get(key.upper(), key)
        self.keyboard.press(mapped_key)
        time.sleep(dur)
        self.keyboard.release(mapped_key)
        self._sleep()

    def interact(self) -> None:
        """Trigger the game's interaction key (default ``Z``)."""

        # Prefer "Z" but fall back to "ENTER" if absent.
        key = "Z" if "Z" in self.keymap else "ENTER"
        self.press(key)

    def confirm(self) -> None:
        """Advance dialogue or confirm selections (default ``ENTER``)."""

        key = "ENTER" if "ENTER" in self.keymap else "Z"
        self.press(key)


__all__ = ["InputDriver", "DEFAULT_KEYMAP"]

