# OpenAI Personal CLI

A personal command-line interface for interacting with OpenAI's services, including chat with GPT models and image generation with DALL-E.

## Features

- Interactive chat with GPT models
- Image generation with DALL-E 3
- Cross-platform support (Windows, macOS, Linux)

## Setup

### Prerequisites

- Python 3.8 or higher
- OpenAI API key

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/openai-personal-cli.git
   cd openai-personal-cli
   ```

2. Create a virtual environment:
   ```
   # Windows
   python -m venv pyvenv
   
   # macOS/Linux
   python3 -m venv pyvenv
   ```

3. Activate the virtual environment:
   ```
   # Windows
   pyvenv\Scripts\activate
   
   # macOS/Linux
   source pyvenv/bin/activate
   ```

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Create a `.env` file with your OpenAI API key:
   ```
   cp openai-key-example.env .env
   ```
   Then edit the `.env` file to add your API key.

## Usage

### Windows

Run the CLI version:
```
launch_cli.bat
```

Run the GUI version:
```
launch_gui.bat
```

### macOS/Linux

Run the CLI version:
```
./launch_cli.sh
```

Run the GUI version:
```
./launch_gui.sh
```

## CLI Commands

- `/image [prompt]` - Generate an image with DALL-E
- `/exit` - Exit the application

## Settings

You can customize settings in the `settings.json` file, including:
- Chat model and parameters
- Image generation settings
- CLI interface preferences

## License

See the [LICENSE](LICENSE) file for details. 