import os
import json
import re
from typing import Dict, Any

class Settings:
    def __init__(self):
        self.settings = self.load_settings()
        
    def load_settings(self) -> Dict[str, Any]:
        default_settings = {
            "chat_settings": {
                "model": "gpt-3.5-turbo",
                "available_models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
                "temperature": 0.7,
                "max_conversation_history": 5
            },
            "vision_settings": {
                "model": "gpt-4o",
                "max_tokens": 1000,
                "detail": "auto",
                "available_details": ["auto", "low", "high"]
            },
            "image_settings": {
                "model": "dall-e-3",
                "size": "1024x1024",
                "available_sizes": ["1024x1024", "1792x1024", "1024x1792"],
                "quality": "standard",
                "available_qualities": ["standard", "hd"],
                "max_context_history": 20,
                "use_raw_prompt": False,
                "prompt_processor": {
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "system_prompt": "You are a creative assistant that helps enhance image generation prompts. Your goal is to make the prompts more detailed and effective for DALL-E image generation while maintaining the user's original intent."
                }
            },
            "voice_settings": {
                "enabled": True,
                "sample_rate": 44100,
                "channels": 1,
                "duration": 5,
                "model": "whisper-1",
                "language": "en"
            },
            "cli_settings": {
                "show_enhanced_prompt": True,
                "save_images_locally": False,
                "images_directory": "generated_images"
            }
        }
        
        try:
            with open('settings.json', 'r') as f:
                content = f.read()
            
            # Remove JSON comments
            content = re.sub(r'//.*?\n|/\*.*?\*/', '', content, flags=re.S)
            user_settings = json.loads(content)
            
            return self._deep_merge(default_settings, user_settings)
            
        except FileNotFoundError:
            print("Warning: settings.json not found. Using default settings.")
            return default_settings
        except json.JSONDecodeError as e:
            print(f"Warning: Error parsing settings.json. Using default settings. Error: {str(e)}")
            return default_settings
        except Exception as e:
            print(f"Warning: Unexpected error loading settings. Using default settings. Error: {str(e)}")
            return default_settings

    def _deep_merge(self, default: Dict, user: Dict) -> Dict:
        """Deep merge two dictionaries."""
        if not isinstance(default, dict) or not isinstance(user, dict):
            return user
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get(self, *keys: str) -> Any:
        """Get a setting value using dot notation."""
        value = self.settings
        for key in keys:
            value = value.get(key)
            if value is None:
                return None
        return value 