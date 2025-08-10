import argparse, time
from typing import List
import numpy as np
import cv2

from config import Config
from capture import ScreenCapture, MacWindowCapture, find_window_by_keyword, debug_windows, get_window_info
from ocr import extract_dialog_and_menu
from perception import update_blocked_seconds, map_hint
from policy import decide_action
from actions import ActionSender
from unblock import routine
from utils import RateLimiter, log_line

try:
    from overlay import HUD
    HAVE_HUD = True
except Exception:
    HAVE_HUD = False
    HUD = None

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--window", type=str, default="", help="Sous-chaîne owner/titre (ex. 'nwjs')")
    p.add_argument("--window-id", type=int, default=0, help="ID de fenêtre macOS (Quartz)")
    p.add_argument("--debug-windows", action="store_true", help="Liste les fenêtres et quitte")
    p.add_argument("--lang", type=str, default="jp,en")
    p.add_argument("--max-fps", type=int, default=15)
    p.add_argument("--ocr-every", type=int, default=3)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--mouse-mode", action="store_true", help="Déplacements via clic souris dans la fenêtre")
    p.add_argument("--llm-model", type=str, default=None)
    p.add_argument("--log-json", action="store_true")
    p.add_argument("--hud", action="store_true", help="Afficher le HUD")
    p.add_argument("--hotkey-stop", action="store_true", help="(placeholder)")
    return p.parse_args()

def main():
    args = parse_args()

    if args.debug_windows:
        for w in debug_windows():
            print(f"ID={w['id']:>7}  PID={w['pid']:>6}  OWNER='{w['owner']}'  NAME='{w['name']}'  BBOX={w['bbox']}")
        return

    cfg = Config(
        window_keyword=args.window,
        langs=[s.strip() for s in args.lang.split(",") if s.strip()],
        max_fps=max(5, min(25, args.max_fps)),
        ocr_every=max(1, min(10, args.ocr_every)),
        dry_run=bool(args.dry_run),
        log_json=bool(args.log_json),
        llm_model=args.llm_model,
        use_hud=bool(args.hud),
        hotkey_stop=bool(args.hotkey_stop),
        mouse_mode=bool(args.mouse_mode),
    )

    cap = None
    used = {}
    pid_ref = 0
    bbox_ref = (0,0,0,0)

    if args.window_id:
        cap = MacWindowCapture(args.window_id)
        info = get_window_info(args.window_id)
        if info:
            pid_ref = info["pid"]; bbox_ref = info["bbox"]
        used = {"mode": "window-id", "window_id": args.window_id, "pid": pid_ref, "bbox": bbox_ref}
    else:
        found = find_window_by_keyword(cfg.window_keyword) if cfg.window_keyword else None
        if found:
            wid, bbox, pid = found
            cap = MacWindowCapture(wid)
            pid_ref, bbox_ref = pid, bbox
            used = {"mode": "keyword", "window_id": wid, "pid": pid, "bbox": bbox}
        else:
            cap = ScreenCapture(bbox=None)
            used = {"mode": "fullscreen", "window_id": None, "pid": None, "bbox": None}

    sender = ActionSender(
        move_press_ms=cfg.move_press_ms,
        mouse_mode=cfg.mouse_mode,
        pid_getter=lambda: pid_ref,
        bbox_getter=lambda: (get_window_info(args.window_id)["bbox"] if args.window_id and get_window_info(args.window_id) else bbox_ref)
    )
    limiter = RateLimiter(cfg.action_min_interval_ms)
    unb = routine()

    prev = None
    ref_shape = None
    blocked_s = 0.0
    last_actions: List[str] = []

    frame_i = 0
    t_prev = time.perf_counter()
    target_dt = 1.0 / cfg.max_fps

    log_line({"event": "start", "capture": used, "langs": "+".join(cfg.langs or ["eng"])}, cfg.log_json)

    app = None
    hud = None
    if cfg.use_hud and HAVE_HUD:
        from PySide6 import QtWidgets
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        hud = HUD(frameless=True)
        if bbox_ref and bbox_ref[2] > 0:
            hud.move_to_bbox(bbox_ref)
        hud.show()

    while True:
        t0 = time.perf_counter()
        frame = cap.grab()
        if ref_shape is None:
            ref_shape = frame.shape[:2]
        elif frame.shape[:2] != ref_shape:
            frame = cv2.resize(frame, (ref_shape[1], ref_shape[0]), interpolation=cv2.INTER_AREA)

        frame_i += 1
        if prev is None:
            prev = frame.copy()

        dt = t0 - t_prev
        t_prev = t0

        blocked_s = update_blocked_seconds(prev, frame, blocked_s, dt, 0.995)
        hint = map_hint(frame)

        dialog_text, menu_options, boxes = (None, [], [])
        if frame_i % cfg.ocr_every == 0:
            dialog_text, menu_options, boxes = extract_dialog_and_menu(frame, cfg.tess_lang_str())

        state = {
            "dialog_text": dialog_text,
            "menu_options": menu_options,
            "blocked_seconds": round(blocked_s, 2),
            "map_hint": hint,
            "last_actions": last_actions[-2:],
        }

        if blocked_s >= cfg.unblock_after_s:
            action, reason = next(unb), "unblock pattern"
        else:
            out = decide_action(state, last_actions)
            action, reason = out["action"], out.get("reason", "")

        event = {"t": time.time(), "state": state, "decision": {"action": action, "reason": reason}}
        log_line(event if cfg.log_json else f"{event}", cfg.log_json)

        if not cfg.dry_run and limiter.allow():
            sender.send(action)
            last_actions.append(action)
            last_actions = last_actions[-10:]

        if hud is not None:
            elapsed = max(1e-6, time.perf_counter() - t0); fps = 1.0 / elapsed
            info = get_window_info(args.window_id) if args.window_id else None
            if info and info.get("bbox"):
                hud.move_to_bbox(info["bbox"])
            hud.update_view(frame, boxes, state, {"action": action, "reason": reason}, fps)
            from PySide6 import QtWidgets
            QtWidgets.QApplication.processEvents()

        prev = frame
        time.sleep(max(0.0, target_dt - (time.perf_counter() - t0)))

if __name__ == "__main__":
    main()
