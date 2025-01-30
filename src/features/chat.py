from typing import List, Dict, Any, Optional
from ..core.api_client import APIClient
from ..core.settings import Settings

class ChatManager:
    def __init__(self, api_client: APIClient, settings: Settings):
        self.api_client = api_client
        self.settings = settings
        self.conversation = [
            {"role": "system", "content": "You are a helpful assistant. You can also generate images using DALL-E 3 when users type '/image' followed by their image description."}
        ]

    def add_message(self, role: str, content: str):
        """Add a message to the conversation history."""
        # Don't add system messages for o1-preview model
        if role == "system" and self.settings.get("chat_settings", "model") == "o1-preview":
            return
        self.conversation.append({"role": role, "content": content})

    def get_response(self, user_input: str) -> Optional[str]:
        """Get response from the AI for user input."""
        self.add_message("user", user_input)
        
        # Create messages list based on model
        model = self.settings.get("chat_settings", "model")
        
        # Handle o1-preview specific settings
        if model == "o1-preview":
            # For o1-preview, exclude system messages and use fixed temperature
            messages = [msg for msg in self.conversation if msg["role"] != "system"]
            temperature = 1  # o1-preview only supports temperature=1
        else:
            messages = self.conversation
            temperature = self.settings.get("chat_settings", "temperature")
        
        response = self.api_client.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature
        )
        
        if response and response.choices:
            assistant_response = response.choices[0].message.content
            self.add_message("assistant", assistant_response)
            return assistant_response
        return None

    def format_conversation(self, messages: List[Dict[str, str]]) -> str:
        """Format conversation messages for context."""
        formatted = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role != "system" and not (
                "Image URL:" in content or 
                "I've generated an image" in content or
                "Please generate an image:" in content or
                content.startswith("/image")
            ):
                formatted.append(f"{role}: {content}")
        return "\n".join(formatted)

    def get_recent_context(self, max_context: int = None) -> List[Dict[str, str]]:
        """Get recent conversation context."""
        if max_context is None:
            max_context = self.settings.get("chat_settings", "max_conversation_history")
        
        # For o1-preview, exclude system messages from context
        if self.settings.get("chat_settings", "model") == "o1-preview":
            messages = [msg for msg in self.conversation if msg["role"] != "system"]
            return messages[-max_context:] if max_context > 0 else messages
        
        return self.conversation[-max_context:] if max_context > 0 else self.conversation 