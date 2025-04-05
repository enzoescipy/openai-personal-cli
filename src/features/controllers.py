from ..core.api_client import APIClient
from ..core.settings import Settings
from .chat import ChatManager
from .voice import VoiceManager
from .image import ImageManager
from typing import Optional, Literal, cast

class MainController:
    """Main controller for the application."""
    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_client = APIClient()
        self.chat_manager = ChatManager(self.api_client, settings)
        self.voice_manager = VoiceManager(self.api_client, settings)
        self.image_manager = ImageManager(self.api_client, settings)

    def handle_chat_message(self, message: str) -> Optional[str]:
        """Handle a chat message."""
        # Vision 명령어 처리
        if message.startswith("/vision"):
            return self._handle_vision_command(message)
            
        return self.chat_manager.get_response(message)
    
    def _handle_vision_command(self, message: str) -> str:
        """
        Handle vision command for image analysis.
        Format: /vision <url_or_path> [prompt] [--detail=<auto|low|high>]
        """
        # Remove command prefix and split arguments
        args = message[7:].strip().split()
        if not args:
            return "사용법: /vision <url_or_path> [prompt] [--detail=<auto|low|high>]"
        
        # Parse arguments
        image_source = args[0]
        detail: Optional[Literal['auto', 'low', 'high']] = None
        prompt = None
        
        # Process remaining arguments
        remaining_args = args[1:]
        for i, arg in enumerate(remaining_args):
            if arg.startswith("--detail="):
                detail_value = arg.split("=")[1].lower()
                if detail_value in ['auto', 'low', 'high']:
                    detail = cast(Literal['auto', 'low', 'high'], detail_value)
                else:
                    return "Error: detail must be one of: auto, low, high"
            else:
                # If we haven't set prompt yet and this isn't a --detail flag
                if not prompt:
                    # Join all remaining args except --detail as prompt
                    prompt_parts = []
                    for p in remaining_args[i:]:
                        if not p.startswith("--detail="):
                            prompt_parts.append(p)
                    prompt = " ".join(prompt_parts)
                    break
        
        # Analyze image
        try:
            result = self.image_manager.analyze_image(
                input_source=image_source,
                prompt=prompt,
                detail=detail
            )
            return str(result) if result is not None else "이미지 분석 중 오류가 발생했습니다."
        except Exception as e:
            return f"Error analyzing image: {str(e)}"

    def force_stop(self):
        """Force stop all operations."""
        self.voice_manager.force_stop()

    def cleanup(self):
        """Clean up resources."""
        pass  # Add cleanup if needed
