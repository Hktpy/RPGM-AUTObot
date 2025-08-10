"""OCR utilities for reading text from the game screen.

This module wraps common OCR operations used by the autoplay system.  It
provides a small :class:`TextReader` helper which performs a few image
pre-processing steps before delegating to Tesseract.
"""

from __future__ import annotations

import re
from typing import List, Tuple

import cv2
import numpy as np
import pytesseract


class TextReader:
    """Utility class for extracting text from screen captures.

    Parameters
    ----------
    langs:
        Languages to pass to Tesseract.  The default covers English and
        Japanese which are common in RPGM games.
    dialog_roi:
        Tuple of floats in ``[0, 1]`` defining the vertical region of
        interest used when searching for dialogue text.  The default
        targets the bottom portion of the screen where RPGM usually
        renders dialogue boxes.
    margin:
        Extra pixels cropped from each side of the region of interest to
        avoid borders and reduce false positives.
    thresh_blocksize / thresh_C:
        Parameters for ``cv2.adaptiveThreshold`` controlling the
        binarisation stage.  Exposed for experimentation in order to
        balance accuracy and false positives.
    min_choice_lines:
        Minimum number of textual lines required for a set of choices to
        be considered valid.
    choice_line_gap:
        Minimum vertical separation (in pixels) between lines when
        detecting choices.
    dialog_min_chars:
        Minimum number of alphanumeric characters that must be detected
        in the dialogue region for ``detect_dialog`` to return ``True``.
    """

    def __init__(
        self,
        langs: str = "eng+jpn",
        dialog_roi: Tuple[float, float] = (0.6, 1.0),
        margin: int = 10,
        thresh_blocksize: int = 31,
        thresh_C: int = 3,
        min_choice_lines: int = 2,
        choice_line_gap: int = 10,
        dialog_min_chars: int = 10,
    ) -> None:
        self.langs = langs
        self.dialog_roi = dialog_roi
        self.margin = margin
        # ``adaptiveThreshold`` requires an odd block size.
        self.thresh_blocksize = int(thresh_blocksize) | 1
        self.thresh_C = thresh_C
        self.min_choice_lines = min_choice_lines
        self.choice_line_gap = choice_line_gap
        self.dialog_min_chars = dialog_min_chars

    # ------------------------------------------------------------------
    # Internal helpers
    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        """Convert to grayscale and apply adaptive thresholding."""

        if img is None:
            raise ValueError("img is None")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            self.thresh_blocksize,
            self.thresh_C,
        )
        return binary

    def _ocr(self, img: np.ndarray, psm: int = 6) -> str:
        """Run Tesseract on ``img`` and return the stripped text."""

        config = f"-l {self.langs} --psm {psm}"
        return pytesseract.image_to_string(img, config=config).strip()

    # ------------------------------------------------------------------
    # Public API
    def detect_dialog(self, img: np.ndarray) -> bool:
        """Return ``True`` when a dialogue box is detected.

        The method crops the bottom part of the screen according to
        ``dialog_roi`` and runs OCR on the result.  A dialogue is
        considered present when a minimum amount of textual characters is
        detected.
        """

        h, w = img.shape[:2]
        y1 = int(h * self.dialog_roi[0]) - self.margin
        y2 = int(h * self.dialog_roi[1]) + self.margin
        x1 = self.margin
        x2 = w - self.margin
        roi = img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]

        pre = self._preprocess(roi)
        text = self._ocr(pre)
        cleaned = re.sub(r"[^0-9A-Za-z\u3040-\u30ff\u4e00-\u9fff]", "", text)
        return len(cleaned) >= self.dialog_min_chars

    def read_dialog_text(self, img: np.ndarray) -> str:
        """Return OCR text from the dialogue region."""

        h, w = img.shape[:2]
        y1 = int(h * self.dialog_roi[0]) - self.margin
        y2 = int(h * self.dialog_roi[1]) + self.margin
        x1 = self.margin
        x2 = w - self.margin
        roi = img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        pre = self._preprocess(roi)
        return self._ocr(pre)

    def detect_choices(self, img: np.ndarray) -> List[str]:
        """Detect a list of choice strings from the image.

        This is a lightweight heuristic based on line separation.  When
        fewer than ``min_choice_lines`` lines are detected an empty list
        is returned.
        """

        pre = self._preprocess(img)
        data = pytesseract.image_to_data(
            pre,
            output_type=pytesseract.Output.DICT,
            config=f"-l {self.langs} --psm 6",
        )

        lines = {}
        for i, txt in enumerate(data["text"]):
            txt = txt.strip()
            if not txt:
                continue
            line_no = data["line_num"][i]
            top = data["top"][i]
            entry = lines.setdefault(line_no, {"text": [], "top": top})
            entry["text"].append(txt)

        sorted_lines = []
        for _, info in sorted(lines.items(), key=lambda kv: kv[1]["top"]):
            line_text = " ".join(info["text"]).strip()
            if line_text:
                sorted_lines.append((info["top"], line_text))

        # Merge lines that are too close vertically and collect final choices
        choices: List[str] = []
        prev_top: int | None = None
        for top, line_text in sorted_lines:
            if prev_top is not None and abs(top - prev_top) <= self.choice_line_gap:
                choices[-1] = f"{choices[-1]} {line_text}".strip()
            else:
                choices.append(line_text)
            prev_top = top

        # Basic sanity filter to avoid false positives
        cleaned_choices = [c for c in choices if len(re.sub(r"\W", "", c)) >= 2]
        if len(cleaned_choices) >= self.min_choice_lines:
            return cleaned_choices
        return []

    def read_full(self, img: np.ndarray) -> str:
        """Read text from the entire image."""

        pre = self._preprocess(img)
        return self._ocr(pre)
