"""Settings manager for persistent configuration."""

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
        return {
            'output_dir': self.settings.value("output_dir", ""),
            'anki_dir': self.settings.value("anki_dir", ""),
            'openai_api_key': self.settings.value("openai_api_key", ""),
            'cefr_level': self.settings.value("cefr_level", "B1")
        }
