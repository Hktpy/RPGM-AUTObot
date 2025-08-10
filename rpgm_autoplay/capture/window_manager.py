"""Window management and capture utilities.

This module provides a :class:`GameWindow` helper that locates a game window
by its title and captures screenshots from it.  The implementation relies on
`pygetwindow` to query window geometry and `mss` to grab the pixels inside the
window.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


class WindowNotFoundError(RuntimeError):
    """Raised when a window cannot be located."""


@dataclass
class GameWindow:
    """Utility class for locating and capturing a game window.

    Parameters
    ----------
    name:
        Title of the window to capture.  The default matches the RPG Maker MZ
        window title.
    """

    name: str = "rmmz-game"

    def __post_init__(self) -> None:  # pragma: no cover - simple attribute init
        self._bbox: Tuple[int, int, int, int] | None = None

    # ------------------------------------------------------------------
    # Window discovery
    # ------------------------------------------------------------------
    def find(self) -> Tuple[int, int, int, int]:
        """Locate the window on the desktop.

        Returns
        -------
        tuple
            ``(x, y, width, height)`` of the window in absolute screen
            coordinates.

        Raises
        ------
        WindowNotFoundError
            If no window with the requested title exists.
        RuntimeError
            If ``pygetwindow`` is not available.
        """

        try:  # Import lazily so that the module can be imported without deps.
            import pygetwindow as gw
        except Exception as exc:  # pragma: no cover - dependency error
            raise RuntimeError("pygetwindow is required to locate windows") from exc

        matches = [w for w in gw.getAllWindows() if w.title == self.name]
        if not matches:
            raise WindowNotFoundError(f"Window {self.name!r} not found")

        win = matches[0]
        self._bbox = (int(win.left), int(win.top), int(win.width), int(win.height))
        return self._bbox

    # ------------------------------------------------------------------
    def bbox(self) -> Tuple[int, int, int, int]:
        """Return the window bounding box in absolute screen coordinates."""

        if self._bbox is None:
            return self.find()
        return self._bbox

    # ------------------------------------------------------------------
    def screenshot(self):  # -> np.ndarray
        """Capture a screenshot of the window as an RGB ``numpy`` array."""

        try:
            import numpy as np
            import mss
        except Exception as exc:  # pragma: no cover - dependency error
            raise RuntimeError("mss and numpy are required for screenshots") from exc

        x, y, w, h = self.bbox()
        with mss.mss() as sct:
            img = sct.grab({"left": x, "top": y, "width": w, "height": h})

        arr = np.array(img, dtype=np.uint8)
        # Convert from BGRA to RGB
        rgb = arr[:, :, :3][:, :, ::-1]
        return rgb


__all__ = ["GameWindow", "WindowNotFoundError"]

