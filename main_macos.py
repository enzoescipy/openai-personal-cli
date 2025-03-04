import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.gui import App

def init_macos_specific():
    """Initialize macOS-specific settings."""
    # Set platform specific attributes
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar)
    
    # Enable Metal/OpenGL
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
    
    # Set environment variables for macOS keyboard handling
    os.environ['PYNPUT_KEYBOARD_MONITORING'] = '1'
    
    # Configure macOS-specific settings for voice recognition
    try:
        import pynput
        print("pynput successfully imported for macOS keyboard handling")
    except ImportError:
        print("Warning: pynput not installed. Voice recording keyboard controls may not work.")
        print("Try installing with: pip install pynput")

def main():
    # Initialize macOS specific settings
    init_macos_specific()
    
    # Create and run the application
    app = App()
    return app.run()

if __name__ == "__main__":
    sys.exit(main()) 