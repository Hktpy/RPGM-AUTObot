import time
from typing import Literal, Optional, Callable, Tuple
from pynput.keyboard import Controller as KController, Key
from pynput.mouse import Controller as MController, Button

KeyName = Literal["UP","DOWN","LEFT","RIGHT","ENTER","INTERACT","MENU","WAIT"]

class ActionSender:
    def __init__(self, move_press_ms: int = 150, mouse_mode: bool = False, pid_getter: Optional[Callable[[], int]] = None, bbox_getter: Optional[Callable[[], Tuple[int,int,int,int]]] = None):
        self.kb = KController()
        self.mouse = MController()
        self.move_press_ms = move_press_ms
        self.stopped = False
        self.mouse_mode = mouse_mode
        self.pid_getter = pid_getter or (lambda: 0)
        self.bbox_getter = bbox_getter or (lambda: (0,0,0,0))

    def _focus(self):
        try:
            from .focus import activate_pid
            pid = self.pid_getter() if self.pid_getter else 0
            if pid:
                activate_pid(pid)
                time.sleep(0.03)
        except Exception:
            pass

    def _tap(self, key, ms: int = 80):
        self.kb.press(key); time.sleep(ms/1000.0); self.kb.release(key)

    def _interact_combo(self):
        self._tap('z', 40); self._tap(Key.enter, 40); self._tap(Key.space, 40)

    def _menu_combo(self):
        self._tap(Key.esc, 60); self._tap('x', 40)

    def _mouse_step(self, direction: str):
        x,y,w,h = self.bbox_getter() or (0,0,0,0)
        if w <= 0 or h <= 0:
            return False
        cx, cy = x + w//2, y + h//2
        dx = 0; dy = 0
        step = max(40, min(w,h)//5)
        if direction == "UP": dy = -step
        elif direction == "DOWN": dy = step
        elif direction == "LEFT": dx = -step
        elif direction == "RIGHT": dx = step
        tx, ty = cx + dx, cy + dy
        try:
            self.mouse.position = (tx, ty)
            time.sleep(0.01)
            self.mouse.click(Button.left, 1)
            return True
        except Exception:
            return False

    def send(self, action: KeyName):
        if self.stopped: return
        self._focus()
        if action == "WAIT": time.sleep(0.12); return
        if action in ("UP","DOWN","LEFT","RIGHT") and self.mouse_mode:
            if self._mouse_step(action): return
        if action == "UP": return self._tap(Key.up, self.move_press_ms)
        if action == "DOWN": return self._tap(Key.down, self.move_press_ms)
        if action == "LEFT": return self._tap(Key.left, self.move_press_ms)
        if action == "RIGHT": return self._tap(Key.right, self.move_press_ms)
        if action == "ENTER": return self._tap(Key.enter, 60)
        if action == "INTERACT": return self._interact_combo()
        if action == "MENU": return self._menu_combo()
