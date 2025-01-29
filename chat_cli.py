import os
import json
import openai
from dotenv import load_dotenv
import sounddevice as sd
import numpy as np
import wave
import tempfile
import keyboard
import threading
import time
import pyperclip  # Add pyperclip import

def load_settings():
    default_settings = {
        "chat_settings": {
            "model": "gpt-3.5-turbo",
            "available_models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
            "temperature": 0.7,
            "max_conversation_history": 5
        },
        "image_settings": {
            "model": "dall-e-3",
            "size": "1024x1024",
            "available_sizes": ["1024x1024", "1792x1024", "1024x1792"],
            "quality": "standard",
            "available_qualities": ["standard", "hd"],
            "max_context_history": 20,
            "use_raw_prompt": True,
            "filter_model": None
        },
        "voice_settings": {
            "enabled": True,
            "sample_rate": 44100,
            "channels": 1,
            "duration": 5,  # seconds
            "model": "whisper-1",
            "language": "en"  # default language
        },
        "cli_settings": {
            "show_enhanced_prompt": True,
            "save_images_locally": False,
            "images_directory": "generated_images"
        }
    }
    
    try:
        # Read the file content
        with open('settings.json', 'r') as f:
            content = f.read()
        
        # Remove JSON comments
        import re
        content = re.sub(r'//.*?\n|/\*.*?\*/', '', content, flags=re.S)
        
        # Parse JSON and merge with defaults
        user_settings = json.loads(content)
        
        # Deep merge user settings with defaults
        def deep_merge(default, user):
            if not isinstance(default, dict) or not isinstance(user, dict):
                return user
            result = default.copy()
            for key, value in user.items():
                if key in result and isinstance(result[key], dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        return deep_merge(default_settings, user_settings)
        
    except FileNotFoundError:
        print("Warning: settings.json not found. Using default settings.")
        return default_settings
    except json.JSONDecodeError as e:
        print(f"Warning: Error parsing settings.json. Using default settings. Error: {str(e)}")
        return default_settings
    except Exception as e:
        print(f"Warning: Unexpected error loading settings. Using default settings. Error: {str(e)}")
        return default_settings

def load_api_key():
    load_dotenv('openai-key.env')
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY in openai-key.env file")
    return api_key

def generate_image_with_context(client, prompt, conversation, settings):
    # Create a context-aware prompt by analyzing recent conversation
    max_context = settings["image_settings"].get("max_context_history", 20)  # Default to 20 if not set
    use_raw_prompt = settings["image_settings"].get("use_raw_prompt", False)
    filter_model = settings["image_settings"].get("filter_model")
    
    # Get conversation context
    recent_conversation = conversation[-max_context:]
    
    if use_raw_prompt:
        final_prompt = format_conversation(recent_conversation + [{"role": "user", "content": prompt}])
    else:
        # Create enhanced prompt using conversation context
        context_messages = [
            {"role": "system", "content": "You are a helpful assistant that creates detailed image generation prompts. Based on the conversation context and the user's request, create a detailed prompt for DALL-E 3."},
            {"role": "user", "content": f"Based on this conversation:\n\n{format_conversation(recent_conversation)}\n\nCreate a detailed prompt for generating an image with this additional request: {prompt}"}
        ]
        
        try:
            # Get enhanced prompt from GPT
            response = client.chat.completions.create(
                model=settings["chat_settings"]["model"],
                messages=context_messages,
                temperature=settings["chat_settings"]["temperature"],
            )
            final_prompt = response.choices[0].message.content
            
            if settings["cli_settings"]["show_enhanced_prompt"]:
                print("\nEnhanced prompt:", final_prompt)
        except Exception as e:
            return f"Error generating enhanced prompt: {str(e)}"
    
    try:
        # print(final_prompt)
        # Generate image with final prompt (either raw or enhanced)
        response = client.images.generate(
            model=settings["image_settings"]["model"],
            prompt=final_prompt,
            size=settings["image_settings"]["size"],
            quality=settings["image_settings"]["quality"],
            n=1,
        )
        
        image_url = response.data[0].url
        
        # Save image locally if enabled
        if settings["cli_settings"]["save_images_locally"]:
            # TODO: Implement local image saving
            pass
            
        return image_url
    except Exception as e:
        return f"Error generating image: {str(e)}"

def format_conversation(messages):
    # Format recent messages for context, filtering out image URLs and commands
    formatted = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        
        # Skip system messages and image-related messages
        if role != "system" and not (
            "Image URL:" in content or 
            "I've generated an image" in content or
            "Please generate an image:" in content or
            content.startswith("/image")
        ):
            formatted.append(f"{role}: {content}")
    return "\n".join(formatted)

def record_audio(settings, stop_processing=None):
    """Record audio using the microphone with spacebar to stop."""
    max_file_size = 25 * 1024 * 1024  # 25MB in bytes
    
    # Flag to control recording
    stop_recording = threading.Event()
    
    # Setup keyboard event
    def on_space():
        stop_recording.set()
    keyboard.on_press_key('space', lambda _: on_space())
    
    try:
        # Calculate buffer size based on audio settings
        bytes_per_sample = 2  # 16-bit audio
        bytes_per_second = settings["voice_settings"]["sample_rate"] * settings["voice_settings"]["channels"] * bytes_per_sample
        max_duration = min(settings["voice_settings"]["duration"], max_file_size / bytes_per_second)
        
        # Start recording
        stream = sd.InputStream(
            samplerate=settings["voice_settings"]["sample_rate"],
            channels=settings["voice_settings"]["channels"],
            dtype=np.int16
        )
        
        # Initialize recording buffer
        frames = []
        current_size = 0
        
        with stream:
            while not stop_recording.is_set() and (stop_processing is None or not stop_processing.is_set()):
                data, _ = stream.read(1024)
                current_size += len(data.tobytes())
                
                # Check size limit
                if current_size >= max_file_size:
                    print("\nReached maximum file size (25MB). Stopping recording...")
                    break
                    
                # Check duration limit
                if len(frames) * settings["voice_settings"]["channels"] / settings["voice_settings"]["sample_rate"] >= max_duration:
                    print(f"\nReached maximum duration ({max_duration:.1f} seconds). Stopping recording...")
                    break
                    
                frames.append(data.copy())
        
        if frames:
            return np.concatenate(frames)
        return None
        
    except Exception as e:
        print(f"\nError recording audio: {str(e)}")
        return None
    finally:
        # Clean up keyboard event
        keyboard.unhook_all()

def save_audio_to_file(recording, settings):
    """Save the recorded audio to a temporary WAV file."""
    if recording is None:
        return None
    
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(settings["voice_settings"]["channels"])
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(settings["voice_settings"]["sample_rate"])
                wf.writeframes(recording.tobytes())
            return temp_file.name
    except Exception as e:
        print(f"\nError saving audio: {str(e)}")
        return None

def transcribe_audio(client, audio_file_path, settings):
    """Transcribe audio using OpenAI's Whisper API."""
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=settings["voice_settings"]["model"],
                file=audio_file,
                language=settings["voice_settings"]["language"]
            )
        return transcript.text
    except Exception as e:
        print(f"\nError transcribing audio: {str(e)}")
        return None
    finally:
        # Clean up the temporary file
        try:
            os.remove(audio_file_path)
        except:
            pass

