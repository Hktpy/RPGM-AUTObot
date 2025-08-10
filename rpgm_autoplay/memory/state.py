"""In-memory representations of game perception and agent memory."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import time
from typing import Deque, List, Optional, Set, Tuple


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

