from typing import Tuple
import numpy as np
import cv2

def frame_similarity(prev: np.ndarray, curr: np.ndarray) -> float:
    ph, pw = 160, 288
    p1 = cv2.resize(prev, (pw, ph))
    p2 = cv2.resize(curr, (pw, ph))
    p1 = cv2.cvtColor(p1, cv2.COLOR_RGB2GRAY)
    p2 = cv2.cvtColor(p2, cv2.COLOR_RGB2GRAY)
    p1 = (p1 - p1.mean()) / (p1.std() + 1e-6)
    p2 = (p2 - p2.mean()) / (p2.std() + 1e-6)
    sim = float((p1*p2).mean())
    return (sim + 1.0) / 2.0

def _align_gray(g1: np.ndarray, g2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    if g1.shape == g2.shape:
        return g1, g2
    h = min(g1.shape[0], g2.shape[0])
    w = min(g1.shape[1], g2.shape[1])
    if h < 4 or w < 4:
        return g1[:0,:0], g2[:0,:0]
    return g1[:h,:w], g2[:h,:w]

def optical_flow_magnitude(prev: np.ndarray, curr: np.ndarray) -> float:
    g1 = cv2.cvtColor(prev, cv2.COLOR_RGB2GRAY)
    g2 = cv2.cvtColor(curr, cv2.COLOR_RGB2GRAY)
    g1, g2 = _align_gray(g1, g2)
    if g1.size == 0 or g2.size == 0:
        return 0.0
    try:
        flow = cv2.calcOpticalFlowFarneback(g1, g2, None, 0.5, 3, 15, 3, 5, 1.1, 0)
        mag, _ = cv2.cartToPolar(flow[...,0], flow[...,1])
        return float(np.median(mag))
    except cv2.error:
        return 0.0

def update_blocked_seconds(prev: np.ndarray, curr: np.ndarray, prev_blocked: float, dt: float, threshold: float) -> float:
    try:
        sim = frame_similarity(prev, curr)
        flow = optical_flow_magnitude(prev, curr)
    except Exception:
        sim = frame_similarity(prev, curr)
        flow = 0.0
    if sim >= threshold and flow < 0.2:
        return prev_blocked + dt
    return 0.0

def map_hint(curr: np.ndarray) -> str:
    gray = cv2.cvtColor(curr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 80, 160)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=40, maxLineGap=6)
    if lines is None:
        return "unknown"
    verts, diags = 0, 0
    for l in lines:
        x1,y1,x2,y2 = l[0]
        dx, dy = abs(x2-x1), abs(y2-y1)
        if dx < 4 and dy > 24:
            verts += 1
        if dx > 12 and dy > 12:
            diags += 1
    if verts >= 8:
        return "door"
    if diags >= 10:
        return "stair"
    return "unknown"
