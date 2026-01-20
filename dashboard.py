import sys
import os
import json
import winreg
import shutil
import win32com.client
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                             QCheckBox, QScrollArea, QFrame, QStackedWidget,
                             QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, Signal, QTimer, Slot
from PySide6.QtGui import QIcon, QFont

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
    def __init__(self, launcher_callback=None):
        super().__init__()
        self.launcher_callback = launcher_callback
        self.setWindowTitle("Jarvis Control Dashboard")
        self.setFixedSize(900, 600)
        
        self.apps_config_path = "apps.json"
        self.urls_config_path = "urls.json"
        self.config_path = "config.json"
        
        self.load_configs()
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        
        self.setup_sidebar()
        self.setup_main_content()
        self.load_styles()
        
        # Initial population
        QTimer.singleShot(100, self.populate_apps)

    def load_configs(self):
        # Load or init apps.json
        if os.path.exists(self.apps_config_path):
            with open(self.apps_config_path, 'r', encoding='utf-8') as f:
                try:
                    self.apps_config = json.load(f)
                except:
                    self.apps_config = {}
        else:
            self.apps_config = {}

        # Load or init urls.json
        if os.path.exists(self.urls_config_path):
            with open(self.urls_config_path, 'r', encoding='utf-8') as f:
                try:
                    self.urls_config = json.load(f)
                except:
                    self.urls_config = {"browser_urls": []}
        else:
            self.urls_config = {"browser_urls": []}

        # Load or init config.json
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                try:
                    self.system_config = json.load(f)
                except:
                    self.system_config = {"wake_word": "jarvis", "mode": "clap"}
        else:
            self.system_config = {"wake_word": "jarvis", "mode": "clap"}

    def save_apps_config(self):
        with open(self.apps_config_path, 'w', encoding='utf-8') as f:
            json.dump(self.apps_config, f, indent=4)

    def save_urls_config(self):
        with open(self.urls_config_path, 'w', encoding='utf-8') as f:
            json.dump(self.urls_config, f, indent=4)

    def save_system_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.system_config, f, indent=4)
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
        
        # Status Page
        self.status_page = QWidget()
        status_layout = QVBoxLayout(self.status_page)
        status_layout.addWidget(QLabel("<h1>System Status</h1>"))
        self.lbl_current_status = QLabel("Status: Idle")
        self.lbl_last_wake = QLabel("Last Wake: Never")
        self.lbl_last_action = QLabel("Last Action: Never")
        status_layout.addWidget(self.lbl_current_status)
        status_layout.addWidget(self.lbl_last_wake)
        status_layout.addWidget(self.lbl_last_action)
        
        self.error_log = QLabel("")
        self.error_log.setStyleSheet("color: #ff4444; font-size: 12px;")
        self.error_log.setWordWrap(True)
        status_layout.addWidget(self.error_log)
        
        status_layout.addStretch()
        
        # App Manager Page
        self.apps_page = QWidget()
        apps_layout = QVBoxLayout(self.apps_page)
        apps_layout.addWidget(QLabel("<h1>App Launch Manager</h1>"))
        
        self.apps_scroll = QScrollArea()
        self.apps_container = QWidget()
        self.apps_list_layout = QVBoxLayout(self.apps_container)
        self.apps_list_layout.setAlignment(Qt.AlignTop)
        self.apps_scroll.setWidget(self.apps_container)
        self.apps_scroll.setWidgetResizable(True)
        apps_layout.addWidget(self.apps_scroll)
        
        # Browser URLs Section (Conditional)
        self.browser_urls_frame = QFrame()
        self.browser_urls_frame.setObjectName("browser_section")
        self.browser_urls_frame.setVisible(False)
        browser_layout = QVBoxLayout(self.browser_urls_frame)
        browser_layout.addWidget(QLabel("<h3>Browser Links to Open:</h3>"))
        
        self.url_list = QListWidget()
        browser_layout.addWidget(self.url_list)
        
        url_input_layout = QHBoxLayout()
        self.txt_new_url = QLineEdit()
        self.txt_new_url.setPlaceholderText("https://...")
        self.btn_add_url = QPushButton("Add")
        self.btn_add_url.setFixedWidth(60)
        url_input_layout.addWidget(self.txt_new_url)
        url_input_layout.addWidget(self.btn_add_url)
        browser_layout.addLayout(url_input_layout)
        
        self.btn_remove_url = QPushButton("Remove Selected")
        browser_layout.addWidget(self.btn_remove_url)
        
        apps_layout.addWidget(self.browser_urls_frame)
        
        # Settings Page
        self.settings_page = QWidget()
        settings_layout = QVBoxLayout(self.settings_page)
        settings_layout.addWidget(QLabel("<h1>Settings</h1>"))
        
        wake_layout = QHBoxLayout()
        wake_layout.addWidget(QLabel("Wake Word:"))
        self.txt_wake_word = QLineEdit(self.system_config.get("wake_word", "jarvis"))
        wake_layout.addWidget(self.txt_wake_word)
        settings_layout.addLayout(wake_layout)
        
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Execution Mode:"))
        self.chk_mode = QCheckBox("Clap Mode (Checked) / Keyword Mode (Unchecked)")
        self.chk_mode.setChecked(self.system_config.get("mode") == "clap")
        mode_layout.addWidget(self.chk_mode)
        settings_layout.addLayout(mode_layout)
        
        self.btn_restart = QPushButton("Restart Jarvis")
        self.btn_restart.setObjectName("restart_btn")
        self.btn_restart.setVisible(False)
        settings_layout.addWidget(self.btn_restart)
        settings_layout.addStretch()
        
        self.pages.addWidget(self.status_page)
        self.pages.addWidget(self.apps_page)
        self.pages.addWidget(self.settings_page)
        
        self.main_layout.addWidget(self.pages)
        
        # Connections
        self.btn_status.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        self.btn_apps.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        self.btn_settings.clicked.connect(lambda: self.pages.setCurrentIndex(2))
        
        self.txt_wake_word.textChanged.connect(self.on_setting_changed)
        self.chk_mode.stateChanged.connect(self.on_setting_changed)
        
        self.btn_add_url.clicked.connect(self.add_url)
        self.btn_remove_url.clicked.connect(self.remove_url)
        self.btn_restart.clicked.connect(self.restart_jarvis)

    def populate_apps(self):
        apps = AppScanner.get_installed_apps()
        for app in apps:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            
            lbl_name = QLabel(app['name'])
            chk = QCheckBox()
            chk.setChecked(app['name'] in self.apps_config)
            
            row_layout.addWidget(lbl_name)
            row_layout.addStretch()
            row_layout.addWidget(chk)
            
            chk.stateChanged.connect(lambda state, name=app['name'], path=app['path']: self.toggle_app(name, path, state))
            
            self.apps_list_layout.addWidget(row)
            
            if app['name'] in self.apps_config and any(b in app['name'].lower() for b in ["chrome", "firefox", "edge"]):
                self.browser_urls_frame.setVisible(True)
        
        self.refresh_url_list()

    def toggle_app(self, name, path, state):
        if state == 2: # Checked
            self.apps_config[name] = path
            if any(b in name.lower() for b in ["chrome", "firefox", "edge"]):
                self.browser_urls_frame.setVisible(True)
        else:
            if name in self.apps_config:
                del self.apps_config[name]
            
            browsers_enabled = any(any(b in k.lower() for b in ["chrome", "firefox", "edge"]) for k in self.apps_config.keys())
            self.browser_urls_frame.setVisible(browsers_enabled)
            
        self.save_apps_config()

    def refresh_url_list(self):
        self.url_list.clear()
        for url in self.urls_config.get("browser_urls", []):
            self.url_list.addItem(url)

    def add_url(self):
        url = self.txt_new_url.text().strip()
        if url:
            if url not in self.urls_config["browser_urls"]:
                self.urls_config["browser_urls"].append(url)
                self.save_urls_config()
                self.refresh_url_list()
                self.txt_new_url.clear()

    def remove_url(self):
        current_item = self.url_list.currentItem()
        if current_item:
            url = current_item.text()
            self.urls_config["browser_urls"].remove(url)
            self.save_urls_config()
            self.refresh_url_list()

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
            QMainWindow { background-color: #121212; }
            #sidebar { background-color: #1e1e1e; border-right: 1px solid #333; }
            #sidebar_title { color: #00e5ff; font-size: 24px; font-weight: bold; margin-bottom: 20px; }
            #sidebar_btn { 
                background-color: transparent; color: #bbb; border: none; 
                padding: 10px; text-align: left; font-size: 16px; 
            }
            #sidebar_btn:hover { background-color: #333; color: white; }
            QLabel { color: #eee; font-size: 14px; }
            h1 { color: #00e5ff; }
            h3 { color: #00e5ff; }
            QLineEdit { background-color: #2a2a2a; color: white; border: 1px solid #444; padding: 5px; }
            QPushButton { background-color: #00e5ff; color: #121212; border: none; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #00b8cc; }
            #restart_btn { background-color: #ff4444; color: white; }
            QScrollArea { border: none; background-color: transparent; }
            #browser_section { background-color: #1e1e1e; padding: 10px; border-top: 2px solid #00e5ff; }
            QListWidget { background-color: #2a2a2a; color: white; border: 1px solid #444; }
            QCheckBox { color: white; }
        """)

    def update_status(self, status, last_wake=None, last_action=None):
        self.lbl_current_status.setText(f"Status: {status}")
        if last_wake:
            self.lbl_last_wake.setText(f"Last Wake: {last_wake}")
        if last_action:
            self.lbl_last_action.setText(f"Last Action: {last_action}")

    @Slot(str)
    def add_error(self, text):
        current = self.error_log.text()
        self.error_log.setText(current + "\n" + text)

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
