import os
from typing import Optional, Dict, Any, Union, Literal, TypedDict, List, cast
import openai
from openai.types.chat import ChatCompletion
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionUserMessageParam
from dotenv import load_dotenv
import base64
from pathlib import Path
from PIL import Image
from io import BytesIO
import requests
from .settings import Settings

class ImageUrlContent(TypedDict):
    url: str
    detail: str

class ImageUrl(TypedDict):
    type: Literal['image_url']
    image_url: ImageUrlContent

class TextContent(TypedDict):
    type: Literal['text']
    text: str

class UserMessage(TypedDict):
    role: Literal['user']
    content: List[Union[TextContent, ImageUrl]]

class APIClient:
    def __init__(self):
        self.client = self._initialize_client()
        self.settings = Settings()
        self.SUPPORTED_IMAGE_FORMATS = {'jpeg', 'jpg', 'png', 'webp', 'gif'}
        self.MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
        
    def _initialize_client(self) -> openai.Client:
        """Initialize the OpenAI client with API key."""
        load_dotenv('openai-key.env')
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("Please set OPENAI_API_KEY in openai-key.env file")
        return openai.Client(api_key=api_key)

    def chat_completion(
        self, 
        messages: list[ChatCompletionMessageParam],
        model: str,
        temperature: float
    ) -> Optional[ChatCompletion]:
        """Get chat completion from OpenAI."""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return response
        except Exception as e:
            print(f"\nError in chat completion: {str(e)}")
            return None

    def transcribe_audio(self, audio_file_path: str, model: str, language: str) -> Optional[str]:
        """Transcribe audio using OpenAI's Whisper API."""
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    language=language
                )
            return transcript.text
        except Exception as e:
            print(f"\nError transcribing audio: {str(e)}")
            return None

    def generate_image(
        self,
        prompt: str,
        model: str,
        size: Literal['256x256', '512x512', '1024x1024', '1792x1024', '1024x1792'],
        quality: Literal['standard', 'hd']
    ) -> Optional[str]:
        """Generate image using DALL-E."""
        try:
            response = self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
            )
            return response.data[0].url
        except Exception as e:
            print(f"\nError generating image: {str(e)}")
            return None

    def _prepare_image(self, image_source: str) -> Dict[str, str]:
        """
        Prepare image for API submission from various sources (URL, file path, base64).
        
        Args:
            image_source: URL, file path, or base64 string of the image
            
        Returns:
            Dict containing the prepared image URL
            
        Raises:
            ValueError: If image format or size is invalid
            FileNotFoundError: If local image file doesn't exist
        """
        # Handle URL
        if image_source.startswith(('http://', 'https://')):
            return {"url": image_source}
        
        # Handle base64
        if image_source.startswith('data:image/'):
            return {"url": image_source}
        
        # Handle local file
        return {"url": self._encode_local_image(image_source)}
    
    def _encode_local_image(self, image_path: str) -> str:
        """
        Encode local image file to base64 with validation.
        
        Args:
            image_path: Path to local image file
            
        Returns:
            Base64 encoded image URL
            
        Raises:
            ValueError: If image format or size is invalid
            FileNotFoundError: If file doesn't exist
        """
        if not Path(image_path).exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {image_path}")
            
        with Image.open(image_path) as img:
            if img.format is None:
                raise ValueError("이미지 형식을 확인할 수 없습니다")
                
            # Validate format
            img_format = img.format.lower()
            if img_format not in self.SUPPORTED_IMAGE_FORMATS:
                raise ValueError(
                    f"지원하지 않는 이미지 형식입니다. 지원 형식: {', '.join(self.SUPPORTED_IMAGE_FORMATS)}"
                )
            
            # Validate file size
            if Path(image_path).stat().st_size > self.MAX_IMAGE_SIZE:
                raise ValueError(f"이미지 크기가 20MB를 초과합니다")
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format=img_format)
            base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return f"data:image/{img_format};base64,{base64_image}"
    
    def analyze_image(
        self,
        image_source: str,
        prompt: str = "이 이미지를 설명해주세요",
        detail: Optional[Literal['auto', 'low', 'high']] = None
    ) -> Optional[str]:
        """
        Analyze image using GPT-4 Vision.
        
        Args:
            image_source: URL, file path, or base64 string of the image
            prompt: Text prompt for image analysis
            detail: Level of detail for analysis ('auto', 'low', or 'high')
            
        Returns:
            Analysis result text or None if error occurs
            
        Raises:
            ValueError: If image format or size is invalid
            FileNotFoundError: If local image file doesn't exist
        """
        try:
            image_data = self._prepare_image(image_source)
            
            # Get settings
            model = self.settings.get("vision_settings", "model")
            max_tokens = self.settings.get("vision_settings", "max_tokens")
            detail = detail or self.settings.get("vision_settings", "detail")
            
            # Note: We're using Any type here because OpenAI's type system
            # doesn't fully support the vision API message format yet
            messages: Any = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data["url"],
                                "detail": detail
                            }
                        }
                    ]
                }
            ]
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"\nError analyzing image: {str(e)}")
            return None 