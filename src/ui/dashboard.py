import sys
import os
import time
import threading
import win32com.client
from src.core import config_manager
import ctypes

if getattr(sys, 'frozen', False):
    APP_ROOT = os.path.dirname(sys.executable)
else:
    APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                             QCheckBox, QScrollArea, QFrame, QStackedWidget,
                             QListWidget, QListWidgetItem, QToolButton, QScroller,
                             QSizePolicy, QAbstractScrollArea)
from PySide6.QtCore import Qt, Signal, QTimer, Slot, QMetaObject
from PySide6.QtGui import QFont, QColor, QPalette

class AppScanner:
    @staticmethod
    def get_installed_apps():
        apps = []
        shell = win32com.client.Dispatch("WScript.Shell")
        
        # Start Menu paths
        paths = [
            os.path.join(os.environ["ProgramData"], "Microsoft", "Windows", "Start Menu", "Programs"),
            os.path.join(os.environ["AppData"], "Microsoft", "Windows", "Start Menu", "Programs")
        ]
        
        for base_path in paths:
            if not os.path.exists(base_path):
                continue
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith(".lnk"):
                        lnk_path = os.path.join(root, file)
                        try:
                            shortcut = shell.CreateShortcut(lnk_path)
                            target = shortcut.TargetPath
                            if target.lower().endswith(".exe") and os.path.exists(target):
                                name = file[:-4] # Remove .lnk
                                apps.append({"name": name, "path": target})
                        except:
                            continue
        
        # Deduplicate by path
        unique_apps = {a['path']: a for a in apps}.values()
        return sorted(list(unique_apps), key=lambda x: x['name'])

