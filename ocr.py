from typing import List, Tuple, Optional
import cv2
import numpy as np
import pytesseract

def preprocess_for_ocr(frame: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bilateralFilter(gray, 5, 35, 35)
    gray = cv2.equalizeHist(gray)
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 31, 10)
    return th

def _bottom_band(frame: np.ndarray, band_ratio: float = 0.33) -> np.ndarray:
    h = frame.shape[0]
    band_h = int(h * band_ratio)
    return frame[h-band_h:h, :, :]

def _text_regions(frame_gray: np.ndarray) -> List[Tuple[int,int,int,int]]:
    bw = cv2.adaptiveThreshold(frame_gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 10)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7,3))
    closed = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    H, W = frame_gray.shape[:2]
    for c in contours:
        x,y,w,h = cv2.boundingRect(c)
        if w*h < (W*H)*0.01:
            continue
        ar = w/float(h+1e-6)
        if 2.0 <= ar <= 20.0 and h > H*0.06:
            boxes.append((x,y,w,h))
    return boxes[:3]

def extract_dialog_and_menu(frame: np.ndarray, tess_langs: str):
    roi = _bottom_band(frame)
    proc = preprocess_for_ocr(roi)
    cfg = "--oem 1 --psm 6"
    try:
        text = pytesseract.image_to_string(proc, lang=tess_langs, config=cfg)
    except pytesseract.TesseractError:
        text = ""
    text = text.strip()

    if text:
        lines = [l.strip("•>▶-–·◆* ").strip() for l in text.splitlines() if l.strip()]
        lines = [l for l in lines if len(l) >= 1]
        menu_keywords = {"Yes","No","はい","いいえ","OK","Cancel","キャンセル","Save","Load"}
        is_menu = (len(lines) >= 2 and sum(1 for l in lines if len(l) <= 18) >= 2) or any(k in text for k in menu_keywords)
        boxes = [(0, frame.shape[0]-roi.shape[0], roi.shape[1], roi.shape[0])]
        if is_menu:
            return None, lines[:6], boxes
        else:
            dialog = " ".join(lines)
            return dialog, [], boxes

    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    boxes = _text_regions(gray)
    for (x,y,w,h) in boxes:
        crop = frame[y:y+h, x:x+w]
        proc = preprocess_for_ocr(crop)
        try:
            t2 = pytesseract.image_to_string(proc, lang=tess_langs, config=cfg)
        except pytesseract.TesseractError:
            t2 = ""
        t2 = t2.strip()
        if not t2: 
            continue
        lines = [l.strip("•>▶-–·◆* ").strip() for l in t2.splitlines() if l.strip()]
        lines = [l for l in lines if len(l) >= 1]
        if len(lines) >= 2 and sum(1 for l in lines if len(l) <= 18) >= 2:
            return None, lines[:6], boxes
        if len(lines) >= 1:
            return " ".join(lines), [], boxes
    return None, [], boxes
