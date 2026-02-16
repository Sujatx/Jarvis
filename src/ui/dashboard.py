"""
Elite Dashboard - Mark-X Visuals with Table-Based Alignment
Guarantees Left for Jarvis and Right for User.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QFrame, QTextEdit, QApplication, QLineEdit
)
from PySide6.QtCore import Qt, Signal, Slot, QSize, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QTextCursor

from src.ui.widgets.face_widget import FaceWidget
from src.core.logging_config import get_logger
import os

logger = get_logger(__name__)

class DashboardWindow(QMainWindow):
    update_status_signal = Signal(str)
    display_signal = Signal(str, str) # text, role

    def __init__(self, launcher_callback=None):
        super().__init__()
        self.launcher = launcher_callback
        self.setWindowTitle("JARVIS")
        self.resize(700, 800)
        self.setStyleSheet("background-color: #000000;")
        
        self._init_ui()
        self._connect_events()
        self.show()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # 1. The Face
        face_path = os.path.abspath("resources/face.png")
        self.face = FaceWidget(face_path)
        
        face_layout = QHBoxLayout()
        face_layout.addStretch()
        face_layout.addWidget(self.face)
        face_layout.addStretch()
        layout.addLayout(face_layout)

        # 2. Status
        self.lbl_status = QLabel("SYSTEM ONLINE")
        self.lbl_status.setFont(QFont("Consolas", 14, QFont.Bold))
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color: #00e5ff;")
        layout.addWidget(self.lbl_status)

        # 3. HTML Console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 11))
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #050505;
                color: #8ffcff;
                border: 1px solid #1a1a1a;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        layout.addWidget(self.console)

        # 4. Text Input
        input_container = QHBoxLayout()
        input_container.addStretch()
        self.txt_input = QLineEdit()
        self.txt_input.setPlaceholderText("TYPE A COMMAND, SIR...")
        self.txt_input.setFixedWidth(500)
        self.txt_input.setFixedHeight(40)
        self.txt_input.setStyleSheet("""
            QLineEdit {
                background-color: #0a0a0a;
                color: #8ffcff;
                border: 1px solid #1a1a1a;
                border-radius: 20px;
                padding-left: 15px;
                font-family: 'Consolas';
            }
            QLineEdit:focus { border: 1px solid #00e5ff; }
        """)
        self.txt_input.returnPressed.connect(self._on_text_send)
        input_container.addWidget(self.txt_input)
        input_container.addStretch()
        layout.addLayout(input_container)

    def _on_text_send(self):
        text = self.txt_input.text().strip()
        if text:
            self.display_signal.emit(text, "user")
            self.txt_input.clear()
            if self.launcher and self.launcher.event_bus:
                self.launcher.event_bus.publish_sync("command.text", {"text": text})

    def _connect_events(self):
        self.update_status_signal.connect(self._on_status_update)
        self.display_signal.connect(self._on_display_update)
        if self.launcher and self.launcher.event_bus:
            self.launcher.event_bus.subscribe("speech.partial", self._on_partial)
            self.launcher.event_bus.subscribe("speech.transcribed", self._on_final)
            self.launcher.event_bus.subscribe("speech.started", self._on_speaking)
            self.launcher.event_bus.subscribe("speech.completed", self._on_idle)

    @Slot(str, str)
    def _on_display_update(self, text, role):
        # Use a table to force absolute left/right alignment
        if role == "user":
            html = f'''
            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                <tr>
                    <td align="right">
                        <div style="color: #8ffcff; font-family: Consolas; margin-bottom: 10px;">
                            <b>YOU:</b> {text}
                        </div>
                    </td>
                </tr>
            </table>
            '''
        else:
            html = f'''
            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                <tr>
                    <td align="left">
                        <div style="color: #00e5ff; font-family: Consolas; margin-bottom: 10px;">
                            <b>JARVIS:</b> {text}
                        </div>
                    </td>
                </tr>
            </table>
            '''
        self.console.insertHtml(html)
        self.console.insertHtml("<br>")
        self.console.moveCursor(QTextCursor.End)

    def _on_status_update(self, status):
        self.lbl_status.setText(status.upper())
        if "Listening" in status: self.face.set_state("listening")
        elif "Thinking" in status or "Acting" in status: self.face.set_state("thinking")
        else: self.face.set_state("idle")

    def _on_partial(self, event):
        text = event.payload.get("text", "")
        self.lbl_status.setText(f"LISTENING: {text}...")

    def _on_final(self, event):
        text = event.payload.get("text", "")
        self.display_signal.emit(text, "user")

    def _on_speaking(self, event):
        text = event.payload.get("text", "")
        self.face.set_state("speaking")
        self.display_signal.emit(text, "assistant")

    def _on_idle(self, event):
        self.face.set_state("idle")

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()
