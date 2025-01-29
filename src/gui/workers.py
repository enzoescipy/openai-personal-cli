from PyQt6.QtCore import QThread, pyqtSignal
from typing import Any, Callable, Optional
import os

class APIWorker(QThread):
    """Worker thread for API calls."""
    response_ready = pyqtSignal(object)  # Can emit any type of response
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)  # For status updates
    
    def __init__(self, api_call: Callable, *args, **kwargs):
        super().__init__()
        self.api_call = api_call
        self.args = args
        self.kwargs = kwargs
        self._is_cancelled = False

    def run(self):
        """Execute the API call in a separate thread."""
        try:
            result = self.api_call(*self.args, **self.kwargs)
            if not self._is_cancelled:
                self.response_ready.emit(result)
        except Exception as e:
            if not self._is_cancelled:
                self.error_occurred.emit(str(e))

    def cancel(self):
        """Mark the worker as cancelled."""
        self._is_cancelled = True

class ImageGenerationWorker(APIWorker):
    """Worker thread specifically for image generation."""
    def __init__(self, image_manager, prompt: str, conversation: list):
        super().__init__(
            image_manager.generate_with_context,
            prompt,
            conversation
        ) 