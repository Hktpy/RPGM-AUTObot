"""Main game interaction loop.

This module implements the high level runner driving the capture → perception
→ policy → action pipeline used by the autoplay system.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict
from logging.handlers import RotatingFileHandler
from typing import Dict, Tuple

import cv2

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
        snapshot_dir: str | None = None,
    ) -> None:
        self.window = GameWindow(window_name)
        self.reader = TextReader(langs=langs)
        self.analyzer = SceneAnalyzer()
        self.snapshot_dir = snapshot_dir
        self._last_snapshot_t = 0.0
        self._snapshot_idx = 0
        if self.snapshot_dir:
            os.makedirs(self.snapshot_dir, exist_ok=True)
            self._memory_path = os.path.join(self.snapshot_dir, "memory.json")
            if os.path.exists(self._memory_path):
                self.memory = Memory.load(self._memory_path)
            else:
                self.memory = Memory()
        else:
            self._memory_path = None
            self.memory = Memory()
        self.agent = Agent(self.memory, wall_hand=wall_hand)
        self.input = InputDriver()
        self.nav = Navigator(self.input, self.memory)
        self._ocr_every = 1
        self._ocr_tick = 0
        self.timings: Dict[str, float] = {}

        log_path = os.path.join(self.snapshot_dir or ".", "autoplay.log")
        handlers = [logging.StreamHandler(), RotatingFileHandler(log_path, maxBytes=10_000_000, backupCount=3)]
        logging.basicConfig(
            level=logging.INFO if debug else logging.WARNING,
            format="%(asctime)s %(levelname)s %(message)s",
            handlers=handlers,
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
    def step(self, dry_run: bool = False) -> Tuple[Perception, Dict, object]:
        """Perform a single cycle of capture → perception → policy → action."""

        t0 = time.perf_counter()
        screenshot = self.window.screenshot()
        t1 = time.perf_counter()

        dialog_present = False
        dialog_text = None
        choices: list[str] = []
        if self._ocr_tick % self._ocr_every == 0:
            ocr_start = time.perf_counter()
            dialog_present = self.reader.detect_dialog(screenshot)
            if dialog_present:
                dialog_text = self.reader.read_dialog_text(screenshot)
                if dialog_text is None:
                    h, w = screenshot.shape[:2]
                    y1 = int(h * self.reader.dialog_roi[0]) - self.reader.margin
                    y2 = int(h * self.reader.dialog_roi[1]) + self.reader.margin
                    x1 = self.reader.margin
                    x2 = w - self.reader.margin
                    roi = (max(0, x1), max(0, y1), max(0, x2 - x1), max(0, y2 - y1))
                    dialog_img = self.window.screenshot_region(roi)
                    dialog_text = self.reader.read_full(dialog_img) or None
            choices = self.reader.detect_choices(screenshot) if dialog_present else []
            t2 = time.perf_counter()
            ocr_t = t2 - ocr_start
        else:
            t2 = time.perf_counter()
            ocr_t = 0.0

        cv_start = time.perf_counter()
        perception = Perception(
            in_dialog=dialog_present,
            choices=choices,
            pos=self.analyzer.locate_player(screenshot),
            interactables=self.analyzer.find_interactables(screenshot),
            screen_hash=self.analyzer.screen_hash(screenshot),
            dialog_text=dialog_text,
        )
        cv_end = time.perf_counter()
        self.memory.update_progress(perception)

        policy_start = time.perf_counter()
        action = self.agent.next_action(perception)
        t4 = time.perf_counter()

        logging.info("Perception: %s", perception)
        logging.info("Action: %s", action)

        control_t = 0.0
        if not dry_run:
            ctrl_start = time.perf_counter()
            self._execute(action)
            control_t = time.perf_counter() - ctrl_start

        self.timings = {
            "capture": t1 - t0,
            "ocr": ocr_t,
            "cv": cv_end - cv_start,
            "policy": t4 - policy_start,
            "control": control_t,
        }
        logging.debug("Timings: %s", self.timings)
        self._ocr_tick += 1
        return perception, action, screenshot

    # ------------------------------------------------------------------
    def run(self, dry_run: bool = False) -> None:
        """Run the main loop at approximately 10–15 Hz."""

        target_dt = 1 / 12  # ≈12 Hz
        try:
            while True:
                start = time.perf_counter()
                try:
                    perception, action, screenshot = self.step(dry_run=dry_run)
                except KeyboardInterrupt:
                    logging.info("Runner stopped by user")
                    break
                except Exception:
                    logging.exception("Error during step")
                    perception, action, screenshot = None, None, None

                now = time.time()
                if (
                    self.snapshot_dir
                    and screenshot is not None
                    and now - self._last_snapshot_t >= 1.0
                ):
                    fname = os.path.join(
                        self.snapshot_dir, f"{int(now)}_{self._snapshot_idx:05d}"
                    )
                    cv2.imwrite(fname + ".png", screenshot[:, :, ::-1])
                    with open(fname + ".json", "w", encoding="utf-8") as f:
                        json.dump(asdict(perception), f)
                    if self._memory_path:
                        self.memory.save(self._memory_path)
                    self._snapshot_idx += 1
                    self._last_snapshot_t = now

                elapsed = time.perf_counter() - start
                fps = 1 / elapsed if elapsed > 0 else 0.0
                self._ocr_every = 3 if fps < 6 else 1
                logging.debug("FPS %.2f OCR every %d", fps, self._ocr_every)
                time.sleep(max(0.0, target_dt - elapsed))
        finally:
            if self._memory_path:
                self.memory.save(self._memory_path)


__all__ = ["Runner"]
