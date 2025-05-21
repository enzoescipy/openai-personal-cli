import os
from typing import Optional, Dict, Any, Union, Literal, TypedDict, List, cast
# from openai import AsyncOpenAI # 이제 사용 안 함
# from openai.types.chat import ChatCompletion # 이제 사용 안 함
from openai.types.chat import ChatCompletionMessageParam # 이건 계속 사용 (타입 힌트용)
import aiohttp # aiohttp 임포트
import json # JSON 처리를 위해 임포트
from dotenv import load_dotenv
# base64, Path, Image, BytesIO는 이미지/음성 처리용이므로 일단 주석 처리 또는 나중에 제거
# import base64 
# from pathlib import Path
# from PIL import Image
# from io import BytesIO
from .settings import Settings

# ImageUrlContent, ImageUrl, TextContent, UserMessage TypedDict는 일단 유지 (채팅 메시지 구조에 필요할 수 있음)
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
        self.settings = Settings()
        current_provider_name = self.settings.get("api_settings", "current_provider")
        
        provider_settings = self.settings.get("api_settings", "providers", current_provider_name)
        
        if not provider_settings:
            raise ValueError(f"Configuration for provider '{current_provider_name}' not found in settings.")

        self.base_url = provider_settings.get("base_url")
        self.api_key_env_name = provider_settings.get("api_key_env")
        
        if not self.base_url or not self.api_key_env_name:
            raise ValueError(f"base_url or api_key_env not configured for provider '{current_provider_name}'.")
            
        self.api_key = self._load_api_key(self.api_key_env_name)
        
    def _load_api_key(self, api_key_env_name: str) -> str:
        """Load the API key from .env file using the specified environment variable name."""
        load_dotenv('.env')
        api_key = os.getenv(api_key_env_name)
        if not api_key:
            raise ValueError(f"Please set {api_key_env_name} in .env file or environment variables")
        return api_key

    async def chat_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        model: str,
        temperature: float
    ) -> Optional[Dict[str, Any]]: # 반환 타입을 Dict로 변경 (JSON 응답 직접 처리)
        """Get chat completion from OpenAI asynchronously using aiohttp."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        # chat_completions_url = "https://api.openai.com/v1/chat/completions"
        chat_completions_url = f"{self.base_url}/chat/completions"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(chat_completions_url, headers=headers, json=payload) as response:
                    response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
                    return await response.json() # JSON 응답 반환
        except aiohttp.ClientResponseError as e:
            # HTTP 에러 (4xx, 5xx)
            error_content = e.message # 에러 응답 내용 확인 시도
            print(f"\nHTTP Error in chat completion: {e.status} {e.message} - {error_content}")
            return None
        except aiohttp.ClientConnectionError as e:
            # 연결 에러
            print(f"\nConnection Error in chat completion: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            # JSON 파싱 에러
            print(f"\nJSON Decode Error in chat completion: {str(e)}")
            return None
        except Exception as e:
            print(f"\nUnexpected error in chat completion: {str(e)}")
            return None

    async def transcribe_audio(self, audio_file_path: str, model: str, language: str) -> Optional[str]:
        """Transcribe audio using OpenAI's Whisper API."""
        raise NotImplementedError("음성 처리 기능은 현재 비활성화되어 있습니다.")

    async def generate_image(
        self,
        prompt: str,
        model_name: str,
        size: Literal['256x256', '512x512', '1024x1024', '1792x1024', '1024x1792'],
        quality: Literal['standard', 'hd']
    ) -> Optional[str]:
        """Generate image using DALL-E."""
        raise NotImplementedError("이미지 생성 기능은 현재 비활성화되어 있습니다.")

    # _prepare_image 와 _encode_local_image는 이미지 관련이므로 일단 주석 처리 또는 나중에 제거
    # def _prepare_image(self, image_source: str) -> Dict[str, str]:
    #     ...
    # def _encode_local_image(self, image_path: str) -> str:
    #     ...
    
    async def analyze_image(
        self,
        image_source: str,
        prompt: str = "이 이미지를 설명해주세요",
        detail: Optional[Literal['auto', 'low', 'high']] = None
    ) -> Optional[str]:
        """Analyze image using GPT-4 Vision."""
        raise NotImplementedError("이미지 비전 기능은 현재 비활성화되어 있습니다.") 