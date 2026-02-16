"""
Face Widget - Pure Mark-X Animation Logic
Animated Iron Man interface with robust image loading and scaling.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, Property, QRect
from PySide6.QtGui import QPainter, QImage, QColor, QRadialGradient, QPixmap
import random
import time
import os

class FaceWidget(QWidget):
    def __init__(self, face_path, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        
        # Load Face Image safely
        if not os.path.exists(face_path):
            print(f"ERROR: Face image not found at {face_path}")
            self.face_img = None
        else:
            self.face_img = QImage(face_path)
            if self.face_img.isNull():
                print("ERROR: Failed to load image data (corrupt file?)")
                self.face_img = None

        self.jarvis_cyan = QColor(0, 180, 255)
        
        # Mark-X State
        self.speaking = False
        self.scale = 1.0
        self.target_scale = 1.0
        self.halo_alpha = 70
        self.target_halo_alpha = 70
        self.last_target_time = time.time()
        
        # Animation Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(16) # ~60 FPS

    def set_state(self, state: str):
        self.speaking = (state == "speaking")

    def _animate(self):
        now = time.time()

        if now - self.last_target_time > (0.25 if self.speaking else 0.7):
            if self.speaking:
                self.target_scale = random.uniform(1.02, 1.1)
                self.target_halo_alpha = random.randint(120, 150)
            else:
                self.target_scale = random.uniform(1.004, 1.012)
                self.target_halo_alpha = random.randint(60, 80)
            self.last_target_time = now

        scale_speed = 0.45 if self.speaking else 0.25
        halo_speed = 0.40 if self.speaking else 0.25

        self.scale += (self.target_scale - self.scale) * scale_speed
        self.halo_alpha += (self.target_halo_alpha - self.halo_alpha) * halo_speed
        
        self.update()

    def paintEvent(self, event):
        if not self.face_img:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        center = self.rect().center()
        
        # 1. Glow
        grad = QRadialGradient(center, self.width() / 2)
        color = QColor(self.jarvis_cyan)
        color.setAlpha(int(self.halo_alpha))
        grad.setColorAt(0, color)
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(grad)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.rect())
        
        # 2. Scale face to fit WIDGET size (not image size)
        # This prevents the image from being tiny if the original file is small
        widget_w = self.width() * 0.85
        widget_h = self.height() * 0.85
        
        draw_w = int(widget_w * self.scale)
        draw_h = int(widget_h * self.scale)
        
        target_rect = QRect(
            center.x() - draw_w // 2,
            center.y() - draw_h // 2,
            draw_w, draw_h
        )
        
        painter.drawImage(target_rect, self.face_img)
