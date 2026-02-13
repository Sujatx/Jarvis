"""
Conversation Widget - Live conversation status and transcript UI

Displays:
- Manual trigger button to bypass wake word
- Status indicator with color coding
- Live transcript of conversation
- Timeout countdown progress bar
"""

import asyncio
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTextEdit, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont

try:
    from src.core.event_bus import get_event_bus
except ImportError:
    def get_event_bus():
        return None


class ConversationWidget(QWidget):
    """
    Widget for displaying conversation status and transcript
    
    Features:
    - Manual "Activate Jarvis" button
    - Color-coded status indicator
    - Live conversation transcript
    - 30-second timeout progress bar
    """
    
    # Signals for thread-safe UI updates
    status_changed = Signal(str, str)  # status, color
    transcript_updated = Signal(str, str)  # role, text
    timeout_progress = Signal(int)  # progress percentage
    timer_control = Signal(bool)  # True to start, False to stop
    ui_visibility_changed = Signal(bool) # True to show, False to hide progress bar
    transcript_cleared = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.event_bus = get_event_bus()
        self.current_status = "Idle"
        self.timeout_seconds = 30
        self.timeout_elapsed = 0
        
        self._init_ui()
        self._init_timer()
        self._connect_signals()
        
        # Subscribe to events (Synchronous call to sync method)
        if self.event_bus:
            self._subscribe_events()
    
    def _init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Manual Trigger Button
        self.trigger_button = QPushButton("🎙️ Activate Jarvis")
        self.trigger_button.setObjectName("trigger_button")
        self.trigger_button.setMinimumHeight(40)
        self.trigger_button.clicked.connect(self._on_manual_trigger)
        self.trigger_button.setStyleSheet("""
            QPushButton#trigger_button {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton#trigger_button:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #45a049, stop:1 #3d8b40);
            }
            QPushButton#trigger_button:pressed {
                background: #2E7D32;
            }
        """)
        layout.addWidget(self.trigger_button)
        
        # Status Section
        status_layout = QHBoxLayout()
        
        self.status_indicator = QLabel("⚪")
        self.status_indicator.setFont(QFont("Segoe UI", 16))
        status_layout.addWidget(self.status_indicator)
        
        self.status_label = QLabel("Idle")
        self.status_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Timeout Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Timeout: %p%")
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #4CAF50;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Transcript Section
        transcript_label = QLabel("Conversation Transcript:")
        transcript_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(transcript_label)
        
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setMaximumHeight(200)
        self.transcript.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 5px;
                font-family: 'Consolas', monospace;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.transcript)
        
        self.setLayout(layout)
    
    def _init_timer(self):
        """Initialize timer for progress bar updates"""
        self.timer = QTimer()
        self.timer.setInterval(100)  # Update every 100ms
        self.timer.timeout.connect(self._update_progress)
    
    def _connect_signals(self):
        """Connect signals to slots"""
        self.status_changed.connect(self._update_status_ui)
        self.transcript_updated.connect(self._update_transcript_ui)
        self.timeout_progress.connect(self._update_progress_ui)
        self.timer_control.connect(self._handle_timer_control)
        self.ui_visibility_changed.connect(self._handle_visibility_change)
        self.transcript_cleared.connect(self._handle_transcript_clear)
    
    def _subscribe_events(self):
        """Subscribe to event bus events (Synchronous)"""
        if not self.event_bus:
            return
        
        # subscribe() is s synchronous method in EventBus
        self.event_bus.subscribe("wake_word.detected", self._on_wake_word)
        self.event_bus.subscribe("speech.transcribed", self._on_speech_transcribed)
        self.event_bus.subscribe("speech.started", self._on_speech_started)
        self.event_bus.subscribe("speech.completed", self._on_speech_completed)
        self.event_bus.subscribe("conversation.ended", self._on_conversation_ended)
    
    def _on_manual_trigger(self):
        """Handle manual trigger button click"""
        print("[ConversationWidget] Manual trigger activated")
        if self.event_bus:
            # Use publish_sync for thread-safe publishing from UI thread
            self.event_bus.publish_sync("wake_word.detected", {"source": "manual"})
    
    async def _on_wake_word(self, event):
        """Handle wake word detected event"""
        payload = event.payload if hasattr(event, 'payload') else event
        source = payload.get("source", "unknown")
        print(f"[ConversationWidget] Wake word detected from {source}")
        self.status_changed.emit("Listening...", "🟢")
        self.timeout_elapsed = 0
        self.timer_control.emit(True)
        self.ui_visibility_changed.emit(True)
    
    async def _on_speech_transcribed(self, event):
        """Handle speech transcribed event"""
        payload = event.payload if hasattr(event, 'payload') else event
        text = payload.get("text", "")
        if text:
            self.transcript_updated.emit("You", text)
        self.timeout_elapsed = 0  # Reset timeout
    
    async def _on_speech_started(self, event):
        """Handle speech started event"""
        payload = event.payload if hasattr(event, 'payload') else event
        text = payload.get("text", "")
        self.transcript_updated.emit("Jarvis", text)
        self.timeout_elapsed = 0  # Reset timeout
    
    async def _on_speech_completed(self, event):
        """Handle speech completed event"""
        pass
    
    async def _on_conversation_ended(self, event):
        """Handle conversation ended event"""
        self.status_changed.emit("Idle", "⚪")
        self.timer_control.emit(False)
        self.ui_visibility_changed.emit(False)
        self.timeout_progress.emit(0)
        self.transcript_cleared.emit()
    
    @Slot(str, str)
    def _update_status_ui(self, status: str, indicator: str):
        """Update status UI (thread-safe slot)"""
        self.current_status = status
        self.status_label.setText(status)
        self.status_indicator.setText(indicator)
    
    @Slot(str, str)
    def _update_transcript_ui(self, role: str, text: str):
        """Update transcript UI (thread-safe slot)"""
        self.transcript.append(f"<b>{role}:</b> {text}<br>")
        # Auto-scroll to bottom
        self.transcript.verticalScrollBar().setValue(
            self.transcript.verticalScrollBar().maximum()
        )

    @Slot(bool)
    def _handle_timer_control(self, start: bool):
        """Handle timer start/stop on main thread"""
        if start:
            self.timer.start()
        else:
            self.timer.stop()

    @Slot(bool)
    def _handle_visibility_change(self, visible: bool):
        """Handle visibility changes on main thread"""
        self.progress_bar.setVisible(visible)

    @Slot()
    def _handle_transcript_clear(self):
        """Clear transcript on main thread"""
        self.transcript.clear()
    
    def _update_progress(self):
        """Update timeout progress bar"""
        if self.current_status != "Idle":
            self.timeout_elapsed += 0.1
            progress = min(100, int((self.timeout_elapsed / self.timeout_seconds) * 100))
            self.timeout_progress.emit(progress)
    
    @Slot(int)
    def _update_progress_ui(self, progress: int):
        """Update progress bar UI (thread-safe slot)"""
        self.progress_bar.setValue(progress)
