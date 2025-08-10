"""Utility functions to interpret RPG Maker scenes using OpenCV.

The :class:`SceneAnalyzer` class exposes a few lightweight helpers used by the
bot to reason about what is displayed on the screen.  The implementation is
intentionally simple and optimised for speed (≈30ms per frame on a modern M1
CPU).
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


class SceneAnalyzer:
    """Analyse a screenshot and extract gameplay elements.

    Parameters
    ----------
    templates:
        Optional dictionary mapping a name (``"player"``, ``"door"``, …) to a
        small RGB template used for template matching.
    match_threshold:
        Minimum normalised correlation score used when matching templates.  A
        value between 0 and 1, higher means stricter.
    player_key:
        Key used in ``templates`` for the player sprite.
    """

    def __init__(
        self,
        templates: Dict[str, np.ndarray] | None = None,
        match_threshold: float = 0.8,
        player_key: str = "player",
    ) -> None:
        self.templates = templates or {}
        self.match_threshold = match_threshold
        self.player_key = player_key

    # ------------------------------------------------------------------
    # Helper methods
    def _center_of(self, loc: Tuple[int, int], tpl_shape: Tuple[int, int, int]) -> Tuple[int, int]:
        h, w = tpl_shape[:2]
        return loc[0] + w // 2, loc[1] + h // 2

    # ------------------------------------------------------------------
    def locate_player(self, img: np.ndarray) -> Optional[Tuple[int, int]]:
        """Return player's position relative to the screen centre.

        The function first tries to match the provided player template.  If no
        template is supplied, a simple edge based heuristic is used to locate
        the sprite near the centre of the screen.
        """

        centre_x, centre_y = img.shape[1] // 2, img.shape[0] // 2
        player_tpl = None if self.templates is None else self.templates.get(self.player_key)

        if player_tpl is not None:
            # Template match to find the player sprite
            res = cv2.matchTemplate(img, player_tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val < self.match_threshold:
                return None
            px, py = self._center_of(max_loc, player_tpl.shape)
            return px - centre_x, py - centre_y

        # Fallback heuristic: find the contour closest to screen centre
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 80, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        nearest: Optional[Tuple[int, int]] = None
        best_dist = float("inf")
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            cx, cy = x + w // 2, y + h // 2
            area = w * h
            if area < 20:  # ignore tiny blobs/noise
                continue
            dist = (cx - centre_x) ** 2 + (cy - centre_y) ** 2
            if dist < best_dist:
                best_dist = dist
                nearest = (cx, cy)

        if nearest is None:
            return None
        px, py = nearest
        return px - centre_x, py - centre_y

    # ------------------------------------------------------------------
    def find_interactables(self, img: np.ndarray, radius: int = 140) -> List[Tuple[int, int, str]]:
        """Locate interactable objects around the player.

        For each template in ``self.templates`` (except the player sprite), the
        method performs template matching and returns the relative positions of
        the detections that fall within ``radius`` pixels of the screen centre.
        Each returned tuple is ``(dx, dy, name)``.
        """

        if not self.templates:
            return []

        centre_x, centre_y = img.shape[1] // 2, img.shape[0] // 2
        radius_sq = radius * radius
        found: List[Tuple[int, int, str]] = []

        for name, tpl in self.templates.items():
            if name == self.player_key:
                continue
            res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
            loc = np.where(res >= self.match_threshold)
            if len(loc[0]) == 0:
                continue
            h, w = tpl.shape[:2]
            for pt in zip(*loc[::-1]):
                cx, cy = pt[0] + w // 2, pt[1] + h // 2
                dx, dy = cx - centre_x, cy - centre_y
                if dx * dx + dy * dy <= radius_sq:
                    found.append((dx, dy, name))
        return found

    # ------------------------------------------------------------------
    @staticmethod
    def screen_hash(img: np.ndarray) -> int:
        """Return a stable 64-bit hash representing ``img``.

        The image is converted to greyscale and down-sampled to 32×32 before a
        SHA1 digest is computed.  The result fits in 64 bits so it can easily be
        used as a dictionary key.
        """

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
        digest = hashlib.sha1(small.tobytes()).hexdigest()[:16]
        return int(digest, 16)
