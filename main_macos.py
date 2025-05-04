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
    
    # Removed environment variable setting for pynput
    # Removed pynput import and related checks

def main():
    # Initialize macOS specific settings
    init_macos_specific()
    
    # Create and run the application
    app = App()
    return app.run()

if __name__ == "__main__":
    sys.exit(main()) 