# AudioProcess

AudioProcess is a powerful YouTube audio processing tool that can download audio from YouTube videos, extract subtitles, transcribe content, and generate summaries.

## Features

- **YouTube Audio Downloading**: Download audio from YouTube videos in WebM format
- **Subtitle Extraction**: Extract subtitles from YouTube videos when available
- **Audio Transcription**: Transcribe audio using Alibaba Cloud's speech recognition service
- **Text Summarization**: Generate summaries of subtitle/transcription content using large language models
- **Telegram Bot Integration**: Two Telegram bots for convenient audio downloading and content summarization

## System Requirements

- Python 3.6+
- Required dependencies (see below)

## Dependencies

Main dependencies include:
- yt-dlp (YouTube downloader)
- oss2 (Alibaba Cloud OSS)
- dashscope (Alibaba Cloud AI services)
- python-telegram-bot (Telegram bot integration)
- openai (API for summarization)
- httpx (with SOCKS proxy support)

## Installation

1. Clone the repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Before using the application, you need to set up your configuration:

1. Configure API keys for cloud services in `audioprocess/config/settings.py`
2. Set up your Telegram bot tokens (if using the Telegram bot features)
3. Configure proxy settings if needed

## Usage

### Starting the Bots

Use the `start.sh` script to start both bots (Audio Download Bot and Text Summary Bot):

```bash
./start.sh
```

This will launch:
- **Audio Download Bot**: Downloads audio from YouTube videos when given a URL
- **Text Summary Bot**: Extracts subtitles or transcribes audio from YouTube videos and generates summaries

### Manual Operation

You can also use the core functionality directly:

```python
from audioprocess.main import process_youtube_video

# Process a YouTube video (extract subtitles/transcribe and summarize)
result = process_youtube_video("https://www.youtube.com/watch?v=VIDEO_ID")
```

## Bot Functionality

### Audio Download Bot
- Accepts YouTube URLs
- Downloads audio in the best available quality
- Sends the audio file back to the user via Telegram

### Text Summary Bot
- Accepts YouTube URLs
- Extracts subtitles if available or downloads and transcribes the audio
- Generates and sends back a summary of the content

## Project Structure

- `audioprocess/core/`: Core functionality modules
  - `youtube_downloader.py`: Audio downloading from YouTube
  - `subtitle_extractor.py`: YouTube subtitle extraction
  - `transcription.py`: Audio transcription
  - `summarization.py`: Text summarization
  - `oss_uploader.py`: File uploading to Alibaba Cloud OSS
- `audioprocess/scripts/`: Bot and utility scripts
  - `start_audio_bot.py`: Audio Download Bot script
  - `start_summary_bot.py`: Text Summary Bot script
- `audioprocess/utils/`: Utility functions
- `audioprocess/config/`: Configuration files

## Troubleshooting

### Proxy Issues
- The system can use system-defined proxies or a default proxy if needed
- For SOCKS proxies, ensure `httpx[socks]` is installed

### Telegram Bot Problems
- Verify your bot tokens are correct
- Ensure your user ID is in the allowed users list if access is restricted

## License

This project is for personal use.

## Credits

Developed by CC. 