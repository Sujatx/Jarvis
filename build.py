import os
import sys
import shutil
import subprocess

def clean_dirs():
    dirs = ['build', 'dist']
    for d in dirs:
        if os.path.exists(d):
            print(f"Cleaning {d}...")
            shutil.rmtree(d)

def build_exe():
    print("Building Jarvis.exe with PyInstaller...")
    spec_file = "jarvis.spec"
    
    if not os.path.exists(spec_file):
        print(f"Error: {spec_file} not found.")
        sys.exit(1)

    try:
        # Run PyInstaller
        subprocess.check_call([
            sys.executable, 
            "-m", 
            "PyInstaller", 
            "--clean", 
            "--noconfirm", 
            spec_file
        ])
    except subprocess.CalledProcessError:
        print("Error: Build failed.")
        sys.exit(1)

def verify_build():
    exe_path = os.path.join("dist", "Jarvis.exe")
    if os.path.exists(exe_path):
        print(f"Build successful: {exe_path}")
        # Copy .env to dist if it exists in root
        if os.path.exists(".env"):
             shutil.copy(".env", os.path.join("dist", ".env"))
             print("Copied .env to dist/")
    else:
        print("Error: Output executable not found.")
        sys.exit(1)

def main():
    clean_dirs()
    build_exe()
    verify_build()

if __name__ == "__main__":
    main()
