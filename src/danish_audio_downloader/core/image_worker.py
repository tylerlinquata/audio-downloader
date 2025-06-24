"""
Worker thread for fetching images from dictionary.langeek.co.
"""

import re
import time
import requests
from typing import List, Dict, Optional
from PyQt5.QtCore import QThread, pyqtSignal
from bs4 import BeautifulSoup
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
        """Search for an image on dictionary.langeek.co and other sources."""
        try:
            # Try multiple search strategies
            search_strategies = [
                self._search_langeek_direct,
                self._search_alternative_sources
            ]
            
            for strategy in search_strategies:
                try:
                    result = strategy(english_word)
                    if result:
                        return result
                except Exception as e:
                    self.update_signal.emit(f"Search strategy failed for {english_word}: {str(e)}")
                    continue
            
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
            
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the JSON response
            data = response.json()
            
            # Check if we got results
            if data and isinstance(data, list) and len(data) > 0:
                # Look for the first result that has a photo
                for item in data:
                    if isinstance(item, dict) and 'id' in item:
                        word_id = item['id']
                        # Construct the image URL using the ID
                        image_url = f"https://cdn.langeek.co/photo/{word_id}/original/file?type=jpeg"
                        
                        # Verify the image exists by making a HEAD request
                        try:
                            img_response = requests.head(image_url, headers=headers, timeout=5)
                            if img_response.status_code == 200:
                                return image_url
                        except:
                            # If HEAD request fails, try with PNG
                            try:
                                png_url = f"https://cdn.langeek.co/photo/{word_id}/original/file?type=png"
                                img_response = requests.head(png_url, headers=headers, timeout=5)
                                if img_response.status_code == 200:
                                    return png_url
                            except:
                                continue
            
            return None
            
        except Exception as e:
            self.update_signal.emit(f"Error accessing langeek API for {english_word}: {str(e)}")
            return None

    def _search_alternative_sources(self, english_word: str) -> Optional[str]:
        """Search alternative image sources as fallback."""
        try:
            # Try Wikimedia Commons for educational images
            wikimedia_url = self._search_wikimedia_commons(english_word)
            if wikimedia_url:
                return wikimedia_url
            
            # Try other educational sources
            # For now, we return None to maintain existing behavior
            # but we could add more sources here like:
            # - OpenClipArt
            # - Pixabay (with API key)
            # - Unsplash (with API key)
            
            return None
            
        except Exception:
            return None
    
    def _search_wikimedia_commons(self, english_word: str) -> Optional[str]:
        """Search Wikimedia Commons for educational images."""
        try:
            # Use Wikimedia Commons API to search for images
            api_url = "https://commons.wikimedia.org/w/api.php"
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': f'File:{english_word}',
                'srnamespace': '6',  # File namespace
                'srlimit': '3'
            }
            
            response = requests.get(api_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'query' in data and 'search' in data['query']:
                    for result in data['query']['search']:
                        title = result.get('title', '')
                        if title.startswith('File:'):
                            # Get the actual file URL
                            file_url = self._get_wikimedia_file_url(title)
                            if file_url:
                                return file_url
            
            return None
            
        except Exception:
            return None
    
    def _get_wikimedia_file_url(self, file_title: str) -> Optional[str]:
        """Get the actual URL for a Wikimedia Commons file."""
        try:
            api_url = "https://commons.wikimedia.org/w/api.php"
            params = {
                'action': 'query',
                'format': 'json',
                'titles': file_title,
                'prop': 'imageinfo',
                'iiprop': 'url|size',
                'iiurlwidth': '300'  # Get a reasonably sized thumbnail
            }
            
            response = requests.get(api_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'query' in data and 'pages' in data['query']:
                    for page in data['query']['pages'].values():
                        if 'imageinfo' in page:
                            imageinfo = page['imageinfo'][0]
                            # Prefer thumbnail URL, fallback to full URL
                            return imageinfo.get('thumburl', imageinfo.get('url'))
            
            return None
            
        except Exception:
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
