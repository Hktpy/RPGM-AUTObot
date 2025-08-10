"""Main game interaction loop.

This module implements the high level runner driving the capture → perception
→ policy → action pipeline used by the autoplay system.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Tuple

from .capture.window_manager import GameWindow
from .ocr.text_reader import TextReader
from .cv.scene_analyzer import SceneAnalyzer
from .memory.state import Memory, Perception
from .agent.policy import Agent
from .control.input_driver import InputDriver
from .control.navigation import Navigator


class Runner:
    """Drive the main capture/decision/action loop."""

    def __init__(
        self,
        window_name: str = "rmmz-game",
        *,
        langs: str = "eng+jpn",
        wall_hand: str = "right",
        debug: bool = False,
    ) -> None:
        self.window = GameWindow(window_name)
        self.reader = TextReader(langs=langs)
        self.analyzer = SceneAnalyzer()
        self.memory = Memory()
        self.agent = Agent(self.memory, wall_hand=wall_hand)
        self.input = InputDriver()
        self.nav = Navigator(self.input, self.memory)

        logging.basicConfig(
            level=logging.INFO if debug else logging.WARNING,
            format="%(asctime)s %(levelname)s %(message)s",
        )

    # ------------------------------------------------------------------
    def _execute(self, action: Dict) -> None:
        """Execute ``action`` using the input driver and navigator."""

        kind = action.get("type")
        if kind == "PRESS_CONFIRM":
            self.input.confirm()
        elif kind == "SELECT_CHOICE":
            idx = int(action.get("index", 0))
            for _ in range(idx):
                self.input.press("DOWN")
            self.input.confirm()
        elif kind == "MOVE_AND_INTERACT":
            target = action.get("target")
            if target is not None:
                self.nav.move_towards(target)
                self.input.interact()
        elif kind == "UNSTUCK_SEQ":
            seq = action.get("sequence", [])
            self.nav.execute_unstuck(list(seq))
        elif kind == "EXPLORE_WALLFOLLOW":
            self.nav.wall_follow(action.get("hand", "right"))
        else:
            logging.warning("Unknown action type: %s", kind)

    # ------------------------------------------------------------------
    def step(self, dry_run: bool = False) -> Tuple[Perception, Dict]:
        """Perform a single cycle of capture → perception → policy → action."""

        screenshot = self.window.screenshot()
        perception = Perception(
            in_dialog=self.reader.detect_dialog(screenshot),
            choices=self.reader.detect_choices(screenshot),
            pos=self.analyzer.locate_player(screenshot),
            interactables=self.analyzer.find_interactables(screenshot),
            screen_hash=self.analyzer.screen_hash(screenshot),
        )
        self.memory.seen_hashes.append(perception.screen_hash)

        action = self.agent.next_action(perception)
        logging.info("Perception: %s", perception)
        logging.info("Action: %s", action)

        if not dry_run:
            self._execute(action)
        return perception, action

    # ------------------------------------------------------------------
    def run(self, dry_run: bool = False) -> None:
        """Run the main loop at approximately 10–15 Hz."""

        target_dt = 1 / 12  # ≈12 Hz
        while True:
            start = time.perf_counter()
            try:
                self.step(dry_run=dry_run)
            except KeyboardInterrupt:
                logging.info("Runner stopped by user")
                break
            except Exception:
                logging.exception("Error during step")
            elapsed = time.perf_counter() - start
            time.sleep(max(0.0, target_dt - elapsed))


__all__ = ["Runner"]
