"""In-memory representations of game perception and agent memory."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
import os
import time
from typing import Deque, Iterable, List, Optional, Set, Tuple


@dataclass
class Perception:
    """High-level information perceived from the current game frame."""

    in_dialog: bool
    choices: List[str]
    pos: Optional[Tuple[int, int]]
    interactables: List[Tuple[int, int, str]]
    screen_hash: Optional[int]


class Memory:
    """Persistent memory used by the autoplay agent."""

    visited_cells: Set[Tuple[int, int]]
    used_interactables: Set[Tuple[int, int, str]]
    last_positions: Deque[Tuple[int, int]]
    last_progress_t: float
    seen_hashes: Deque[int]

    def __init__(self) -> None:
        self.visited_cells = set()
        self.used_interactables = set()
        self.last_positions = deque(maxlen=30)
        self.last_progress_t = time.time()
        self.seen_hashes = deque(maxlen=50)

    def mark_visited(self, pos: Tuple[int, int]) -> None:
        """Record that a map cell has been visited."""

        if pos not in self.visited_cells:
            self.visited_cells.add(pos)
            self.last_progress_t = time.time()
        self.last_positions.append(pos)

    def mark_used_interactable(self, x: int, y: int, t: str) -> None:
        """Record that an interactable object has been used."""

        item = (x, y, t)
        if item not in self.used_interactables:
            self.used_interactables.add(item)
            self.last_progress_t = time.time()

    def is_stuck(self) -> bool:
        """Return True if recent movement stayed within a single cell."""

        if len(self.last_positions) < self.last_positions.maxlen:
            return False
        xs = [p[0] for p in self.last_positions]
        ys = [p[1] for p in self.last_positions]
        return max(xs) - min(xs) <= 1 and max(ys) - min(ys) <= 1

    def no_progress(self, timeout_s: int) -> bool:
        """Return True if no progress was made for ``timeout_s`` seconds."""

        return time.time() - self.last_progress_t > timeout_s

    # ------------------------------------------------------------------
    def save(self, path: str) -> None:
        """Persist memory state to ``path`` in JSON format."""

        if dirpath := os.path.dirname(path):
            os.makedirs(dirpath, exist_ok=True)

        data = {
            "visited_cells": _compact_cells(self.visited_cells),
            "used_interactables": list(self.used_interactables),
            "last_positions": list(self.last_positions),
            "last_progress_t": self.last_progress_t,
            "seen_hashes": list(self.seen_hashes),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: str) -> "Memory":
        """Load memory state from ``path``."""

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        mem = cls()
        mem.visited_cells = _expand_cells(data.get("visited_cells", []))
        mem.used_interactables = {tuple(x) for x in data.get("used_interactables", [])}
        mem.last_positions = deque((tuple(p) for p in data.get("last_positions", [])), maxlen=30)
        mem.last_progress_t = data.get("last_progress_t", time.time())
        mem.seen_hashes = deque(data.get("seen_hashes", []), maxlen=50)
        return mem


# ----------------------------------------------------------------------
def _pack_cell(x: int, y: int) -> int:
    """Pack ``(x, y)`` into a single integer."""

    return ((x & 0xFFFF) << 16) | (y & 0xFFFF)


def _unpack_cell(v: int) -> Tuple[int, int]:
    """Unpack a packed cell integer into ``(x, y)``."""

    x = (v >> 16) & 0xFFFF
    y = v & 0xFFFF
    if x >= 0x8000:
        x -= 0x10000
    if y >= 0x8000:
        y -= 0x10000
    return x, y


def _compact_cells(cells: Iterable[Tuple[int, int]]) -> List[int]:
    """Return a compact list representation of ``cells``."""

    return sorted(_pack_cell(x, y) for x, y in cells)


def _expand_cells(data: Iterable[int]) -> Set[Tuple[int, int]]:
    """Expand a compacted cell list back into coordinate tuples."""

    return {_unpack_cell(v) for v in data}

