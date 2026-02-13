"""
Dashboard Window — Fluent UI Conversational Agent
- Uses qfluentwidgets for a modern Windows 11 style.
- Preserves the strict Signal/Slot architecture.
"""

import sys
import os
import time
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, Signal, Slot, QUrl
from PySide6.QtGui import QIcon, QDesktopServices

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon as FIF,
    SplashScreen, setTheme, Theme
)

from src.core import config_manager
from src.ui.widgets.chat_widget import ChatWidget

# Determine application root
if getattr(sys, 'frozen', False):
    APP_ROOT = os.path.dirname(sys.executable)
else:
    APP_ROOT = os.path.dirname(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

class DashboardWindow(FluentWindow):
    def __init__(self, launcher_callback=None):
        super().__init__()
        self.launcher_callback = launcher_callback
        
        # Window Setup
        self.setWindowTitle("Jarvis")
        self.resize(1000, 750)
        self.setMinimumSize(850, 600)
        
        # Center on screen
        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        
        # Theme
        setTheme(Theme.DARK)
        
        self.config_path = os.path.join(APP_ROOT, "config.json")
        self.load_configs()
        
        # Initialize Sub-Interfaces
        self.chat_interface = ChatWidget(self)
        self.settings_interface = QWidget() # Placeholder for now
        self.settings_interface.setObjectName("settings_interface")
        
        self.init_navigation()
        self.splash_screen = SplashScreen(self.windowIcon(), self)
        self.splash_screen.finish()

    def init_navigation(self):
        self.addSubInterface(
            self.chat_interface,
            FIF.CHAT,
            "Conversation",
            NavigationItemPosition.TOP
        )
        
        self.addSubInterface(
            self.settings_interface,
            FIF.SETTING,
            "Settings",
            NavigationItemPosition.BOTTOM
        )

    def load_configs(self):
        self.system_config = config_manager.ensure_json(self.config_path, {"wake_word": "jarvis", "version": 2})

    @Slot(str, str, str)
    def update_status(self, status, last_wake, last_action):
        # Delegate status updates to the chat widget (header)
        if hasattr(self, 'chat_interface'):
            self.chat_interface.set_status(status)

    @Slot(str)
    def add_error(self, msg):
        # We can implement a InfoBar later
        print(f"[UI Error] {msg}")

    @Slot()
    def show_window(self):
        self.show()
        self.activateWindow()
        self.raise_()
