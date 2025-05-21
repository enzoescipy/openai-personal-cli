from PyQt6.QtCore import QThread, pyqtSignal
from typing import Any, Callable, Optional, List, Dict, Literal
import os
import asyncio # Import asyncio
import inspect # Import inspect

# Import necessary types for hinting, check for circular imports later if issues arise
from ..features.controllers import MainController
from ..features.image import ImageManager
# from ..core.api_client import APIClient # Not directly used in constructors here

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
            # Check if api_call is an async function
            if inspect.iscoroutinefunction(self.api_call):
                # For async functions, run them in the existing asyncio event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If the loop is already running (e.g., from qasync),
                    # we need to schedule the coroutine and wait for its result.
                    # This is tricky from a QThread if the main loop is in the main thread.
                    # A common pattern is to use asyncio.run_coroutine_threadsafe
                    # if the loop is running in a different thread (which it is, the main GUI thread).
                    future = asyncio.run_coroutine_threadsafe(
                        self.api_call(*self.args, **self.kwargs), 
                        loop
                    )
                    result = future.result() # This will block until the coroutine is done.
                else:
                    # This case should ideally not happen if qasync is managing the main loop.
                    # If it does, it means the main loop isn't running, so we can use run_until_complete.
                    result = loop.run_until_complete(self.api_call(*self.args, **self.kwargs))
            else:
                # For regular functions, call them directly
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
    def __init__(self, image_manager: ImageManager, prompt: str, conversation: list):
        # Note: Passing the manager instance might be cleaner than passing the method
        super().__init__(
            image_manager.generate_with_context,
            prompt,
            conversation
        )

class ChatWorker(APIWorker):
    """Worker thread for handling chat messages."""
    def __init__(self, controller: MainController, message: str):
        # We call controller.handle_chat_message which internally calls chat_manager
        super().__init__(
            controller.handle_chat_message, 
            message
        )

class VisionWorker(APIWorker):
    """Worker thread for handling vision analysis."""
    # Vision analysis is also handled by controller.handle_chat_message based on command prefix
    # So it uses the same structure as ChatWorker for now.
    def __init__(self, controller: MainController, command: str):
        super().__init__(
            controller.handle_chat_message, 
            command # The command already contains /vision prefix and args
        ) 