import os
import webbrowser
import shutil
import subprocess
from src.tools.base_tool import BaseTool
from src.tools.registry import register
from src.core.logging_config import get_logger

logger = get_logger(__name__)

class OpenWebsiteTool(BaseTool):
    name = "open_website"
    description = "Open a URL in a browser"
    schema = {
        "name": "open_website",
        "description": "Open a URL in a browser",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "browser": {"type": "string"}
            },
            "required": ["url"]
        }
    }

    async def execute(self, **kwargs) -> dict:
        url = kwargs.get("url")
        browser_name = kwargs.get("browser")
        
        if not url:
            return {"status": "error", "message": "Missing URL"}
        
        if not url.startswith("http"):
            url = "https://" + url

        if browser_name:
            browser_name = browser_name.lower()
            mappings = {
                "brave": "brave.exe",
                "chrome": "chrome.exe",
                "edge": "msedge.exe",
                "firefox": "firefox.exe"
            }
            
            exe = mappings.get(browser_name)
            if exe:
                # Resolve path
                path = shutil.which(exe)
                if not path:
                    # Check common paths
                    common_paths = [
                        os.path.join(os.environ.get("ProgramFiles", ""), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                        os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
                        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
                        os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
                        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
                        os.path.join(os.environ.get("ProgramFiles", ""), "Mozilla Firefox", "firefox.exe")
                    ]
                    for p in common_paths:
                        if os.path.exists(p) and exe in p:
                            path = p
                            break
                
                if path:
                    logger.info(f"Launching browser {browser_name} using: {path}")
                    subprocess.Popen([path, url])
                    return {"status": "success", "browser": browser_name, "url": url}
                else:
                    return {"status": "error", "reason": "browser_not_found"}
            
        # Default fallback
        webbrowser.open(url)
        return {"status": "success", "url": url}

# Auto-register on import
register(OpenWebsiteTool)
