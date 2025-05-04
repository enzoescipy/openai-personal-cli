from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QApplication, QProgressDialog
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

class ProcessingDialog(QProgressDialog):
    """Modal dialog for processing status."""
    def __init__(self, message: str, parent=None):
        super().__init__(message, "Cancel", 0, 0, parent)
        self.setWindowTitle("Processing")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumDuration(500)
        
    def keyPressEvent(self, event):
        """Handle key press events."""
        # Prevent ESC from closing the dialog
        if event.key() != Qt.Key.Key_Escape:
            super().keyPressEvent(event) 