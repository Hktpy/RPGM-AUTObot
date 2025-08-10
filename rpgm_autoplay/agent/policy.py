"""Decision policy for the autoplay agent.

This module contains a small deterministic policy used by the agent to
decide which high level action to perform based on the current
``Perception``.  The goal is not to be clever but to provide a reliable
baseline behaviour.
"""

from __future__ import annotations

from typing import Dict, List
import time

from ..memory.state import Memory, Perception


# Keywords that hint a menu option advances the main story.  Each set
# contains words in a different language (English, French and Japanese).
STORY_KEYWORDS: Dict[str, set[str]] = {
    "en": {
        "story",
        "quest",
        "start",
        "continue",
        "next",
        "yes",
        "ok",
        "accept",
        "enter",
        "proceed",
    },
    "fr": {
        "histoire",
        "quête",
        "commencer",
        "continuer",
        "suivant",
        "oui",
        "d'accord",
        "accepter",
        "entrer",
        "poursuivre",
    },
    "jp": {
        "ストーリー",
        "クエスト",
        "開始",
        "続ける",
        "次へ",
        "はい",
        "進む",
        "了解",
        "入る",
    },
}


class Agent:
    """Simple deterministic agent policy."""

    def __init__(self, memory: Memory) -> None:
        self.memory = memory

    # ------------------------------------------------------------------
    def _choice_score(self, text: str) -> int:
        """Return a score indicating how likely ``text`` advances story."""

        ltext = text.lower()
        score = 0
        for kw in STORY_KEYWORDS["en"]:
            if kw.lower() in ltext:
                score += 1
        for kw in STORY_KEYWORDS["fr"]:
            if kw.lower() in ltext:
                score += 1
        for kw in STORY_KEYWORDS["jp"]:
            if kw in text:
                score += 1
        return score

    def _select_choice(self, choices: List[str]) -> int:
        """Select the best choice index based on ``STORY_KEYWORDS``."""

        best_i = 0
        best_score = -1
        for i, option in enumerate(choices):
            score = self._choice_score(option)
            if score > best_score:
                best_score = score
                best_i = i
        return best_i

    # ------------------------------------------------------------------
    def next_action(self, perception: Perception) -> Dict:
        """Return the next high level action for the agent."""

        if perception.pos is not None:
            self.memory.mark_visited(perception.pos)

        # 1. Dialog currently open: advance it.
        if perception.in_dialog:
            self.memory.last_progress_t = time.time()
            return {"type": "PRESS_CONFIRM"}

        # 2. Choices available: select the one that likely continues story.
        if perception.choices:
            idx = self._select_choice(perception.choices)
            self.memory.last_progress_t = time.time()
            return {"type": "SELECT_CHOICE", "index": idx}

        # 3. Nearby unused interactable.
        if perception.pos is not None:
            px, py = perception.pos
            for x, y, t in perception.interactables:
                if (x, y, t) in self.memory.used_interactables:
                    continue
                if abs(px - x) + abs(py - y) <= 1:
                    self.memory.mark_used_interactable(x, y, t)
                    return {
                        "type": "MOVE_AND_INTERACT",
                        "target": (x, y, t),
                    }

        # 4. Stuck detection – perform an unstuck sequence.
        if self.memory.is_stuck():
            return {
                "type": "UNSTUCK_SEQ",
                "sequence": [
                    "MOVE_UP",
                    "MOVE_RIGHT",
                    "MOVE_DOWN",
                    "MOVE_LEFT",
                ],
            }

        # 5. Default exploration behaviour using wall following.
        return {"type": "EXPLORE_WALLFOLLOW", "hand": "right"}


__all__ = ["Agent", "STORY_KEYWORDS"]

