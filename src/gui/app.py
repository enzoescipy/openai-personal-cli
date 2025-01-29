import sys
from PyQt6.QtWidgets import QApplication
from .main_window import MainWindow
from ..core.settings import Settings
from ..features.controllers import MainController

class App:
    def __init__(self):
        # Initialize Qt Application
        self.app = QApplication(sys.argv)
        
        # Initialize core components
        self.settings = Settings()
        
        # Initialize controller
        self.controller = MainController(self.settings)
        
        # Initialize main window
        self.window = MainWindow(self.controller)

    def run(self):
        """Run the application."""
        self.window.show()
        return self.app.exec() 