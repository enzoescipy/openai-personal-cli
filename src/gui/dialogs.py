from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QApplication, QProgressDialog
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

class ProcessingDialog(QProgressDialog):
    """Modal dialog for processing status with explicit user cancellation signal."""
    # Signal emitted only when the user explicitly cancels (e.g., clicks Cancel button)
    user_cancelled = pyqtSignal()

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

    def reject(self):
        """Override reject to emit user_cancelled signal when Cancel is clicked."""
        # Emit the custom signal before calling the base class reject (which closes the dialog)
        print("[DEBUG] ProcessingDialog reject() called, emitting user_cancelled.")
        self.user_cancelled.emit()
        # Call the base class implementation to ensure the dialog still closes
        super().reject() 