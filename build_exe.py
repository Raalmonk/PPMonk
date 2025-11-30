import os
import subprocess
import sys

def build_exe():
    """
    Builds the executable using PyInstaller.
    Requires 'pyinstaller' to be installed (pip install pyinstaller).
    """

    # Define main entry point
    main_script = "main.py"

    # Define assets path (Windows separator ';', Unix ':')
    # Assuming Windows for "exe" request, but PyInstaller handles separator if we use `add_data` arg format correctly or detect OS.
    # The standard format for PyInstaller command line is "src;dest" on Windows.

    sep = ";" if os.name == 'nt' else ":"
    assets_arg = f"assets{sep}assets"

    cmd = [
        "pyinstaller",
        "--noconsole",          # Don't show console window (GUI app)
        "--onefile",            # Bundle everything into a single .exe
        "--name=PPMonkSim",     # Name of the output executable
        f"--add-data={assets_arg}", # Include assets folder
        "--clean",              # Clean cache
        main_script
    ]

    print("Building EXE with command:")
    print(" ".join(cmd))

    try:
        subprocess.check_call(cmd)
        print("\nBuild successful! Check the 'dist' folder for PPMonkSim.exe")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed: {e}")
        print("Ensure pyinstaller is installed: pip install pyinstaller")
    except FileNotFoundError:
        print("\nPyInstaller not found. Please install it with: pip install pyinstaller")

if __name__ == "__main__":
    build_exe()
