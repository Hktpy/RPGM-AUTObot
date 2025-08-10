from typing import Dict, List, Tuple, Optional
import numpy as np
import cv2
from PySide6 import QtCore, QtGui, QtWidgets

class HUD(QtWidgets.QMainWindow):
    def __init__(self, frameless: bool = True):
        super().__init__()
        self.setWindowTitle("RPGM AutoPlayer — HUD")
        if frameless:
            self.setWindowFlags(
                QtCore.Qt.WindowStaysOnTopHint
                | QtCore.Qt.FramelessWindowHint
                | QtCore.Qt.Tool
                | QtCore.Qt.WindowTransparentForInput
            )
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        else:
            self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)

        cw = QtWidgets.QWidget(self)
        self.setCentralWidget(cw)
        layout = QtWidgets.QVBoxLayout(cw)
        layout.setContentsMargins(6,6,6,6)

        self.label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.label.setMinimumSize(640, 360)
        layout.addWidget(self.label)

        self.info = QtWidgets.QTextEdit(readOnly=True)
        self.info.setFixedHeight(140)
        layout.addWidget(self.info)

    def move_to_bbox(self, bbox: Tuple[int,int,int,int]):
        if not bbox: return
        x,y,w,h = bbox
        self.setGeometry(x, y, w, h)

    def update_view(self, frame: np.ndarray, boxes: List[Tuple[int,int,int,int]], state: Dict, decision: Dict, fps: float):
        disp = frame.copy()
        for (x,y,w,h) in boxes or []:
            cv2.rectangle(disp, (x,y), (x+w, y+h), (0,255,0), 2)

        lines = [
            f"FPS: {fps:.1f}",
            f"Blocked: {state.get('blocked_seconds')} s",
            f"Hint: {state.get('map_hint')}",
            f"Dialog: {str(state.get('dialog_text'))[:80]}",
            f"Menu: {', '.join(state.get('menu_options') or [])[:80]}",
            f"Action: {decision.get('action')} ({decision.get('reason')})"
        ]
        y = 24
        for t in lines:
            cv2.putText(disp, t, (10,y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 3, cv2.LINE_AA)
            cv2.putText(disp, t, (10,y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1, cv2.LINE_AA)
            y += 22

        h, w, ch = disp.shape
        bytes_per_line = ch * w
        qimg = QtGui.QImage(disp.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
        pix = QtGui.QPixmap.fromImage(qimg)
        self.label.setPixmap(pix)
        self.info.setPlainText("\n".join(lines))