def enter_voice_copy_mode():
    """Enter the rapid voice copying mode."""
    print("\n🎤 Welcome to OpenAI Whisper-model based voice copying mode!")
    print("This mode will allow you to rapidly record and transcribe voice samples.")
    print("Your voice will be automatically converted to text and copied to clipboard.")
    print("\nInstructions:")
    print("- Press ENTER to start recording")
    print("- Press SPACEBAR to stop recording")
    print("- Press ESC to force-stop (cancels current recording)")
    print("- Type 'exit' to quit this mode")
    
    # Load settings and initialize client
    settings = load_settings()
    client = openai.Client(api_key=load_api_key())
    
    # Flag to control processing
    stop_processing = threading.Event()
    
    def on_escape():
        stop_processing.set()
        print("\n❌ Force stopped!")
    
    while True:
        try:
            stop_processing.clear()  # Reset the stop flag
            command = input("\n⏳ Ready - Press ENTER to start recording (or type 'exit' to quit): ").strip().lower()
            
            if command == 'exit':
                print("\nExiting voice copy mode...")
                break
            
            if command == '':  # User pressed Enter
                # Setup escape key handler
                keyboard.on_press_key('esc', lambda _: on_escape())
                
                print("\n🔴 Recording... (Press SPACEBAR to stop, ESC to cancel)")
                recording = record_audio(settings, stop_processing)
                
                if stop_processing.is_set():
                    keyboard.unhook_all()
                    continue
                
                if recording is not None:
                    print("\n⚙️ Processing audio...")
                    audio_file = save_audio_to_file(recording, settings)
                    
                    if stop_processing.is_set():
                        keyboard.unhook_all()
                        if audio_file:
                            try:
                                os.remove(audio_file)
                            except:
                                pass
                        continue
                    
                    if audio_file:
                        transcription = transcribe_audio(client, audio_file, settings)
                        if transcription:
                            print(f"\n📝 Transcribed text: {transcription}")
                            pyperclip.copy(transcription)
                            print("✨ Text copied to clipboard!")
                        else:
                            print("\n❌ Failed to transcribe audio")
                    else:
                        print("\n❌ Failed to save audio")
                else:
                    print("\n❌ No audio recorded")
                
                # Clean up keyboard hooks
                keyboard.unhook_all()
                    
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            keyboard.unhook_all()  # Ensure keyboard hooks are cleaned up
            continue

