from PyQt6.QtCore import QThread, pyqtSignal
from typing import Any, Callable, Optional, List, Dict, Literal
import os
import asyncio
import inspect
import traceback # traceback 추가

# Import necessary types for hinting, check for circular imports later if issues arise
from ..features.controllers import MainController
from ..features.image import ImageManager
# from ..core.api_client import APIClient # Not directly used in constructors here

class APIWorker(QThread):
    """Worker thread for API calls."""
    response_ready = pyqtSignal(object)  # Can emit any type of response
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)  # For status updates
    
    def __init__(self, api_call: Callable, main_event_loop: asyncio.AbstractEventLoop, *args, **kwargs): # main_event_loop 추가
        super().__init__()
        self.api_call = api_call
        self.main_event_loop = main_event_loop # 저장
        self.args = args
        self.kwargs = kwargs
        self._is_cancelled = False

    def run(self):
        """Execute the API call in a separate thread."""
        try:
            if inspect.iscoroutinefunction(self.api_call):
                if not self.main_event_loop or self.main_event_loop.is_closed():
                    error_msg = "Main asyncio event loop is not available or closed."
                    print(f"[APIWorker Error] {error_msg}")
                    self.error_occurred.emit(error_msg)
                    return

                future = asyncio.run_coroutine_threadsafe(
                    self.api_call(*self.args, **self.kwargs),
                    self.main_event_loop
                )
                result = future.result()
            else:
                result = self.api_call(*self.args, **self.kwargs)
            
            if not self._is_cancelled:
                self.response_ready.emit(result)
        except Exception as e:
            if not self._is_cancelled:
                error_msg = f"{type(e).__name__}: {str(e)}"
                print(f"[APIWorker Exception] {error_msg}\n{traceback.format_exc()}")
                self.error_occurred.emit(error_msg)

    def cancel(self):
        """Mark the worker as cancelled."""
        self._is_cancelled = True

class ImageGenerationWorker(APIWorker):
    """Worker thread specifically for image generation."""
    def __init__(self, image_manager: ImageManager, prompt: str, conversation: list, main_event_loop: asyncio.AbstractEventLoop):
        # Note: Passing the manager instance might be cleaner than passing the method
        super().__init__(
            image_manager.generate_with_context,
            main_event_loop, # 전달
            prompt,
            conversation
        )

class ChatWorker(APIWorker):
    """Worker thread for handling chat messages."""
    def __init__(self, controller: MainController, message: str, main_event_loop: asyncio.AbstractEventLoop):
        # We call controller.handle_chat_message which internally calls chat_manager
        super().__init__(
            controller.handle_chat_message, 
            main_event_loop, # 전달
            message
        )

class VisionWorker(APIWorker):
    """Worker thread for handling vision analysis."""
    # Vision analysis is also handled by controller.handle_chat_message based on command prefix
    # So it uses the same structure as ChatWorker for now.
    def __init__(self, controller: MainController, command: str, main_event_loop: asyncio.AbstractEventLoop):
        super().__init__(
            controller.handle_chat_message, 
            main_event_loop, # 전달
            command # The command already contains /vision prefix and args
        ) 