"""High-level navigation helpers.

This module exposes :class:`Navigator` which provides a couple of simple
movement primitives used by the agent.  The routines favour very small
movement steps in order to avoid blocking the game logic and to re-evaluate
perception after each action.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

from .input_driver import InputDriver
from ..memory.state import Memory

# Default duration (in seconds) for a single movement step.  The value is kept
# short so that higher level logic may intervene between steps if needed.
STEP_DURATION = 0.15


class Navigator:
    """Collection of small navigation utilities.

    Parameters
    ----------
    input:
        Object responsible for sending key presses to the game.
    memory:
        Shared memory instance tracking visited cells and recent positions.
    """

    def __init__(self, input: InputDriver, memory: Memory) -> None:
        self.input = input
        self.memory = memory

    # ------------------------------------------------------------------
    def _current_pos(self) -> Tuple[int, int] | None:
        """Return the most recent known position of the player."""

        if self.memory.last_positions:
            return self.memory.last_positions[-1]
        return None

    # ------------------------------------------------------------------
    def move_towards(self, target: Tuple[int, int, str]) -> None:
        """Move step by step toward ``target``.

        The function only performs one-tile steps so that the caller may
        re-evaluate perception between moves.  The ``Memory`` is updated with
        the estimated new position after each step.
        """

        tx, ty, _ = target
        # Limit number of iterations to avoid infinite loops in edge cases.
        for _ in range(100):
            pos = self._current_pos()
            if pos is None:
                return
            px, py = pos
            if (px, py) == (tx, ty):
                return
            if px < tx:
                self.input.hold("RIGHT", STEP_DURATION)
                self.memory.mark_visited((px + 1, py))
            elif px > tx:
                self.input.hold("LEFT", STEP_DURATION)
                self.memory.mark_visited((px - 1, py))
            elif py < ty:
                self.input.hold("DOWN", STEP_DURATION)
                self.memory.mark_visited((px, py + 1))
            elif py > ty:
                self.input.hold("UP", STEP_DURATION)
                self.memory.mark_visited((px, py - 1))

    # ------------------------------------------------------------------
    def wall_follow(self, hand: str = "right") -> None:
        """Perform a simple wall following step.

        ``hand`` chooses between a right-hand or left-hand rule when selecting
        the order of directions to attempt.  ``UP`` is always evaluated first to
        keep a deterministic bias which makes the resulting exploration easier
        to reason about.
        """

        pos = self._current_pos()
        if pos is None:
            return
        px, py = pos

        if hand.lower() == "left":
            order: Iterable[str] = ("UP", "LEFT", "DOWN", "RIGHT")
        else:
            order = ("UP", "RIGHT", "DOWN", "LEFT")

        deltas: Dict[str, Tuple[int, int]] = {
            "UP": (0, -1),
            "DOWN": (0, 1),
            "LEFT": (-1, 0),
            "RIGHT": (1, 0),
        }

        for direction in order:
            dx, dy = deltas[direction]
            nxt = (px + dx, py + dy)
            if nxt not in self.memory.visited_cells:
                self.input.hold(direction, STEP_DURATION)
                self.memory.mark_visited(nxt)
                return

        # Fallback: move in the first direction even if already visited.
        first = next(iter(order))
        dx, dy = deltas[first]
        self.input.hold(first, STEP_DURATION)
        self.memory.mark_visited((px + dx, py + dy))

    # ------------------------------------------------------------------
    def execute_unstuck(self, sequence: List[str]) -> None:
        """Execute a predefined sequence of short key presses."""

        for action in sequence:
            key = action.upper()
            if key in {"UP", "DOWN", "LEFT", "RIGHT"}:
                self.input.hold(key, STEP_DURATION)
            elif key == "INTERACT":
                self.input.interact()
            else:
                # Fall back to a simple key press for any other keyword.
                self.input.press(key)


__all__ = ["Navigator"]

