from typing import List, Dict, Any, Optional, Sequence
from openai.types.chat import ChatCompletionMessageParam
from ..core.api_client import APIClient
from ..core.settings import Settings

class ChatManager:
    def __init__(self, api_client: APIClient, settings: Settings):
        self.api_client = api_client
        self.settings = settings
        self.conversation: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]

    def add_message(self, role: str, content: str):
        """Add a message to the conversation history."""
        # Don't add system messages for o1-preview model
        if role == "system" and self.settings.get("chat_settings", "model") == "o1-preview":
            return
        # Ensure content is a string, as ChatCompletionMessageParam expects str for content
        # However, the type hint List[ChatCompletionMessageParam] should guide usage
        # For safety, if direct dict construction is used elsewhere with non-str content:
        # if not isinstance(content, str):
        #     content = str(content) # Or handle error
        self.conversation.append({"role": role, "content": content} # type: ignore
        )

    async def get_response(self, user_input: str) -> Optional[str]: # async def로 변경
        """Get response from the AI for user input asynchronously."""
        self.add_message("user", user_input)
        
        model_setting = self.settings.get("chat_settings", "model")
        # Ensure model_setting is a string, provide a default or raise error if None/invalid
        model = str(model_setting) if model_setting is not None else "gpt-3.5-turbo" # Example default

        temperature_setting = self.settings.get("chat_settings", "temperature")
        # Ensure temperature_setting is float, provide a default or raise error if None/invalid
        temperature = float(temperature_setting) if isinstance(temperature_setting, (float, int)) else 1.0
        
        messages_for_api = self.conversation
        if model.startswith('o1-'): # Simplified check for o1 models based on previous logic
            messages_for_api = [msg for msg in self.conversation if msg.get("role") != "system"]
            temperature = 1.0  # o1-preview only supports temperature=1
        
        try:
            response_json = await self.api_client.chat_completion(
                messages=messages_for_api, # type: ignore
                model=model,
                temperature=temperature
            )
            
            if response_json is None:
                return None
                
            # Process JSON response from aiohttp
            # Based on OpenAI API structure: response_json['choices'][0]['message']['content']
            if isinstance(response_json, dict) and response_json.get('choices') and \
               isinstance(response_json['choices'], list) and len(response_json['choices']) > 0:
                first_choice = response_json['choices'][0]
                if isinstance(first_choice, dict) and first_choice.get('message') and \
                   isinstance(first_choice['message'], dict):
                    assistant_message_obj = first_choice['message']
                    assistant_response_content = assistant_message_obj.get('content')
                    
                    if assistant_response_content and isinstance(assistant_response_content, str):
                        self.add_message("assistant", assistant_response_content)
                        return assistant_response_content
            
            # If content couldn't be extracted, log for debugging
            error_msg = response_json.get("error", {}).get("message", "Unknown error structure") if isinstance(response_json, dict) else "Invalid response_json format"
            print(f"Could not extract assistant_response. API Response Error: {error_msg} Full Response: {response_json}")
            return None
            
        except Exception as e:
            # Catch any other exceptions during API call or response processing
            print(f"Error in ChatManager.get_response: {e}")
            return None

    def format_conversation(self, messages: Sequence[Dict[str, str]]) -> str:
        """Format conversation messages for context."""
        formatted = []
        for msg in messages:
            role = msg.get("role") # Use .get for safety
            content = msg.get("content") # Use .get for safety
            
            # Ensure role and content are strings before processing
            if not (isinstance(role, str) and isinstance(content, str)):
                continue # Skip malformed messages

            if role != "system" and not (
                "Image URL:" in content or 
                "I've generated an image" in content or
                "Please generate an image:" in content or
                content.startswith("/image") 
            ):
                formatted.append(f"{role}: {content}")
        return "\n".join(formatted)

    def get_recent_context(self, max_context: Optional[int] = None) -> Sequence[ChatCompletionMessageParam]: # Changed return type to Sequence
        """Get recent conversation context."""
        if max_context is None:
            max_context_setting = self.settings.get("chat_settings", "max_conversation_history")
            if not isinstance(max_context_setting, int) or max_context_setting <= 0:
                max_context = 10 # Default to 10 if setting is invalid, not found, or non-positive
            else:
                max_context = max_context_setting
        
        current_model_setting = self.settings.get("chat_settings", "model")
        current_model = str(current_model_setting) if current_model_setting is not None else ""
        
        if current_model.startswith("o1-"):
            messages_to_return = [msg for msg in self.conversation if msg.get("role") != "system"]
        else:
            messages_to_return = list(self.conversation) # Make a copy
        
        return messages_to_return[-max_context:] if max_context > 0 else messages_to_return 