"""
Validation utilities for Danish Audio Downloader.
"""

import os
import re
from typing import List, Optional


class FileValidator:
    """Utilities for file validation."""
    
    @staticmethod
    def is_valid_audio_file(file_path: str, min_size: int = 1024) -> bool:
        """
        Validate that a file is a valid audio file.
        
        Args:
            file_path: Path to the file to validate
            min_size: Minimum file size in bytes
            
        Returns:
            bool: True if the file is valid, False otherwise
        """
        # Check if file exists
        if not os.path.exists(file_path):
            return False
            
        # Check file size
        try:
            file_size = os.path.getsize(file_path)
            if file_size < min_size:
                return False
        except OSError:
            return False
            
        # Basic validation: check for MP3 headers
        try:
            with open(file_path, 'rb') as f:
                header = f.read(10)
                # Check for ID3 tag or MPEG frame header
                if not (header.startswith(b'ID3') or b'\xff\xfb' in header):
                    return False
        except (OSError, IOError):
            return False
        
        return True
    
    @staticmethod
    def is_valid_directory(path: str, create_if_missing: bool = False) -> bool:
        """
        Validate that a directory exists and is writable.
        
        Args:
            path: Directory path to validate
            create_if_missing: Whether to create the directory if it doesn't exist
            
        Returns:
            bool: True if directory is valid and writable
        """
        if not path:
            return False
            
        # Expand user path
        expanded_path = os.path.expanduser(path)
        
        # Check if directory exists
        if not os.path.exists(expanded_path):
            if create_if_missing:
                try:
                    os.makedirs(expanded_path, exist_ok=True)
                except OSError:
                    return False
            else:
                return False
        
        # Check if it's a directory and writable
        return os.path.isdir(expanded_path) and os.access(expanded_path, os.W_OK)
    
    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
        """
        Validate that a filename has an allowed extension.
        
        Args:
            filename: The filename to validate
            allowed_extensions: List of allowed extensions (e.g., ['.txt', '.mp3'])
            
        Returns:
            bool: True if extension is allowed
        """
        if not filename:
            return False
            
        _, ext = os.path.splitext(filename.lower())
        return ext in [ext.lower() for ext in allowed_extensions]


class TextValidator:
    """Utilities for text validation."""
    
    @staticmethod
    def validate_word_list(text: str) -> List[str]:
        """
        Validate and clean a word list from text input.
        
        Args:
            text: Raw text containing words
            
        Returns:
            List of cleaned, valid words
        """
        if not text:
            return []
        
        # Split by lines and clean each word
        words = []
        for line in text.split('\n'):
            word = line.strip()
            if word and TextValidator.is_valid_danish_word(word):
                words.append(word)
        
        return words
    
    @staticmethod
    def is_valid_danish_word(word: str) -> bool:
        """
        Basic validation for Danish words.
        
        Args:
            word: Word to validate
            
        Returns:
            bool: True if word appears to be valid Danish
        """
        if not word or len(word) > 50:  # Reasonable length limit
            return False
        
        # Allow Danish letters including æ, ø, å
        danish_pattern = re.compile(r'^[a-zA-ZæøåÆØÅ\-\']+$')
        return bool(danish_pattern.match(word))
    
    @staticmethod
    def clean_word(word: str) -> str:
        """
        Clean a word for processing.
        
        Args:
            word: Word to clean
            
        Returns:
            str: Cleaned word
        """
        if not word:
            return ""
        
        # Remove extra whitespace and convert to lowercase
        cleaned = word.strip().lower()
        
        # Remove any invalid characters but keep Danish letters
        cleaned = re.sub(r'[^a-zA-ZæøåÆØÅ\-\']', '', cleaned)
        
        return cleaned


class APIValidator:
    """Utilities for API validation."""
    
    @staticmethod
    def is_valid_openai_api_key(api_key: str) -> bool:
        """
        Basic validation for OpenAI API key format.
        
        Args:
            api_key: API key to validate
            
        Returns:
            bool: True if key format appears valid
        """
        if not api_key:
            return False
        
        # OpenAI API keys typically start with 'sk-' and are 51 characters long
        return (api_key.startswith('sk-') and 
                len(api_key) >= 20 and  # Minimum reasonable length
                api_key.replace('-', '').replace('_', '').isalnum())
    
    @staticmethod
    def validate_cefr_level(level: str) -> bool:
        """
        Validate CEFR level format.
        
        Args:
            level: CEFR level to validate
            
        Returns:
            bool: True if level is valid
        """
        valid_levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        return level.upper() in valid_levels
    
    @staticmethod
    def normalize_cefr_level(level: str) -> Optional[str]:
        """
        Normalize CEFR level to standard format.
        
        Args:
            level: CEFR level to normalize
            
        Returns:
            str: Normalized level or None if invalid
        """
        if not level:
            return None
        
        normalized = level.upper().strip()
        return normalized if APIValidator.validate_cefr_level(normalized) else None
