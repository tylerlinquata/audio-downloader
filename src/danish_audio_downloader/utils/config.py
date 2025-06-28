"""
Configuration management utilities for Danish Audio Downloader.
"""

import os
from PyQt5.QtCore import QSettings


class AppConfig:
    """Configuration manager for the Danish Audio Downloader application."""
    
    # Application constants
    APP_NAME = "Danish Audio Downloader"
    APP_VERSION = "1.0.0"
    ORGANIZATION = "TylerLinquata"
    APP_IDENTIFIER = "DanishAudioDownloader"
    
    # Default settings
    DEFAULT_OUTPUT_DIR = "~/Documents/danish_pronunciations"
    DEFAULT_ANKI_FOLDER = "~/Library/Application Support/Anki2/User 1/collection.media"
    DEFAULT_CEFR_LEVEL = "B1"
    
    # API settings
    OPENAI_MODEL = "gpt-4o-mini"
    OPENAI_MAX_TOKENS = 800
    OPENAI_TEMPERATURE = 0.7
    
    # Download settings
    MAX_RETRIES = 3
    REQUEST_DELAY = 1  # seconds between requests
    CHUNK_SIZE = 1024  # for file downloads
    MIN_AUDIO_FILE_SIZE = 1024  # minimum size for valid audio file
    
    # URLs
    BASE_URL = "https://ordnet.dk/ddo/ordbog"
    
    # File patterns
    AUDIO_FILE_EXTENSION = ".mp3"
    FAILED_WORDS_FILENAME = "failed_words.txt"
    SENTENCES_FILENAME = "danish_example_sentences.txt"
    
    def __init__(self):
        """Initialize configuration manager."""
        self.settings = QSettings(self.ORGANIZATION, self.APP_IDENTIFIER)
    
    def get_output_dir(self) -> str:
        """Get the output directory setting."""
        default_path = os.path.expanduser(self.DEFAULT_OUTPUT_DIR)
        return self.settings.value("output_dir", default_path)
    
    def set_output_dir(self, path: str) -> None:
        """Set the output directory setting."""
        self.settings.setValue("output_dir", path)
    
    def get_anki_dir(self) -> str:
        """Get the Anki media directory setting."""
        default_path = os.path.expanduser(self.DEFAULT_ANKI_FOLDER)
        return self.settings.value("anki_dir", default_path)
    
    def set_anki_dir(self, path: str) -> None:
        """Set the Anki media directory setting."""
        self.settings.setValue("anki_dir", path)
    
    def get_openai_api_key(self) -> str:
        """Get the OpenAI API key setting."""
        return self.settings.value("openai_api_key", "")
    
    def set_openai_api_key(self, key: str) -> None:
        """Set the OpenAI API key setting."""
        self.settings.setValue("openai_api_key", key)
    
    def get_cefr_level(self) -> str:
        """Get the CEFR level setting."""
        return self.settings.value("cefr_level", self.DEFAULT_CEFR_LEVEL)
    
    def set_cefr_level(self, level: str) -> None:
        """Set the CEFR level setting."""
        self.settings.setValue("cefr_level", level)
    
    def get_all_settings(self) -> dict:
        """Get all settings as a dictionary."""
        return {
            "output_dir": self.get_output_dir(),
            "anki_dir": self.get_anki_dir(),
            "openai_api_key": self.get_openai_api_key(),
            "cefr_level": self.get_cefr_level()
        }
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        self.settings.clear()


class HTTPConfig:
    """HTTP configuration for web requests."""
    
    # User agent string
    USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36')
    
    # Request headers
    HEADERS = {
        'User-Agent': USER_AGENT,
        'Accept-Language': 'en-US,en;q=0.9,da;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    }
    
    # Request timeouts (in seconds)
    CONNECT_TIMEOUT = 10
    READ_TIMEOUT = 30
    
    @classmethod
    def get_session_config(cls) -> dict:
        """Get configuration for requests.Session."""
        return {
            'headers': cls.HEADERS,
            'timeout': (cls.CONNECT_TIMEOUT, cls.READ_TIMEOUT)
        }
