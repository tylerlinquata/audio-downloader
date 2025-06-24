"""
Worker thread for fetching images from langeek.co only.
"""

import re
import time
import requests
from typing import List, Dict, Optional
from PyQt5.QtCore import QThread, pyqtSignal
import openai

from ..utils.config import AppConfig


class ImageWorker(QThread):
    """Worker thread for fetching images for Danish words from langeek.co."""
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(dict)  # word -> image_url mapping
    error_signal = pyqtSignal(str)  # error message

    def __init__(self, word_translations: Dict[str, str], api_key: str) -> None:
        """
        Initialize the image worker.
        
        Args:
            word_translations: Dictionary mapping Danish words to their English translations
            api_key: OpenAI API key for getting English translations if needed
        """
        super().__init__()
        self.word_translations = word_translations
        self.api_key = api_key
        self.abort_flag = False

    def run(self) -> None:
        """Run the image fetching process."""
        try:
            # Set up OpenAI client for missing translations
            openai.api_key = self.api_key
            client = openai.OpenAI(api_key=self.api_key)
            
            image_urls = {}
            total_words = len(self.word_translations)
            
            for i, (danish_word, english_translation) in enumerate(self.word_translations.items()):
                if self.abort_flag:
                    break
                    
                self.update_signal.emit(f"Fetching image for: {danish_word}")
                self.progress_signal.emit(i + 1, total_words)
                
                # Get English translation if not provided
                if not english_translation:
                    english_translation = self._get_english_translation(client, danish_word)
                
                if english_translation:
                    # Search for image on langeek.co
                    image_url = self._search_langeek_image(english_translation)
                    if image_url:
                        image_urls[danish_word] = image_url
                        self.update_signal.emit(f"✓ Found image for {danish_word}: {image_url}")
                    else:
                        self.update_signal.emit(f"⚠ No suitable image found for {danish_word} (will use placeholder)")
                        image_urls[danish_word] = None
                else:
                    self.update_signal.emit(f"⚠ Could not get English translation for {danish_word}")
                    image_urls[danish_word] = None
                
                # Add a small delay to be respectful to the website
                time.sleep(1)
                    
            if not self.abort_flag:
                self.finished_signal.emit(image_urls)
            
        except Exception as e:
            self.error_signal.emit(f"Failed to fetch images: {str(e)}")

    def _get_english_translation(self, client, danish_word: str) -> Optional[str]:
        """Get English translation for a Danish word using ChatGPT."""
        try:
            prompt = f"Translate this single Danish word to English. Provide only the most common English translation, nothing else: {danish_word}"
            
            response = client.chat.completions.create(
                model=AppConfig.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a translator. Provide only the most common English translation of Danish words."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            translation = response.choices[0].message.content.strip()
            # Remove any extra text, keep only the first word/phrase
            translation = translation.split(',')[0].split('.')[0].strip()
            return translation.lower()
            
        except Exception as e:
            self.update_signal.emit(f"Error getting translation for {danish_word}: {str(e)}")
            return None

    def _search_langeek_image(self, english_word: str) -> Optional[str]:
        """Search for an image on langeek.co."""
        try:
            # Search using langeek direct API
            self.update_signal.emit(f"Searching langeek for: {english_word}")
            result = self._search_langeek_direct(english_word)
            if result:
                self.update_signal.emit(f"Langeek search successful: {result}")
                return result
            
            # If no images found, log this but don't error
            self.update_signal.emit(f"No suitable images found for: {english_word}")
            return None
            
        except Exception as e:
            self.update_signal.emit(f"Error searching image for {english_word}: {str(e)}")
            return None

    def _search_langeek_direct(self, english_word: str) -> Optional[str]:
        """Search for an image using the langeek.co API."""
        try:
            # Use the langeek API to search for the word
            api_url = f"https://api.langeek.co/v1/cs/en/word/?term={english_word}&filter=,inCategory,photo"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive'
            }
            
            self.update_signal.emit(f"Making API request to: {api_url}")
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the JSON response
            data = response.json()
            
            self.update_signal.emit(f"API response: {len(data) if isinstance(data, list) else 'Not a list'} results")
            
            # Check if we got results
            if data and isinstance(data, list) and len(data) > 0:
                # Look for the first result that has a photo
                for item in data:
                    if isinstance(item, dict):
                        # Check if the item has a translation with wordPhoto
                        translation = item.get('translation', {})
                        if translation and isinstance(translation, dict):
                            word_photo = translation.get('wordPhoto')
                            if word_photo and isinstance(word_photo, dict):
                                photo_url = word_photo.get('photo')
                                if photo_url:
                                    # Verify the image exists by making a HEAD request
                                    try:
                                        self.update_signal.emit(f"Checking image URL: {photo_url}")
                                        img_response = requests.head(photo_url, headers=headers, timeout=5)
                                        self.update_signal.emit(f"Image check status: {img_response.status_code}")
                                        if img_response.status_code == 200:
                                            return photo_url
                                    except Exception as e:
                                        self.update_signal.emit(f"Image check failed: {str(e)}")
                                        continue
                        
                        # Also check in translations.noun if main translation doesn't have photo
                        translations = item.get('translations', {})
                        if translations and isinstance(translations, dict):
                            noun_translations = translations.get('noun', [])
                            if noun_translations and isinstance(noun_translations, list):
                                for noun_trans in noun_translations:
                                    if isinstance(noun_trans, dict):
                                        word_photo = noun_trans.get('wordPhoto')
                                        if word_photo and isinstance(word_photo, dict):
                                            photo_url = word_photo.get('photo')
                                            if photo_url:
                                                # Verify the image exists
                                                try:
                                                    self.update_signal.emit(f"Checking noun image URL: {photo_url}")
                                                    img_response = requests.head(photo_url, headers=headers, timeout=5)
                                                    self.update_signal.emit(f"Noun image check status: {img_response.status_code}")
                                                    if img_response.status_code == 200:
                                                        return photo_url
                                                except Exception as e:
                                                    self.update_signal.emit(f"Noun image check failed: {str(e)}")
                                                    continue
            
            self.update_signal.emit("No valid images found in API response")
            return None
            
        except Exception as e:
            self.update_signal.emit(f"Error accessing langeek API for {english_word}: {str(e)}")
            return None

    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL looks like a valid image URL."""
        if not url:
            return False
        
        # Check for image file extensions
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        url_lower = url.lower()
        
        # Direct extension check
        if any(url_lower.endswith(ext) for ext in image_extensions):
            return True
        
        # Check for image URLs that might not have extensions
        if 'image' in url_lower or 'img' in url_lower:
            return True
        
        # Langeek-specific patterns
        if 'langeek.co/assets/img/' in url_lower:
            return True
        
        return False

    def abort(self) -> None:
        """Abort the image fetching process."""
        self.abort_flag = True
        self.update_signal.emit("Aborting image fetching...")
