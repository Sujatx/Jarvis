import os
import sys
import json
import subprocess
import traceback

# Determine application root
if getattr(sys, 'frozen', False):
    APP_ROOT = os.path.dirname(sys.executable)
else:
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))

def install_dependencies():
    print("Installing dependencies from requirements.txt...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    except subprocess.CalledProcessError:
        print("Error: Failed to install dependencies.")
        sys.exit(1)

def create_config_files():
    print("Checking configuration files...")
    
    files = {
        "apps.json": {},
        "urls.json": {"google chrome": [], "microsoft edge": [], "firefox": []},
        "config.json": {"wake_word": "jarvis", "mode": "clap", "version": 1}
    }

    for filename, content in files.items():
        path = os.path.join(APP_ROOT, filename)
        if not os.path.exists(path):
            print(f"Creating {filename}...")
            with open(path, 'w') as f:
                json.dump(content, f, indent=4)
        else:
            print(f"{filename} exists.")

    env_path = os.path.join(APP_ROOT, ".env")
    if not os.path.exists(env_path):
        print("Creating .env...")
        with open(env_path, 'w') as f:
            f.write("PORCUPINE_ACCESS_KEY=your_access_key_here\nCHROME_PROFILE=Profile 1\n")
    else:
        print(".env exists.")

def check_porcupine():
    print("Verifying Porcupine initialization...")
    # Import here after dependencies are installed
    try:
        import pvporcupine
        from dotenv import load_dotenv
    except ImportError:
        print("Warning: pvporcupine or python-dotenv not installed correctly.")
        return

    load_dotenv(os.path.join(APP_ROOT, ".env"))
    key = os.getenv("PORCUPINE_ACCESS_KEY")
    
    if not key or key == "your_access_key_here":
        print("Warning: PORCUPINE_ACCESS_KEY is not set in .env. Voice features will fail.")
        return

    try:
        pvporcupine.create(access_key=key, keywords=["jarvis"])
        print("Porcupine initialized successfully.")
    except Exception as e:
        # Handle specific activation limit error by string checking if class not available directly
        err_str = str(e)
        if "ActivationLimit" in err_str or "PorcupineActivationLimitError" in type(e).__name__:
            print(f"\n[WARNING] Porcupine Activation Limit Reached: {e}")
            print("The app will still run, but wake-word detection may be disabled.")
        else:
            print(f"\n[WARNING] Porcupine Initialization Failed: {e}")
            print("Please check your AccessKey in .env.")

def main():
    install_dependencies()
    create_config_files()
    check_porcupine()
    print("\nSetup complete.")

if __name__ == "__main__":
    main()