def enter_voice_chat_mode(client, settings, conversation):
    """Enter the continuous voice chat mode."""
    print("\n🎤 Welcome to continuous voice chat mode!")
    print("Have a continuous conversation with the AI using your voice.")
    print("\nInstructions:")
    print("- Press ENTER to start recording your message")
    print("- Press SPACEBAR to stop recording")
    print("- Press ESC to force-stop current recording")
    print("- Type 'exit' to quit this mode")
    
    # Flag to control processing
    stop_processing = threading.Event()
    
    def on_escape():
        stop_processing.set()
        print("\n❌ Force stopped!")
    
    while True:
        try:
            stop_processing.clear()  # Reset the stop flag
            command = input("\n⏳ Ready - Press ENTER to speak (or type 'exit' to quit): ").strip().lower()
            
            if command == 'exit':
                print("\nExiting voice chat mode...")
                break
            
            if command == '':  # User pressed Enter
                # Setup escape key handler
                keyboard.on_press_key('esc', lambda _: on_escape())
                
                print("\n🔴 Recording... (Press SPACEBAR to stop, ESC to cancel)")
                recording = record_audio(settings, stop_processing)
                
                if stop_processing.is_set():
                    keyboard.unhook_all()
                    continue
                
                if recording is not None:
                    print("\n⚙️ Processing audio...")
                    audio_file = save_audio_to_file(recording, settings)
                    
                    if stop_processing.is_set():
                        keyboard.unhook_all()
                        if audio_file:
                            try:
                                os.remove(audio_file)
                            except:
                                pass
                        continue
                    
                    if audio_file:
                        transcription = transcribe_audio(client, audio_file, settings)
                        if transcription:
                            print(f"\n📝 You said: {transcription}")
                            
                            # Add user message to conversation
                            conversation.append({"role": "user", "content": transcription})
                            
                            # Get response from OpenAI
                            try:
                                print("\n💭 Assistant is thinking...")
                                response = client.chat.completions.create(
                                    model=settings["chat_settings"]["model"],
                                    messages=conversation,
                                    temperature=settings["chat_settings"]["temperature"],
                                )
                                
                                # Extract and print the assistant's response with clear formatting
                                assistant_response = response.choices[0].message.content
                                print("\n" + "─" * 50)  # Top border
                                print("🤖 Assistant's Response:")
                                print("─" * 50)  # Separator
                                print(assistant_response)
                                print("─" * 50)  # Bottom border
                                
                                # Add assistant's response to conversation history
                                conversation.append({"role": "assistant", "content": assistant_response})
                            except Exception as e:
                                print(f"\n❌ Error getting response: {str(e)}")
                        else:
                            print("\n❌ Failed to transcribe audio")
                    else:
                        print("\n❌ Failed to save audio")
                else:
                    print("\n❌ No audio recorded")
                
                # Clean up keyboard hooks
                keyboard.unhook_all()
                    
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            keyboard.unhook_all()  # Ensure keyboard hooks are cleaned up
            continue

