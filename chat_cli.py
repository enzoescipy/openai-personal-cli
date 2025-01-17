import os
import json
import openai
from dotenv import load_dotenv

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

def chat_with_gpt():
    # Load settings and initialize client
    settings = load_settings()
    client = openai.OpenAI(api_key=load_api_key())
    
    # Store conversation history
    conversation = [
        {"role": "system", "content": "You are a helpful assistant. You can also generate images using DALL-E 3 when users type '/image' followed by their image description."}
    ]
    
    print("Welcome to the OpenAI Chat CLI! (Type 'quit' to exit)")
    print(f"Using Chat Model: {settings['chat_settings']['model']}")
    print(f"Using Image Settings: {settings['image_settings']['size']}, {settings['image_settings']['quality']} quality")
    print("\nSpecial commands:")
    print("- /image [description] : Generate an image using DALL-E 3 (uses conversation context)")
    print("-" * 50)
    
    while True:
        # Get user input
        user_input = input("\nYou: ").strip()
        
        # Check for quit command
        if user_input.lower() in ['quit', 'exit']:
            print("\nGoodbye!")
            break
        
        # try:
        # Check if this is an image generation request
        if user_input.startswith('/image'):
            image_prompt = user_input[6:].strip()  # Remove '/image' and leading space
            if image_prompt:
                print("\nGenerating image (considering conversation context)...")
                image_url = generate_image_with_context(client, image_prompt, conversation, settings)
                print(f"\nImage URL: {image_url}")
                
                # Add to conversation history
                conversation.append({"role": "user", "content": f"Please generate an image: {image_prompt}"})
                conversation.append({"role": "assistant", "content": f"I've generated an image based on your request and our conversation context. You can view it here: {image_url}"})
            else:
                print("\nPlease provide an image description after /image")
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
            
        # except Exception as e:
        #     print(f"\nError: {str(e)}")
        #     continue

if __name__ == "__main__":
    chat_with_gpt()