class DashboardWindow(QMainWindow):
    validation_finished = Signal(bool, str)

    def __init__(self, launcher_callback=None):
        super().__init__()
        self.launcher_callback = launcher_callback
        self.setWindowTitle("Jarvis Control Dashboard")
        self.resize(1000, 700)
        self.setMinimumSize(850, 550)
        
        # Modernize Window
        self.apply_modern_effects()
        font = QFont("Segoe UI Variable Display", 10)
        if not font.exactMatch():
            font = QFont("Segoe UI", 10)
        self.setFont(font)
        
        self.apps_config_path = os.path.join(APP_ROOT, "apps.json")
        self.urls_config_path = os.path.join(APP_ROOT, "urls.json")
        self.config_path = os.path.join(APP_ROOT, "config.json")
        
        self.load_configs()
        
        self.central_widget = QWidget()
        self.central_widget.setObjectName("central_widget")
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        
        self.setup_sidebar()
        self.setup_main_content()
        self.load_styles()
        
        # Initial population
        QTimer.singleShot(100, self.populate_apps)

    def apply_modern_effects(self):
        # Enable dark mode for window frame
        dwm = ctypes.windll.dwmapi
        hwnd = self.winId()
        
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        dark_mode = ctypes.c_int(1)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))
        
        # DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2
        corner_preference = ctypes.c_int(2)
        dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_preference), ctypes.sizeof(corner_preference))
        
        # DWMWA_SYSTEMBACKDROP_TYPE = 38, DWMSBT_MAINWINDOW = 2 (Mica)
        # Use 3 (Acrylic) if Mica is not available or desired. 2 is usually better for Win 11.
        backdrop_type = ctypes.c_int(2) 
        dwm.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop_type), ctypes.sizeof(backdrop_type))
        
        # Set background transparent to show Mica
        # self.setAttribute(Qt.WA_TranslucentBackground) # Removed for opacity

    def load_configs(self):
        # Apps
        self.apps_config = config_manager.ensure_json(self.apps_config_path, {})
        
        # URLs Migration & Load
        urls_data = config_manager.load_json(self.urls_config_path)
        default_urls = {"google chrome": [], "microsoft edge": [], "firefox": []}
        if isinstance(urls_data, list):
            urls_data = {"google chrome": urls_data, "microsoft edge": [], "firefox": []}
            config_manager.save_json(self.urls_config_path, urls_data)
        elif "browser_urls" in urls_data:
            urls_data = {"google chrome": urls_data["browser_urls"], "microsoft edge": [], "firefox": []}
            config_manager.save_json(self.urls_config_path, urls_data)
            
        if not urls_data and not os.path.exists(self.urls_config_path):
            self.urls_config = config_manager.ensure_json(self.urls_config_path, default_urls)
        elif not urls_data:
            self.urls_config = default_urls
        else:
            self.urls_config = urls_data

        # System
        self.system_config = config_manager.ensure_json(self.config_path, {"wake_word": "jarvis", "mode": "clap", "version": 1})

    def save_apps_config(self):
        config_manager.save_json(self.apps_config_path, self.apps_config)

    def save_urls_config(self):
        config_manager.save_json(self.urls_config_path, self.urls_config)

    def save_system_config(self):
        config_manager.save_json(self.config_path, self.system_config)
        self.btn_restart.setVisible(True)

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        
        title = QLabel("JARVIS")
        title.setObjectName("sidebar_title")
        title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title)
        
        self.btn_status = QPushButton("Status")
        self.btn_apps = QPushButton("App Manager")
        self.btn_settings = QPushButton("Settings")
        
        for btn in [self.btn_status, self.btn_apps, self.btn_settings]:
            btn.setObjectName("sidebar_btn")
            sidebar_layout.addWidget(btn)
            
        sidebar_layout.addStretch()
        
        self.main_layout.addWidget(self.sidebar)

    def setup_main_content(self):
        self.pages = QStackedWidget()
        self.pages.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # --- Status Page ---
        self.status_page = QWidget()
        self.status_page.setObjectName("stack_page")
        self.status_page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        status_layout = QVBoxLayout(self.status_page)
        
        status_card = QFrame()
        status_card.setObjectName("settings_card")
        status_card_layout = QVBoxLayout(status_card)
        
        self.lbl_current_status = QLabel("Status: Idle")
        self.lbl_current_status.setStyleSheet("font-size: 18px; color: #00e5ff; font-weight: bold;")
        self.lbl_last_wake = QLabel("Last Wake: Never")
        self.lbl_last_action = QLabel("Last Action: Never")
        
        status_card_layout.addWidget(self.lbl_current_status)
        status_card_layout.addWidget(self.lbl_last_wake)
        status_card_layout.addWidget(self.lbl_last_action)
        status_layout.addWidget(QLabel("<h1>System Status</h1>"))
        status_layout.addWidget(status_card)
        
        # Event Log
        status_layout.addWidget(QLabel("<h3>Event Log</h3>"))
        self.log_scroll = QScrollArea()
        self.log_scroll.setWidgetResizable(True)
        self.log_scroll.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.log_scroll.setStyleSheet("background-color: #1b1b1b; border-radius: 8px; border: 1px solid #333;")
        
        self.log_label = QLabel("Waiting for events...")
        self.log_label.setContentsMargins(10, 10, 10, 10)
        self.log_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.log_label.setWordWrap(True)
        self.log_label.setStyleSheet("font-family: 'Consolas', monospace; font-size: 11px; color: #aaa;")
        
        self.log_scroll.setWidget(self.log_label)
        status_layout.addWidget(self.log_scroll)
        
        # --- App Manager Page ---
        self.apps_page = QWidget()
        self.apps_page.setObjectName("stack_page")
        self.apps_page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        apps_layout = QVBoxLayout(self.apps_page)
        apps_layout.addWidget(QLabel("<h1>App Launch Manager</h1>"))
        
        self.apps_scroll = QScrollArea()
        self.apps_scroll.setWidgetResizable(True)
        self.apps_scroll.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        
        self.apps_container = QWidget()
        # self.apps_container.setParent(self.apps_scroll) # REMOVED: setWidget handles this
        
        self.apps_main_layout = QVBoxLayout(self.apps_container)
        self.apps_main_layout.setAlignment(Qt.AlignTop)
        
        # Enabled Section
        self.enabled_apps_label = QLabel("<h3>Enabled Apps</h3>")
        self.apps_main_layout.addWidget(self.enabled_apps_label)
        self.enabled_apps_layout = QVBoxLayout()
        self.apps_main_layout.addLayout(self.enabled_apps_layout)
        
        # Available Section
        self.available_apps_label = QLabel("<h3>Available Apps</h3>")
        self.apps_main_layout.addWidget(self.available_apps_label)
        self.available_apps_layout = QVBoxLayout()
        self.apps_main_layout.addLayout(self.available_apps_layout)
        
        self.apps_scroll.setWidget(self.apps_container)
        QScroller.grabGesture(self.apps_scroll.viewport(), QScroller.LeftMouseButtonGesture)
        apps_layout.addWidget(self.apps_scroll)
        
        # --- Settings Page ---
        self.settings_page = QWidget()
        self.settings_page.setObjectName("stack_page")
        self.settings_page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        settings_page_layout = QVBoxLayout(self.settings_page)
        settings_page_layout.addWidget(QLabel("<h1>Settings</h1>"))
        
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        
        settings_container = QWidget()
        # settings_container.setParent(settings_scroll) # REMOVED: setWidget handles this
        
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setAlignment(Qt.AlignTop)
        
        # Wake Word Card
        wake_card = QFrame()
        wake_card.setObjectName("settings_card")
        wake_vbox = QVBoxLayout(wake_card)
        wake_vbox.addWidget(QLabel("<h3>Wake Word</h3>"))
        wake_vbox.addWidget(QLabel("The word Jarvis listens for to activate."))
        self.txt_wake_word = QLineEdit(self.system_config.get("wake_word", "jarvis"))
        wake_vbox.addWidget(self.txt_wake_word)
        settings_layout.addWidget(wake_card)
        
        # Voice Engine Card
        engine_card = QFrame()
        engine_card.setObjectName("settings_card")
        engine_vbox = QVBoxLayout(engine_card)
        engine_vbox.addWidget(QLabel("<h3>Voice Engine</h3>"))
        engine_vbox.addWidget(QLabel("Porcupine Access Key (from picovoice.ai)"))
        
        key_input_layout = QHBoxLayout()
        self.txt_access_key = QLineEdit()
        self.txt_access_key.setEchoMode(QLineEdit.Password)
        self.txt_access_key.setPlaceholderText("Enter Access Key...")
        # Initial value from .env
        env_path = os.path.join(APP_ROOT, ".env")
        self.txt_access_key.setText(config_manager.get_env_value(env_path, "PORCUPINE_ACCESS_KEY"))
        
        self.btn_toggle_key = QPushButton("Show")
        self.btn_toggle_key.setFixedWidth(80)
        self.btn_toggle_key.setStyleSheet("""
            QPushButton {
                background-color: #444; 
                color: white;
                padding: 8px 5px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        
        key_input_layout.addWidget(self.txt_access_key)
        key_input_layout.addWidget(self.btn_toggle_key)
        engine_vbox.addLayout(key_input_layout)
        
        self.btn_save_key = QPushButton("Verify & Save Key")
        engine_vbox.addWidget(self.btn_save_key)
        settings_layout.addWidget(engine_card)
        
        # Mode Card
        mode_card = QFrame()
        mode_card.setObjectName("settings_card")
        mode_vbox = QVBoxLayout(mode_card)
        mode_vbox.addWidget(QLabel("<h3>Execution Mode</h3>"))
        mode_vbox.addWidget(QLabel("How Jarvis confirms the launch trigger."))
        self.chk_mode = QCheckBox("Clap Mode (Checked) / Keyword Mode (Unchecked)")
        self.chk_mode.setChecked(self.system_config.get("mode") == "clap")
        mode_vbox.addWidget(self.chk_mode)
        settings_layout.addWidget(mode_card)
        
        # Restart Card
        restart_card = QFrame()
        restart_card.setObjectName("settings_card")
        restart_vbox = QVBoxLayout(restart_card)
        restart_vbox.addWidget(QLabel("<h3>System</h3>"))
        self.btn_restart = QPushButton("Restart Jarvis")
        self.btn_restart.setObjectName("restart_btn")
        self.btn_restart.setVisible(False)
        restart_vbox.addWidget(self.btn_restart)
        settings_layout.addWidget(restart_card)
        
        settings_scroll.setWidget(settings_container)
        settings_page_layout.addWidget(settings_scroll)
        
        self.pages.addWidget(self.status_page)
        self.pages.addWidget(self.apps_page)
        self.pages.addWidget(self.settings_page)
        
        # FIX: Make pages opaque to prevent overlap artifacts
        for page in (self.status_page, self.apps_page, self.settings_page):
            page.setAutoFillBackground(True)
            pal = page.palette()
            pal.setColor(page.backgroundRole(), QColor(32, 32, 32))
            page.setPalette(pal)
            page.setAttribute(Qt.WA_StyledBackground, True)
        
        self.main_layout.addWidget(self.pages)
        self.main_layout.setStretchFactor(self.sidebar, 0)
        self.main_layout.setStretchFactor(self.pages, 1)
        
        # Connections
        self.btn_status.clicked.connect(lambda: self.switch_page(0))
        self.btn_apps.clicked.connect(lambda: self.switch_page(1))
        self.btn_settings.clicked.connect(lambda: self.switch_page(2))
        
        self.txt_wake_word.textChanged.connect(self.on_setting_changed)
        self.chk_mode.stateChanged.connect(self.on_setting_changed)
        self.btn_restart.clicked.connect(self.restart_jarvis)
        
        self.btn_toggle_key.clicked.connect(self.toggle_access_key_visibility)
        self.btn_save_key.clicked.connect(self.save_access_key)
        
        self.switch_page(0)
        
        # First-run check: if no access key, highlight settings
        QTimer.singleShot(500, self.check_first_run)

    def check_first_run(self):
        env_path = os.path.join(APP_ROOT, ".env")
        key = config_manager.get_env_value(env_path, "PORCUPINE_ACCESS_KEY")
        if not key:
            self.add_log_entry("NOTICE: No Access Key found. Opening Settings.")
            self.switch_page(2)
            self.txt_access_key.setFocus()

    def toggle_access_key_visibility(self):
        if self.txt_access_key.echoMode() == QLineEdit.Password:
            self.txt_access_key.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_key.setText("Hide")
        else:
            self.txt_access_key.setEchoMode(QLineEdit.Password)
            self.btn_toggle_key.setText("Show")

    def save_access_key(self):
        key = self.txt_access_key.text().strip()
        if not key:
            self.add_log_entry("ERROR: Please enter an access key.")
            return
            
        self.btn_save_key.setEnabled(False)
        self.btn_save_key.setText("Verifying...")
        self.add_log_entry("Verifying access key...")
        
        # Run validation in a thread to keep UI responsive
        def run_validation():
            if self.launcher_callback:
                # We need to reach the launcher object. 
                # In main(), window = DashboardWindow(launcher_callback=launcher)
                success, message = self.launcher_callback.validate_and_update_key(key)
                
                # UI update must happen in main thread
                QMetaObject.invokeMethod(self, "on_validation_result", 
                                       Qt.QueuedConnection,
                                       Qt.Argument("bool", success),
                                       Qt.Argument("QString", message))
            else:
                self.btn_save_key.setEnabled(True)
                self.btn_save_key.setText("Verify & Save Key")

        threading.Thread(target=run_validation, daemon=True).start()

    @Slot(bool, str)
    def on_validation_result(self, success, message):
        self.btn_save_key.setEnabled(True)
        self.btn_save_key.setText("Verify & Save Key")
        if success:
            self.add_log_entry(f"SUCCESS: {message}")
        else:
            self.add_log_entry(f"ERROR: {message}")

    def switch_page(self, index):
        self.pages.setCurrentIndex(index)
        w = self.pages.currentWidget()
        if w:
            w.raise_()
            
        # Update sidebar button styling
        self.btn_status.setProperty("active", index == 0)
        self.btn_apps.setProperty("active", index == 1)
        self.btn_settings.setProperty("active", index == 2)
        # Force style refresh
        for btn in [self.btn_status, self.btn_apps, self.btn_settings]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def populate_apps(self):
        self.clear_layout(self.enabled_apps_layout)
        self.clear_layout(self.available_apps_layout)
        
        apps = AppScanner.get_installed_apps()
        
        # Sort all apps alphabetically
        apps = sorted(apps, key=lambda x: x['name'].lower())
        
        enabled_count = 0
        available_count = 0
        
        for app in apps:
            is_enabled = app['name'] in self.apps_config
            card = self.create_app_card(app['name'], app['path'], is_enabled)
            
            if is_enabled:
                self.enabled_apps_layout.addWidget(card)
                enabled_count += 1
            else:
                self.available_apps_layout.addWidget(card)
                available_count += 1
        
        self.enabled_apps_label.setVisible(enabled_count > 0)
        self.available_apps_label.setVisible(available_count > 0)

    def create_app_card(self, name, path, is_enabled):
        card = QFrame()
        card.setObjectName("app_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(5)
        
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        chk = QCheckBox(name)
        chk.setChecked(is_enabled)
        chk.setStyleSheet("font-size: 15px; font-weight: bold;")
        header_layout.addWidget(chk)
        header_layout.addStretch()
        
        card_layout.addWidget(header)
        
        # If browser, add collapsible URL section
        is_browser = any(b in name.lower() for b in ["chrome", "firefox", "edge"])
        if is_browser and is_enabled:
            # Determine browser key for urls.json
            browser_key = "google chrome"
            if "firefox" in name.lower(): browser_key = "firefox"
            elif "edge" in name.lower(): browser_key = "microsoft edge"
            
            collapsible = self.create_url_section(browser_key)
            card_layout.addWidget(collapsible)
            
        chk.stateChanged.connect(lambda state, n=name, p=path: self.on_app_toggled(n, p, state))
        
        return card

    def create_url_section(self, browser_key):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(25, 5, 5, 5)
        
        toggle_btn = QToolButton()
        toggle_btn.setCheckable(True)
        toggle_btn.setChecked(False)
        toggle_btn.setText(f" {browser_key.title()} URLs")
        toggle_btn.setArrowType(Qt.RightArrow)
        toggle_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toggle_btn.setStyleSheet("border: none; color: #00e5ff; font-weight: bold;")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 5, 0, 5)
        
        url_list = QListWidget()
        url_list.setMinimumHeight(100)
        url_list.setMaximumHeight(150)
        urls = self.urls_config.get(browser_key, [])
        for url in urls:
            url_list.addItem(url)
            
        content_layout.addWidget(url_list)
        
        input_row = QHBoxLayout()
        txt_url = QLineEdit()
        txt_url.setPlaceholderText("Add URL...")
        btn_add = QPushButton("+")
        btn_add.setFixedWidth(40)
        input_row.addWidget(txt_url)
        input_row.addWidget(btn_add)
        content_layout.addLayout(input_row)
        
        btn_del = QPushButton("Remove Selected")
        btn_del.setStyleSheet("background-color: #444; color: white;")
        content_layout.addWidget(btn_del)
        
        layout.addWidget(toggle_btn)
        layout.addWidget(content)
        
        content.setVisible(False)
        
        def toggle(checked):
            toggle_btn.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
            content.setVisible(checked)
            
        toggle_btn.clicked.connect(toggle)
        
        # URL Logic
        def add_url_inner():
            u = txt_url.text().strip()
            if u:
                if browser_key not in self.urls_config:
                    self.urls_config[browser_key] = []
                if u not in self.urls_config[browser_key]:
                    self.urls_config[browser_key].append(u)
                    config_manager.save_json(self.urls_config_path, self.urls_config)
                    url_list.addItem(u)
                    txt_url.clear()
                    
        def remove_url_inner():
            item = url_list.currentItem()
            if item:
                u = item.text()
                if u in self.urls_config.get(browser_key, []):
                    self.urls_config[browser_key].remove(u)
                    config_manager.save_json(self.urls_config_path, self.urls_config)
                    url_list.takeItem(url_list.row(item))
        
        btn_add.clicked.connect(add_url_inner)
        btn_del.clicked.connect(remove_url_inner)
        
        return container

    def on_app_toggled(self, name, path, state):
        if state == 2: # Checked
            config_manager.update_json(self.apps_config_path, name, path)
            self.apps_config[name] = path
        else:
            if name in self.apps_config:
                del self.apps_config[name]
                config_manager.save_json(self.apps_config_path, self.apps_config)
            
        # Refresh UI to move cards between sections
        self.populate_apps()

    def on_setting_changed(self):
        self.system_config["wake_word"] = self.txt_wake_word.text()
        self.system_config["mode"] = "clap" if self.chk_mode.isChecked() else "keyword"
        self.save_system_config()

    def restart_jarvis(self):
        if self.launcher_callback:
            # Re-executing current process
            os.execl(sys.executable, sys.executable, *sys.argv)

    def load_styles(self):
        self.setStyleSheet("""
            #central_widget { 
                background-color: #202020; 
            }
            QStackedWidget > QWidget {
                background-color: #202020;
            }
            #sidebar { 
                background-color: #1b1b1b; 
                border-right: 1px solid #333; 
            }
            #sidebar_title { 
                color: #00e5ff; 
                font-size: 24px; 
                font-weight: bold; 
                margin-bottom: 20px; 
                padding: 10px;
            }
            #sidebar_btn { 
                background-color: transparent; 
                color: #bbb; 
                border: none; 
                padding: 12px 20px; 
                text-align: left; 
                font-size: 15px; 
                border-radius: 6px;
                margin: 2px 8px;
            }
            #sidebar_btn:hover { 
                background-color: #2a2a2a; 
                color: white; 
            }
            #sidebar_btn[active="true"] {
                background-color: #2a2a2a;
                color: #00e5ff;
                font-weight: bold;
            }
            
            QLabel { color: #eee; }
            h1, h2, h3 { color: #00e5ff; font-weight: bold; }
            
            QLineEdit { 
                background-color: #2a2a2a; 
                color: white; 
                border: 1px solid #444; 
                padding: 8px; 
                border-radius: 6px;
            }
            QLineEdit:focus {
                border: 1px solid #00e5ff;
            }
            
            QPushButton { 
                background-color: #00e5ff; 
                color: #121212; 
                border: none; 
                padding: 10px 20px; 
                font-weight: bold; 
                border-radius: 6px;
            }
            QPushButton:hover { 
                background-color: #00d2eb; 
            }
            QPushButton:pressed {
                background-color: #00b8cc;
            }
            
            #restart_btn { 
                background-color: #ff4444; 
                color: white; 
            }
            #restart_btn:hover {
                background-color: #ff2222;
            }
            
            QScrollArea { 
                border: none; 
                background-color: #202020; 
            }
            QScrollArea > QWidget {
                background: transparent;
            }
            
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #444;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #555;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            /* Card Style */
            .QFrame#app_card, .QFrame#settings_card {
                background-color: #2a2a2a;
                border-radius: 10px;
                padding: 15px;
                margin: 5px;
            }
            
            QCheckBox { 
                color: white; 
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #555;
                background-color: #1b1b1b;
            }
            QCheckBox::indicator:checked {
                background-color: #00e5ff;
                border: 1px solid #00e5ff;
            }
        """)

    def update_status(self, status, last_wake=None, last_action=None):
        self.lbl_current_status.setText(f"Status: {status}")
        if last_wake:
            self.lbl_last_wake.setText(f"Last Wake: {last_wake}")
        if last_action:
            self.lbl_last_action.setText(f"Last Action: {last_action}")
        self.add_log_entry(f"Status changed to: {status}")

    @Slot(str)
    def add_error(self, text):
        self.add_log_entry(f"ERROR: {text}")

    def add_log_entry(self, text):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {text}"
        
        current_text = self.log_label.text()
        if current_text == "Waiting for events...":
            lines = []
        else:
            lines = current_text.split("\n")
            
        lines.append(entry)
        # Keep only last 20 events
        lines = lines[-20:]
        
        self.log_label.setText("\n".join(lines))
        # Scroll to bottom
        QTimer.singleShot(10, lambda: self.log_scroll.verticalScrollBar().setValue(
            self.log_scroll.verticalScrollBar().maximum()
        ))

    @Slot()
    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())
