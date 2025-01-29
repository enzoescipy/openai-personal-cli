from typing import Optional, List, Dict
from ..core.api_client import APIClient
from ..core.settings import Settings

class ImageManager:
    def __init__(self, api_client: APIClient, settings: Settings):
        self.api_client = api_client
        self.settings = settings

    def generate_with_context(self, prompt: str, conversation: List[Dict[str, str]]) -> Optional[str]:
        """Generate image with conversation context."""
        max_context = self.settings.get("image_settings", "max_context_history")
        use_raw_prompt = self.settings.get("image_settings", "use_raw_prompt")
        
        # Get conversation context
        recent_conversation = conversation[-max_context:]
        
        if use_raw_prompt:
            final_prompt = self._format_conversation(recent_conversation + [{"role": "user", "content": prompt}])
        else:
            # Create enhanced prompt using conversation context
            context_messages = [
                {"role": "system", "content": "You are a helpful assistant that creates detailed image generation prompts. Based on the conversation context and the user's request, create a detailed prompt for DALL-E 3."},
                {"role": "user", "content": f"Based on this conversation:\n\n{self._format_conversation(recent_conversation)}\n\nCreate a detailed prompt for generating an image with this additional request: {prompt}"}
            ]
            
            try:
                # Get enhanced prompt from GPT
                response = self.api_client.chat_completion(
                    messages=context_messages,
                    model=self.settings.get("chat_settings", "model"),
                    temperature=self.settings.get("chat_settings", "temperature")
                )
                final_prompt = response.choices[0].message.content
                
                if self.settings.get("cli_settings", "show_enhanced_prompt"):
                    print("\nEnhanced prompt:", final_prompt)
            except Exception as e:
                return f"Error generating enhanced prompt: {str(e)}"
        
        # Generate image with final prompt
        return self.api_client.generate_image(
            prompt=final_prompt,
            model=self.settings.get("image_settings", "model"),
            size=self.settings.get("image_settings", "size"),
            quality=self.settings.get("image_settings", "quality")
        )

    def _format_conversation(self, messages: List[Dict[str, str]]) -> str:
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