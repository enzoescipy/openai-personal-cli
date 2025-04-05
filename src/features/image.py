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
        
        # Normalize prompt (remove /image prefix if present)
        current_prompt = prompt[7:].strip() if prompt.startswith("/image ") else prompt
        
        # Get conversation context
        recent_conversation = conversation[-max_context:]
        
        # Debug: show all messages in conversation
        print("\n대화 컨텍스트 내용:")
        for i, msg in enumerate(recent_conversation):
            if msg["role"] == "user":
                print(f"{i}: User: {msg['content'][:80]}{'...' if len(msg['content']) > 80 else ''}")
            elif msg["role"] == "assistant":
                print(f"{i}: AI: {msg['content'][:50]}{'...' if len(msg['content']) > 50 else ''}")
        
        # Get previous image requests for context
        previous_image_requests = []
        
        # Go through conversation to find previous image requests (recent to old)
        for msg in reversed(recent_conversation):
            if msg["role"] == "user" and msg["content"].startswith("/image "):
                # Extract the content after "/image "
                image_req = msg["content"][7:].strip()
                
                # Don't include the current prompt
                if image_req and image_req != current_prompt:
                    previous_image_requests.insert(0, image_req)  # Add at beginning to preserve order
        
        # Limit to last 3 previous requests for clarity
        previous_image_requests = previous_image_requests[-3:] if len(previous_image_requests) > 3 else previous_image_requests
        
        # Build the context-aware prompt
        context_prefix = ""
        if previous_image_requests:
            # Only include context if we have previous requests
            context_prefix = "Previous image: "
            if len(previous_image_requests) == 1:
                context_prefix += f"{previous_image_requests[0]}. "
            else:
                # Multiple previous requests, list them in progression
                context_prefix += f"{'. Then, '.join(previous_image_requests)}. "
        
        # Form final prompt
        final_prompt = f"{context_prefix}Now, {current_prompt}"
        
        # Debug information
        print("\n이전 이미지 요청들:", previous_image_requests)
        print("최종 이미지 프롬프트:", final_prompt)
        
        # If not using raw prompt, enhance with GPT
        if not use_raw_prompt:
            try:
                enhanced_prompt = self._enhance_prompt_with_gpt(recent_conversation, current_prompt, previous_image_requests)
                if enhanced_prompt:
                    final_prompt = enhanced_prompt
            except Exception as e:
                print(f"Error enhancing prompt with GPT: {e}")
                # Continue with original prompt if enhancement fails
                pass
        
        # Generate image with final prompt
        return self.api_client.generate_image(
            prompt=final_prompt,
            model=self.settings.get("image_settings", "model"),
            size=self.settings.get("image_settings", "size"),
            quality=self.settings.get("image_settings", "quality")
        )
        
    def _enhance_prompt_with_gpt(self, conversation: List[Dict[str, str]], current_prompt: str, 
                               previous_image_requests: List[str]) -> Optional[str]:
        """Enhance the image prompt using GPT."""
        # Create context message
        previous_requests_context = ""
        if previous_image_requests:
            previous_requests_context = "Previous image requests: " + "; ".join(previous_image_requests) + ". "
        
        # Create GPT prompt
        context_messages = [
            {"role": "system", "content": "You are an expert image prompt creator. Your task is to create a detailed, descriptive prompt for DALL-E 3 image generation based on the conversation context and the user's specific request. Focus on visual elements mentioned in the conversation, maintaining the user's intent while adding descriptive details. Create a cohesive scene that captures the essence of what's being discussed."},
            {"role": "user", "content": f"{previous_requests_context}Based on the conversation context and previous image requests, create a detailed prompt for generating this image: {current_prompt}"}
        ]
        
        # Get enhanced prompt from GPT
        response = self.api_client.chat_completion(
            messages=context_messages,
            model=self.settings.get("chat_settings", "model"),
            temperature=self.settings.get("chat_settings", "temperature")
        )
        
        # Extract content safely
        try:
            # Try different ways to access content based on response type
            if hasattr(response, 'choices') and len(response.choices) > 0:
                enhanced_prompt = response.choices[0].message.content
            elif isinstance(response, dict) and 'choices' in response and response['choices']:
                enhanced_prompt = response['choices'][0]['message']['content']
            else:
                return None
            
            if self.settings.get("cli_settings", "show_enhanced_prompt"):
                print("\nEnhanced prompt:", enhanced_prompt)
                
            return enhanced_prompt
        except Exception as e:
            print(f"Error extracting enhanced prompt: {e}")
            return None

    def _format_conversation(self, messages: List[Dict[str, str]]) -> str:
        """Format conversation messages for context."""
        formatted = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                # Skip system messages
                continue
                
            # Handle image URLs and results separately from image requests
            if ("Image URL:" in content or 
                "I've generated an image" in content):
                # Skip image result messages
                continue
            
            # Check if this is an image request and reformat it
            if content.startswith("/image "):
                # Extract the description part after "/image " and keep that
                image_description = content[7:].strip()  # 7 = len("/image ")
                if image_description:
                    formatted.append(f"{role}: {image_description}")
            else:
                # Regular message - include as is
                formatted.append(f"{role}: {content}")
                
        return "\n".join(formatted) 