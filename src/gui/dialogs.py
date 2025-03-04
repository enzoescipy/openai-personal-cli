from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QApplication, QProgressDialog
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

class RecordingDialog(QDialog):
    """Modal dialog for voice recording."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recording")
        self.setModal(True)
        self.setFixedSize(400, 200)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)  # Disable close button
        
        # Setup UI
        layout = QVBoxLayout()
        
        # Recording label with large emoji
        self.rec_label = QLabel("🔴")
        self.rec_label.setFont(QFont('Segoe UI Emoji', 48))
        self.rec_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.rec_label)
        
        # Instructions
        instructions = QLabel("Recording...\nPress SPACEBAR to stop\nPress ESC to cancel")
        instructions.setFont(QFont('Segoe UI', 12))
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)
        
        # Recording duration
        self.duration_label = QLabel("00:00")
        self.duration_label.setFont(QFont('Segoe UI', 14))
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.duration_label)
        
        self.setLayout(layout)
        
        # Setup timer for duration display
        self.duration = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_duration)
        self.timer.start(1000)  # Update every second
        
        # Ensure dialog gets keyboard focus
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        
    def update_duration(self):
        """Update the recording duration display."""
        self.duration += 1
        minutes = self.duration // 60
        seconds = self.duration % 60
        self.duration_label.setText(f"{minutes:02d}:{seconds:02d}")
        QApplication.processEvents()
        
    def closeEvent(self, event):
        """Handle dialog close."""
        self.timer.stop()
        super().closeEvent(event)
        
    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Space:
            print("SPACE key pressed - stopping recording")
            self.accept()  # Stop recording and accept
        elif event.key() == Qt.Key.Key_Escape:
            print("ESC key pressed - canceling recording")
            self.reject()  # Cancel recording
        else:
            super().keyPressEvent(event)
            
    def showEvent(self, event):
        """Handle dialog show event."""
        super().showEvent(event)
        # Ensure dialog gets keyboard focus when shown
        self.activateWindow()
        self.raise_()
        self.setFocus()

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