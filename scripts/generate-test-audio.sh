#!/bin/bash
# Generate a simple test audio file using macOS 'say' command
# This creates a short spoken message for testing ASR

# Create a simple test message
say -o test-media/sample.aiff "Hello world. This is a test of the DHG AI Factory automatic speech recognition system."

# Convert to mp3 if ffmpeg is available
if command -v ffmpeg &> /dev/null; then
    ffmpeg -i test-media/sample.aiff -acodec libmp3lame -ab 128k test-media/sample.mp3 -y 2>&1 | grep -v "^ffmpeg version"
    rm test-media/sample.aiff
    echo "✓ Created test-media/sample.mp3"
else
    echo "✓ Created test-media/sample.aiff (install ffmpeg to convert to mp3)"
fi
