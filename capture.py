from typing import Optional, Tuple, List, Dict
import numpy as np
from PIL import Image
import mss

try:
    import Quartz as Q
    HAVE_QUARTZ = True
except Exception:
    HAVE_QUARTZ = False

EXCLUDE_OWNERS = {"Python", "python", "Python3"}

def _list_windows() -> List[Dict]:
    if not HAVE_QUARTZ:
        return []
    info = Q.CGWindowListCopyWindowInfo(Q.kCGWindowListOptionOnScreenOnly, Q.kCGNullWindowID)
    return info or []

def debug_windows() -> List[Dict]:
    out = []
    for w in _list_windows():
        wid = int(w.get("kCGWindowNumber") or 0)
        owner = (w.get("kCGWindowOwnerName") or "").strip()
        name = (w.get("kCGWindowName") or "").strip()
        pid = int(w.get("kCGWindowOwnerPID") or 0)
        b = w.get("kCGWindowBounds", {})
        x, y = int(b.get('X', 0)), int(b.get('Y', 0))
        w_, h_ = int(b.get('Width', 0)), int(b.get('Height', 0))
        out.append({"id": wid, "owner": owner, "pid": pid, "name": name, "bbox": (x, y, w_, h_)})
    out.sort(key=lambda r: r["bbox"][2] * r["bbox"][3], reverse=True)
    return out

def get_window_info(window_id: int) -> Optional[Dict]:
    for w in _list_windows():
        if int(w.get("kCGWindowNumber") or 0) == int(window_id):
            owner = (w.get("kCGWindowOwnerName") or "").strip()
            name = (w.get("kCGWindowName") or "").strip()
            pid = int(w.get("kCGWindowOwnerPID") or 0)
            b = w.get("kCGWindowBounds", {})
            x, y = int(b.get('X', 0)), int(b.get('Y', 0))
            w_, h_ = int(b.get('Width', 0)), int(b.get('Height', 0))
            return {"id": window_id, "owner": owner, "pid": pid, "name": name, "bbox": (x, y, w_, h_)}
    return None

def find_window_by_keyword(title_keyword: str) -> Optional[Tuple[int, Tuple[int,int,int,int], int]]:
    if not title_keyword or not HAVE_QUARTZ:
        return None
    title_keyword = title_keyword.lower()
    cand = []
    for w in _list_windows():
        owner = (w.get("kCGWindowOwnerName") or "")
        name = (w.get("kCGWindowName") or "")
        if any(ex in owner for ex in EXCLUDE_OWNERS):
            continue
        full = f"{name} {owner}".lower()
        if title_keyword in full:
            b = w.get("kCGWindowBounds", {})
            x, y = int(b.get('X',0)), int(b.get('Y',0))
            W, H = int(b.get('Width',0)), int(b.get('Height',0))
            wid = int(w.get("kCGWindowNumber") or 0)
            pid = int(w.get("kCGWindowOwnerPID") or 0)
            if W > 200 and H > 200:
                cand.append((wid, (x, y, W, H), pid))
    if not cand:
        return None
    cand.sort(key=lambda t: t[1][2] * t[1][3], reverse=True)
    return cand[0]

class MacWindowCapture:
    def __init__(self, window_id: int):
        self.window_id = int(window_id)

    def grab(self) -> np.ndarray:
        cgimg = Q.CGWindowListCreateImage(
            Q.CGRectNull,
            Q.kCGWindowListOptionIncludingWindow,
            self.window_id,
            Q.kCGWindowImageDefault
        )
        if not cgimg:
            raise RuntimeError("CGWindowListCreateImage failed")
        width = Q.CGImageGetWidth(cgimg)
        height = Q.CGImageGetHeight(cgimg)
        provider = Q.CGImageGetDataProvider(cgimg)
        data = Q.CGDataProviderCopyData(provider)
        buf = bytes(data)
        rowbytes = Q.CGImageGetBytesPerRow(cgimg)
        arr = np.frombuffer(buf, dtype=np.uint8)
        arr = arr.reshape((height, rowbytes // 4, 4))
        arr = arr[:, :width, :]
        b, g, r, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
        rgb = np.dstack((r, g, b))
        return rgb

class ScreenCapture:
    def __init__(self, bbox: Optional[Tuple[int,int,int,int]] = None):
        self.sct = mss.mss()
        self.bbox = bbox
    def grab(self) -> np.ndarray:
        if self.bbox:
            mon = {"left": self.bbox[0], "top": self.bbox[1], "width": self.bbox[2], "height": self.bbox[3]}
        else:
            mon = self.sct.monitors[1]
        img = self.sct.grab(mon)
        from PIL import Image
        arr = np.array(Image.frombytes("RGB", (img.width, img.height), img.rgb))
        return arr
