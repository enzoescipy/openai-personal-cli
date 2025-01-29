from ..core.api_client import APIClient
from ..core.settings import Settings
from .chat import ChatManager
from .voice import VoiceManager
from .image import ImageManager

class MainController:
    """Main controller for the application."""
    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_client = APIClient()
        self.chat_manager = ChatManager(self.api_client, settings)
        self.voice_manager = VoiceManager(self.api_client, settings)
        self.image_manager = ImageManager(self.api_client, settings)

    def handle_chat_message(self, message: str) -> str:
        """Handle a chat message."""
        return self.chat_manager.get_response(message)

    def force_stop(self):
        """Force stop all operations."""
        self.voice_manager.force_stop()

    def cleanup(self):
        """Clean up resources."""
        pass  # Add cleanup if needed
