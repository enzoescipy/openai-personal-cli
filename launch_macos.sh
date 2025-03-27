#!/bin/bash
# modify this path as the repository folder position
cd /Users/godonghyo/Documents/project_repository/openai-personal-cli

# Set Qt environment variables for Apple Silicon
export QT_MAC_WANTS_LAYER=1
export QT_AUTO_SCREEN_SCALE_FACTOR=1
export QT_ENABLE_HIGHDPI_SCALING=1

# Get Qt path from Homebrew
export QT_PATH=$(brew --prefix qt@6)
export PATH="$QT_PATH/bin:$PATH"

# Activate virtual environment
source pyvenv/bin/activate

# Run the macOS-specific version
python main_macos.py 