def chat_with_gpt():
    # Load settings and initialize client
    settings = load_settings()
    openai.api_key = load_api_key()
    client = openai.Client()
    conversation = []

    # Store conversation history
    conversation = [
        {"role": "system", "content": "You are a helpful assistant. You can also generate images using DALL-E 3 when users type '/image' followed by their image description."}
    ]
    
    print("Welcome to the OpenAI Chat CLI! (Type 'quit' to exit)")
    print(f"Using Chat Model: {settings['chat_settings']['model']}")
    print(f"Using Image Settings: {settings['image_settings']['size']}, {settings['image_settings']['quality']} quality")
    print("\nSpecial commands:")
    print("- /image [description] : Generate an image using DALL-E 3 (uses conversation context)")
    print("- /image --with_voice (-v) : Generate an image using voice input")
    print("- /voice : Record and transcribe voice input")
    print("- /voice --continuous (-c) : Enter continuous voice chat mode")
    print("- /cpyvoice : Enter the rapid voice copying mode")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() == '/quit':
                break
            elif user_input.lower() == '/cpyvoice':
                enter_voice_copy_mode()
                continue
            elif user_input.lower() in ['/voice --continuous', '/voice -c']:
                enter_voice_chat_mode(client, settings, conversation)
                continue
            
            # Handle voice input
            if user_input == '/voice':
                recording = record_audio(settings)
                if recording is not None:
                    audio_file = save_audio_to_file(recording, settings)
                    if audio_file:
                        transcription = transcribe_audio(client, audio_file, settings)
                        if transcription:
                            print(f"\nTranscribed: {transcription}")
                            user_input = transcription
                        else:
                            continue
                    else:
                        continue
                else:
                    continue
            
            # Check if this is an image generation request
            if user_input.startswith('/image'):
                # Parse voice input flags and additional text
                has_voice = False
                additional_text = ""
                
                parts = user_input[6:].strip().split()  # Split into words after '/image'
                if parts:
                    if parts[0] in ['--with_voice', '-v']:
                        has_voice = True
                        additional_text = ' '.join(parts[1:])  # Get any text after the flag
                    else:
                        image_prompt = user_input[6:].strip()
                
                # Handle voice input if flag is present
                if has_voice:
                    print("\nPlease speak your image description...")
                    recording = record_audio(settings)
                    if recording is not None:
                        audio_file = save_audio_to_file(recording, settings)
                        if audio_file:
                            transcription = transcribe_audio(client, audio_file, settings)
                            if transcription:
                                print(f"\nTranscribed image description: {transcription}")
                                # Combine voice and text inputs if both present
                                image_prompt = f"{transcription}"
                                if additional_text:
                                    print(f"Additional text input: {additional_text}")
                                    image_prompt += f" {additional_text}"
                            else:
                                continue
                        else:
                            continue
                    else:
                        continue
                
                if image_prompt:
                    print("\nGenerating image (considering conversation context)...")
                    image_url = generate_image_with_context(client, image_prompt, conversation, settings)
                    print(f"\nImage URL: {image_url}")
                    
                    # Add to conversation history
                    conversation.append({"role": "user", "content": f"Please generate an image: {image_prompt}"})
                    conversation.append({"role": "assistant", "content": f"I've generated an image based on your request and our conversation context. You can view it here: {image_url}"})
                else:
                    print("\nPlease provide an image description after /image or use voice input")
                continue
            
            # Add user message to conversation
            conversation.append({"role": "user", "content": user_input})
            
            # Get response from OpenAI
            response = client.chat.completions.create(
                model=settings["chat_settings"]["model"],
                messages=conversation,
                temperature=settings["chat_settings"]["temperature"],
            )
            
            # Extract and print the assistant's response
            assistant_response = response.choices[0].message.content
            print("\nAssistant:", assistant_response)
            
            # Add assistant's response to conversation history
            conversation.append({"role": "assistant", "content": assistant_response})
        except Exception as e:
            print(f"\nError in chat loop: {str(e)}")
            continue

if __name__ == "__main__":
    chat_with_gpt()