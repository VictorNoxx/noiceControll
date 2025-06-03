import PyInstaller.__main__
import os
import sys

def build():
    # Get the absolute path of the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define paths
    dist_path = os.path.join(script_dir, "dist")
    build_path = os.path.join(script_dir, "build")
    icon_path = os.path.join(script_dir, "app_icon.ico")
    
    # Create icon if it doesn't exist
    if not os.path.exists(icon_path):
        print("Creating icon...")
        os.system(f"{sys.executable} create_icon.py")
    
    # Define PyInstaller arguments
    args = [
        'noise_monitor_gui.py',
        '--name=NoiseMonitor',
        '--onefile',
        '--windowed',
        '--icon=app_icon.ico',
        '--clean',
        # Add hidden imports
        '--hidden-import=numpy',
        '--hidden-import=sounddevice',
        '--hidden-import=soundfile',
        '--hidden-import=requests',
        # Add data files
        '--add-data=app_icon.ico;.',
        # Set paths
        f'--workpath={build_path}',
        f'--distpath={dist_path}',
        '--noconfirm',
    ]
    
    print("Building executable...")
    PyInstaller.__main__.run(args)
    print(f"\nBuild complete! Executable is available at: {os.path.join(dist_path, 'NoiseMonitor.exe')}")

if __name__ == '__main__':
    build() 