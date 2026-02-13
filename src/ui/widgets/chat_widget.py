"""
Chat Widget - Fluent UI Upgrade (Fixed Toggle)
Maintains ChatGPT-style layout but uses correct ToggleButton for state.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
    QScrollArea, QSizePolicy, QLineEdit
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QMetaObject, QSize
from PySide6.QtGui import QColor, QFont

from qfluentwidgets import (
    BodyLabel, PrimaryPushButton, TransparentToolButton, 
    FluentIcon as FIF, StrongBodyLabel, Theme, ToggleButton
)

try:
    from src.core.event_bus import get_event_bus
except ImportError:
    def get_event_bus():
        return None


class ChatBubble(QFrame):
    """Fluent-styled chat bubble"""
    def __init__(self, text, role="user", parent=None):
        super().__init__(parent)
        self.role = role
        self.setFrameShape(QFrame.NoFrame)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        
        align_layout = QHBoxLayout()
        align_layout.setContentsMargins(0, 0, 0, 0)
        
        if role == "user":
            align_layout.addStretch()
            # User Message - Plain text (no bubble background)
            bubble = QFrame()
            bubble.setStyleSheet("background-color: transparent; color: #ffffff;")
            bubble_layout = QVBoxLayout(bubble)
            bubble_layout.setContentsMargins(10, 5, 10, 5)
            
            lbl = BodyLabel(text, self)
            lbl.setTextColor(QColor(255, 255, 255), QColor(255, 255, 255))
            lbl.setWordWrap(True)
            bubble_layout.addWidget(lbl)
            align_layout.addWidget(bubble)
        else:
            text_container = QWidget()
            text_layout = QVBoxLayout(text_container)
            text_layout.setContentsMargins(0, 0, 0, 0)
            
            lbl = BodyLabel(text, self)
            lbl.setWordWrap(True)
            text_layout.addWidget(lbl)
            
            actions_layout = QHBoxLayout()
            actions_layout.setSpacing(8)
            actions_layout.setContentsMargins(0, 5, 0, 0)
            
            for icon, tooltip in [(FIF.COPY, "Copy"), (FIF.SYNC, "Regenerate")]:
                btn = TransparentToolButton(icon, self)
                btn.setToolTip(tooltip)
                btn.setFixedSize(28, 28)
                actions_layout.addWidget(btn)
            
            actions_layout.addStretch()
            text_layout.addLayout(actions_layout)
            align_layout.addWidget(text_container)
            align_layout.addStretch()
            
        layout.addLayout(align_layout)


class ChatWidget(QWidget):
    """
    Main Chat Interface - Only Text and Hands-Free
    """
    
    display_message = Signal(str, str) 
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatWidget")
        self.event_bus = get_event_bus()
        self._init_ui()
        self._connect_signals()
        
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setFixedHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)
        
        self.lbl_model = StrongBodyLabel("Jarvis", self)
        header_layout.addWidget(self.lbl_model)
        
        header_layout.addSpacing(12)
        self.lbl_status = BodyLabel("• Idle", self)
        self.lbl_status.setStyleSheet("color: #00e5ff;")
        header_layout.addWidget(self.lbl_status)
        
        header_layout.addStretch()
        main_layout.addWidget(header)
        
        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        center_container = QWidget()
        center_layout = QHBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chat_container = QWidget()
        self.chat_container.setFixedWidth(750) 
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.addStretch() 
        self.chat_layout.setSpacing(10)
        self.chat_layout.setContentsMargins(0, 20, 0, 20)
        
        center_layout.addStretch()
        center_layout.addWidget(self.chat_container)
        center_layout.addStretch()
        
        self.scroll_area.setWidget(center_container)
        main_layout.addWidget(self.scroll_area)
        
        # --- Bottom Input Area ---
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 10, 0, 24)
        bottom_layout.setSpacing(10)
        
        input_wrapper = QFrame()
        input_wrapper.setFixedWidth(750)
        input_wrapper.setFixedHeight(56)
        input_wrapper.setStyleSheet("""
            QFrame {
                background-color: #2f2f2f;
                border-radius: 28px;
                border: 1px solid #3d3d3d;
            }
        """)
        wrapper_layout = QHBoxLayout(input_wrapper)
        wrapper_layout.setContentsMargins(15, 6, 10, 6)
        
        # Left: Plus
        self.btn_plus = TransparentToolButton(FIF.ADD, self)
        self.btn_plus.setFixedSize(36, 36)
        wrapper_layout.addWidget(self.btn_plus)
        
        # Center: Input Field
        self.txt_input = QLineEdit(self)
        self.txt_input.setPlaceholderText("Ask anything")
        self.txt_input.setStyleSheet("background: transparent; border: none; color: white; font-size: 16px; padding: 5px;")
        wrapper_layout.addWidget(self.txt_input)
        
        # Right: Circular Voice Mode Button
        self.btn_voice_mode = ToggleButton(parent=self)
        self.btn_voice_mode.setIcon(FIF.MUSIC)
        self.btn_voice_mode.setToolTip("Toggle Hands-Free Mode")
        self.btn_voice_mode.setFixedSize(40, 40)
        self.btn_voice_mode.setStyleSheet("""
            ToggleButton {
                border-radius: 20px;
                background-color: white;
                border: none;
            }
            ToggleButton:checked {
                background-color: #4CAF50;
            }
            ToggleButton:hover {
                background-color: #e0e0e0;
            }
        """)
        wrapper_layout.addWidget(self.btn_voice_mode)
        
        pill_hbox = QHBoxLayout()
        pill_hbox.addStretch()
        pill_hbox.addWidget(input_wrapper)
        pill_hbox.addStretch()
        bottom_layout.addLayout(pill_hbox)
        
        self.lbl_disclaimer = BodyLabel("Jarvis can make mistakes. Check important info.", self)
        self.lbl_disclaimer.setAlignment(Qt.AlignCenter)
        self.lbl_disclaimer.setStyleSheet("color: #666; font-size: 11px;")
        bottom_layout.addWidget(self.lbl_disclaimer)
        
        main_layout.addWidget(bottom_container)
        
        self.add_message("Hello sir. How can I help you today?", "assistant")
        
    def _connect_signals(self):
        self.txt_input.returnPressed.connect(self._on_send)
        self.btn_voice_mode.clicked.connect(self._on_voice_toggle_clicked)
        self.display_message.connect(self.add_message)
        
        if self.event_bus:
            self.event_bus.subscribe("speech.transcribed", self._on_user_speech_event)
            self.event_bus.subscribe("speech.started", self._on_jarvis_speech_event)

    def _on_voice_toggle_clicked(self):
        enabled = self.btn_voice_mode.isChecked()
        if self.event_bus:
            self.event_bus.publish_sync("voice_mode.changed", {"enabled": enabled})

    def _on_user_speech_event(self, event):
        payload = event.payload if hasattr(event, 'payload') else event
        text = payload.get("text", "")
        if text:
            self.display_message.emit(text, "user")

    def _on_jarvis_speech_event(self, event):
        payload = event.payload if hasattr(event, 'payload') else event
        text = payload.get("text", "")
        if text:
            self.display_message.emit(text, "assistant")

    def _on_send(self):
        text = self.txt_input.text().strip()
        if text:
            self.add_message(text, "user")
            self.txt_input.clear()
            if self.event_bus:
                self.event_bus.publish_sync("command.text", {"text": text})

    @Slot(str)
    def set_status(self, status):
        color = "#00e5ff" if "Idle" in status else "#4CAF50"
        self.lbl_status.setText(f"• {status}")
        self.lbl_status.setStyleSheet(f"color: {color};")

    @Slot(str, str)
    def add_message(self, text, role="user"):
        bubble = ChatBubble(text, role)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())
