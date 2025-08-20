"""Settings manager for persistent configuration."""

import os
from PyQt5.QtCore import QSettings


class SettingsManager:
    """Manages application settings using QSettings."""
    
    def __init__(self):
        self.settings = QSettings("TylerLinquata", "DanishAudioDownloader")
    
    def save_settings(self, settings_dict):
        """Save settings dictionary to persistent storage."""
        for key, value in settings_dict.items():
            self.settings.setValue(key, value)
    
    def load_settings(self):
        """Load settings from persistent storage."""
        # Use safe defaults that expand to user directories
        default_output = os.path.expanduser("~/Documents/danish_pronunciations")
        default_anki = os.path.expanduser("~/Library/Application Support/Anki2/User 1/collection.media")
        
        return {
            'output_dir': self.settings.value("output_dir", default_output),
            'anki_dir': self.settings.value("anki_dir", default_anki),
            'openai_api_key': self.settings.value("openai_api_key", ""),
            'forvo_api_key': self.settings.value("forvo_api_key", ""),
            'cefr_level': self.settings.value("cefr_level", "B1"),
            'generate_second_sentence': self.settings.value("generate_second_sentence", True, type=bool)
        }
