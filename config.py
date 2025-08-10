from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Config:
    window_keyword: str = ""
    langs: List[str] = None
    max_fps: int = 15
    ocr_every: int = 3
    dry_run: bool = False
    log_json: bool = False
    llm_model: Optional[str] = None
    action_min_interval_ms: int = 90
    move_press_ms: int = 150
    unblock_after_s: float = 8.0
    diff_block_threshold: float = 0.995
    use_hud: bool = False
    hotkey_stop: bool = False
    mouse_mode: bool = False

    def tess_lang_str(self) -> str:
        if not self.langs:
            return "eng"
        return "+".join(["eng" if l in ("en","eng") else "jpn" if l in ("jp","jpn") else l for l in self.langs])
