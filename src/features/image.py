from typing import Optional, List, Dict, Literal, Sequence
from openai.types.chat import ChatCompletionMessageParam
from ..core.api_client import APIClient
from ..core.settings import Settings
import re
from pathlib import Path

class ImageManager:
    def __init__(self, api_client: APIClient, settings: Settings):
        self.api_client = api_client
        self.settings = settings

    def analyze_image(self, input_source: str, prompt: Optional[str] = None, detail: Optional[Literal['auto', 'low', 'high']] = None) -> Optional[str]:
        """
        Analyze an image from URL or local file path.
        
        Args:
            input_source: URL or file path of the image
            prompt: Custom prompt for image analysis
            detail: Level of detail for analysis
            
        Returns:
            Analysis result or None if error occurs
        """
        # URL 패턴 확인
        url_pattern = re.compile(r'^https?://')
        
        # 입력이 URL인지 확인
        if url_pattern.match(input_source):
            # URL에서 쿼리 파라미터 제거하고 파일 확장자 확인
            base_url = input_source.split('?')[0]
            # 실제 파일 확장자가 없더라도 이미지 타입이면 허용 (blob URL 등)
            if not (base_url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')) or
                   'image/' in input_source.lower()):
                print("Error: URL must point to a supported image file (PNG, JPG, JPEG, GIF, WEBP) or be an image blob")
                return None
        else:
            # 로컬 파일 경로 처리
            file_path = Path(input_source)
            if not file_path.exists():
                print(f"Error: File not found: {input_source}")
                return None
            if not file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                print("Error: Unsupported file format. Please use PNG, JPG, JPEG, GIF, or WEBP")
                return None
        
        try:
            # Vision API 호출
            return self.api_client.analyze_image(
                image_source=input_source,
                prompt=prompt or "이 이미지를 자세히 설명해주세요.",
                detail=detail
            )
        except Exception as e:
            print(f"Error analyzing image: {str(e)}")
            return None

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
        
        # --- Create Conversation Summary (for both raw and enhanced prompt context) ---
        conversation_summary = ""
        # Take last ~5 messages for summary, excluding system/image results
        summary_context_limit = 5 
        relevant_messages = []
        for msg in reversed(recent_conversation):
            role = msg.get("role")
            content = msg.get("content", "")
            # Skip system, image URLs/results, and the current image command itself
            if (role == "system" or 
                "Image URL:" in content or 
                "I've generated an image" in content or 
                (role == "user" and content.startswith("/image") and content[7:].strip() == current_prompt)):
                continue
            # Reformat image requests for context
            if role == "user" and content.startswith("/image"):
                 image_description = content[7:].strip()
                 if image_description:
                     relevant_messages.insert(0, f"User (requested image): {image_description}")
            elif role in ["user", "assistant"]:
                 # Limit content length for summary
                 summary_content = content[:100] + ('...' if len(content) > 100 else '')
                 relevant_messages.insert(0, f"{role.capitalize()}: {summary_content}")
            
            if len(relevant_messages) >= summary_context_limit:
                break
        
        if relevant_messages:
            conversation_summary = "Conversation context: \n" + "\n".join(relevant_messages) + "\n\n"
        # --- End Conversation Summary ---

        # Build the context-aware prompt parts
        context_prefix = ""
        if previous_image_requests:
            # Only include context if we have previous requests
            context_prefix = "Previous image requests: "
            if len(previous_image_requests) == 1:
                context_prefix += f"{previous_image_requests[0]}. "
            else:
                # Multiple previous requests, list them in progression
                context_prefix += f"{'. Then, '.join(previous_image_requests)}. "
        
        # Form final prompt (using summary, previous requests, and current request)
        # This will be the base for both raw and enhanced prompts
        final_prompt = f"{conversation_summary}{context_prefix}Now, generate an image of: {current_prompt}"
        
        # Debug information
        print("\n대화 요약 (프롬프트용):", conversation_summary if conversation_summary else "(없음)")
        print("\n이전 이미지 요청들:", previous_image_requests)
        print("기본 조합 프롬프트:", final_prompt)
        
        # If not using raw prompt, enhance with GPT
        if not use_raw_prompt:
            try:
                enhanced_prompt = self._enhance_prompt_with_gpt(recent_conversation, current_prompt, previous_image_requests)
                if enhanced_prompt:
                    final_prompt = enhanced_prompt # Overwrite with enhanced prompt
                    print("\n향상된 프롬프트 사용:", final_prompt)
            except Exception as e:
                print(f"Error enhancing prompt with GPT: {e}")
                # Continue with original prompt if enhancement fails
                pass
        # No else block needed here, final_prompt already holds the base combination
        
        # Generate image with final prompt
        return self.api_client.generate_image(
            prompt=final_prompt,
            model=self.settings.get("image_settings", "model"),
            size=self.settings.get("image_settings", "size"),
            quality=self.settings.get("image_settings", "quality")
        )
        
    def _enhance_prompt_with_gpt(self, conversation: Sequence[Dict[str, str]], current_prompt: str, 
                               previous_image_requests: List[str]) -> Optional[str]:
        """Enhance the image prompt using GPT."""
        # Create context message for previous requests
        previous_requests_context = ""
        if previous_image_requests:
            previous_requests_context = "Previous image requests: " + "; ".join(previous_image_requests) + ". "
        
        # Prepare conversation history for the prompt enhancement request
        # Filter out system messages if needed, depending on the model (similar logic to ChatManager might be needed)
        # For simplicity now, let's pass the recent conversation directly.
        # We might need to format/filter this further later.
        history_messages = list(conversation) # Make a copy to avoid modifying the original

        # Create the final user prompt for enhancement request
        enhancement_request_prompt = f"{previous_requests_context}Based on the conversation context and previous image requests, create a detailed prompt for generating this image: {current_prompt}"

        # Construct messages for GPT: system + history + final user request
        context_messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": "You are an expert image prompt creator. Your task is to create a detailed, descriptive prompt for DALL-E 3 image generation based on the conversation context and the user's specific request. Focus on visual elements mentioned in the conversation, maintaining the user's intent while adding descriptive details. Create a cohesive scene that captures the essence of what's being discussed."}
        ]
        # Add conversation history
        context_messages.extend(history_messages) # type: ignore
        # Add the final user request
        context_messages.append({"role": "user", "content": enhancement_request_prompt})
        
        # Get enhanced prompt from GPT
        try:
            response = self.api_client.chat_completion(
                messages=context_messages,
                model=self.settings.get("chat_settings", "model"),
                temperature=self.settings.get("chat_settings", "temperature")
            )
            
            # Extract content safely
            if response is None:
                return None
                
            # Try different ways to access content based on response type
            if hasattr(response, 'choices') and response.choices and response.choices[0].message:
                enhanced_prompt = response.choices[0].message.content
            elif isinstance(response, dict) and response.get('choices') and response['choices'][0].get('message', {}).get('content'):
                enhanced_prompt = response['choices'][0]['message']['content']
            else:
                return None
            
            # Removed cli_settings check as it was removed from settings
            # We might add a specific setting for this later if needed
            # print("\nEnhanced prompt:", enhanced_prompt)
                
            return enhanced_prompt
            
        except Exception as e:
            print(f"Error enhancing prompt with GPT: {e}")
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