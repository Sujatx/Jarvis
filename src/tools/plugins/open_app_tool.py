import os
import shutil
import subprocess
import winreg
from src.tools.base_tool import BaseTool
from src.tools.registry import register
from src.core.logging_config import get_logger

logger = get_logger(__name__)

class OpenAppTool(BaseTool):
    name = "open_app"
    description = "Launch a desktop application"
    schema = {
        "name": "open_app",
        "description": "Launch a desktop application",
        "parameters": {
            "type": "object",
            "properties": {
                "app": {"type": "string"}
            },
            "required": ["app"]
        }
    }

    def _find_app_path(self, app_name: str) -> str:
        """Try to find the app executable."""
        app_name_lower = app_name.lower()
        
        # 1. Try adding .exe if not present
        if not app_name_lower.endswith(".exe"):
            app_name_exe = f"{app_name}.exe"
        else:
            app_name_exe = app_name
        
        # 2. Check if it's in PATH
        path = shutil.which(app_name_exe)
        if path:
            logger.info(f"Found app in PATH: {path}")
            return path
        
        # 3. Try common Windows app locations
        common_paths = [
            f"C:\\Program Files\\{app_name}\\{app_name_exe}",
            f"C:\\Program Files (x86)\\{app_name}\\{app_name_exe}",
            f"C:\\Program Files\\{app_name.capitalize()}\\{app_name_exe}",
            f"C:\\Program Files (x86)\\{app_name.capitalize()}\\{app_name_exe}",
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                logger.info(f"Found app in common path: {path}")
                return path
        
        # 4. Try registry for uninstall paths (Windows)
        try:
            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    subkey_name = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, subkey_name) as subkey:
                        try:
                            display_name = winreg.QueryValueEx(subkey, "DisplayName")[0].lower()
                            if app_name_lower in display_name:
                                install_path = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                exe_path = os.path.join(install_path, app_name_exe)
                                if os.path.exists(exe_path):
                                    logger.info(f"Found app in registry: {exe_path}")
                                    return exe_path
                        except:
                            pass
        except:
            pass
        
        # 5. Fall back to just the app name (Windows will search PATH)
        logger.warning(f"Could not find full path for {app_name}, using name directly")
        return app_name_exe

    async def execute(self, **kwargs) -> dict:
        app = kwargs.get("app")
        if not app:
            return {"status": "error", "message": "Missing app name"}
        
        try:
            # First try to find the full path
            app_path = self._find_app_path(app)
            logger.info(f"Launching {app} from {app_path}")
            
            # Use Windows 'start' command which properly searches PATH and handles app launching
            # Format: start "" "app_path" - the empty string avoids title bar issues
            cmd = f'start "" "{app_path}"'
            subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            return {"status": "success", "message": f"Opened {app}, sir."}
        except Exception as e:
            logger.error(f"Failed to open {app}: {e}")
            return {"status": "error", "message": f"Failed to open {app}: {str(e)}"}

# Auto-register on import
register(OpenAppTool)
