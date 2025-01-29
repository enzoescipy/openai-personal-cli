import os
from typing import Optional, Dict, Any
import openai
from dotenv import load_dotenv

class APIClient:
    def __init__(self):
        self.client = self._initialize_client()
        
    def _initialize_client(self) -> openai.Client:
        """Initialize the OpenAI client with API key."""
        load_dotenv('openai-key.env')
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("Please set OPENAI_API_KEY in openai-key.env file")
        return openai.Client(api_key=api_key)

    def chat_completion(self, messages: list, model: str, temperature: float) -> Dict[str, Any]:
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

    def generate_image(self, prompt: str, model: str, size: str, quality: str) -> Optional[str]:
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