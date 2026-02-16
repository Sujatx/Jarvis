"""
System Skills - Elite Primitives.
Optimized for window-reuse and instance protection.
"""

import pyautogui
import time
import winreg
import os
import pygetwindow as gw
from src.core.logging_config import get_logger

logger = get_logger(__name__)

pyautogui.PAUSE = 0.1

def focus_window(title_part: str) -> bool:
    """Finds a window by title and brings it to the front."""
    try:
        windows = gw.getWindowsWithTitle(title_part)
        if windows:
            win = windows[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.3)
            return True
        return False
    except Exception as e:
        logger.error(f"OS: Focus Window Failed: {e}")
        return False

def is_app_installed(app_name: str) -> bool:
    app_name = app_name.lower()
    reg_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    ]
    for path in reg_paths:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            name = winreg.QueryValueEx(subkey, "DisplayName")[0].lower()
                            if app_name in name and "uninstall" not in name:
                                return True
                    except: continue
        except: continue
    return False

def open_visual(target: str) -> str:
    """Only use this for non-browser apps or files."""
    logger.info(f"OS: Visual Search for {target}...")
    
    # Check if already open first
    if focus_window(target):
        return f"Focused existing {target} window."

    try:
        pyautogui.press("esc")
        time.sleep(0.1)
        pyautogui.press("win")
        time.sleep(0.5)
        pyautogui.write(target, interval=0.02)
        time.sleep(0.4)
        pyautogui.press("enter")
        return f"Visual search triggered for {target}."
    except Exception as e:
        return f"Failed: {e}"

def execute_hotkey(keys: list) -> str:
    try:
        pyautogui.hotkey(*keys)
        return f"Executed {keys}"
    except Exception as e:
        return f"Failed hotkey: {e}"

def input_text(text: str, enter=True) -> str:
    pyautogui.write(text, interval=0.02)
    if enter: pyautogui.press("enter")
    return f"Typed {text}"

def navigation(action: str) -> str:
    actions = {
        "scroll_up": lambda: pyautogui.press("pgup"),
        "scroll_down": lambda: pyautogui.press("pgdn"),
        "close": lambda: pyautogui.hotkey("alt", "f4")
    }
    if action in actions:
        actions[action]()
        return f"Executed {action}."
    return "Unknown action."
