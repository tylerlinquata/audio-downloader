"""
Core audio downloader functionality for Danish pronunciations.
"""

import os
import time
from typing import Optional, List, Tuple, Any
import requests
import shutil
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..utils.config import HTTPConfig, AppConfig
from ..utils.validators import FileValidator


class DanishAudioDownloader:
    """Downloads audio pronunciations for Danish words from ordnet.dk."""

    def __init__(self, output_dir: str = "danish_pronunciations", anki_folder: str = "", signal_handler: Optional[Any] = None) -> None:
        """Initialize the downloader with the given output directory."""
        self.output_dir = output_dir
        self.anki_folder = anki_folder
        self.signal = signal_handler
        self.base_url = AppConfig.BASE_URL
        self.session = requests.Session()
        self.session.headers.update(HTTPConfig.HEADERS)
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def log(self, message: str) -> None:
        """Log a message to the GUI."""
        if self.signal:
            self.signal.update_signal.emit(message)
        else:
            print(message)

    def download_audio_for_words(self, words: List[str]) -> Tuple[List[str], List[str]]:
        """
        Download audio files for a list of Danish words.
        
        Args:
            words: List of Danish words to download audio for.
        
        Returns:
            tuple: (list of successful downloads, list of failed downloads)
        """
        successful = []
        failed = []
        
        total_words = len(words)
        
        for i, word in enumerate(words):
            if hasattr(self.signal, 'abort_flag') and self.signal.abort_flag:
                break
                
            self.log(f"Processing {i+1}/{total_words}: {word}")
            
            # Update progress
            if self.signal:
                self.signal.progress_signal.emit(i+1, total_words)
            
            success = False
            retries = 0
            max_retries = AppConfig.MAX_RETRIES
            
            while not success and retries < max_retries:
                try:
                    if self._download_word_audio(word):
                        successful.append(word)
                        success = True
                        self.log(f"✅ Successfully downloaded audio for '{word}'")
                    else:
                        retries += 1
                        if retries >= max_retries:
                            failed.append(word)
                            self.log(f"❌ Failed to find audio for '{word}' after {max_retries} attempts")
                        else:
                            self.log(f"Retrying ({retries}/{max_retries})...")
                            time.sleep(2)  # Wait before retrying
                except Exception as e:
                    self.log(f"Error processing '{word}': {str(e)}")
                    retries += 1
                    if retries >= max_retries:
                        failed.append(word)
                        self.log(f"❌ Failed to download audio for '{word}' after {max_retries} attempts")
                    else:
                        self.log(f"Retrying ({retries}/{max_retries})...")
                        time.sleep(2)  # Wait before retrying
            
            # Add a short delay between requests to avoid rate limiting
            time.sleep(AppConfig.REQUEST_DELAY)
        
        return successful, failed
    
    def _move_to_anki_media(self, file_path: str, word: str) -> bool:
        """
        Move the validated audio file to Anki media collection folder.
        
        Args:
            file_path: Path to the validated audio file
            word: The word for which the audio was downloaded
            
        Returns:
            bool: True if the file was successfully moved, False otherwise
        """
        # If anki_folder is empty, use default
        if not self.anki_folder:
            self.anki_folder = os.path.expanduser("~/Library/Application Support/Anki2/User 1/collection.media")
        
        # Make sure the destination folder exists
        if not os.path.exists(self.anki_folder):
            self.log(f"Error: Anki media folder does not exist: {self.anki_folder}")
            return False
            
        # Create the destination path with the same filename
        dest_path = os.path.join(self.anki_folder, f"{word.lower()}.mp3")
        
        try:
            # Copy the file to the Anki media folder
            shutil.copy2(file_path, dest_path)
            self.log(f"Audio file copied to Anki media folder: {dest_path}")
            return True
        except Exception as e:
            self.log(f"Error copying file to Anki media folder: {str(e)}")
            return False
    
    def _validate_audio_file(self, file_path: str) -> bool:
        """
        Validate that the downloaded file is a valid audio file.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            bool: True if the file is valid, False otherwise
        """
        return FileValidator.is_valid_audio_file(file_path, AppConfig.MIN_AUDIO_FILE_SIZE)
    
    def _download_word_audio(self, word: str) -> bool:
        """
        Download the audio file for a single Danish word from ordnet.dk.
        
        Args:
            word: The Danish word to download audio for.
            
        Returns:
            bool: True if download was successful, False otherwise.
        """
        # Construct the URL for ordnet.dk search
        url = f"{self.base_url}?query={word}"
        self.log(f"Searching for '{word}' at URL: {url}")
        
        try:
            # Get the search results page
            response = self.session.get(url)
            response.raise_for_status()
            self.log(f"Response status: {response.status_code}")
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for pronunciation section
            udtale_div = soup.find('div', id='id-udt')
            if not udtale_div:
                self.log(f"No pronunciation section found for '{word}'")
                return False
            
            # Find all audio fallback links
            audio_links = udtale_div.find_all('a', id=lambda x: x and x.endswith('_fallback'))
            
            if not audio_links:
                self.log(f"No audio links found for '{word}'")
                return False
            
            # Get the first audio URL
            audio_url = audio_links[0].get('href')
            if not audio_url:
                self.log(f"No audio URL found for '{word}'")
                return False
            
            self.log(f"Found audio URL: {audio_url}")
            
            # Make sure we have a full URL
            if not audio_url.startswith('http'):
                audio_url = urljoin('https://ordnet.dk', audio_url)
                self.log(f"Full audio URL: {audio_url}")
            
            # Download the audio file
            self.log(f"Downloading audio file...")
            audio_response = self.session.get(audio_url, stream=True)
            audio_response.raise_for_status()
            
            # Save the file with lowercase name
            output_path = os.path.join(self.output_dir, f"{word.lower()}{AppConfig.AUDIO_FILE_EXTENSION}")
            with open(output_path, 'wb') as f:
                for chunk in audio_response.iter_content(chunk_size=AppConfig.CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
            
            # Validate the downloaded file
            if not self._validate_audio_file(output_path):
                self.log(f"Downloaded file for '{word}' is not valid")
                # Remove invalid file
                os.remove(output_path)
                return False
                
            self.log(f"Audio file saved to {output_path}")
            
            # Move to Anki media folder if path is provided
            if self.anki_folder:
                self._move_to_anki_media(output_path, word)
            
            return True
                
        except requests.RequestException as e:
            self.log(f"Request error for '{word}': {str(e)}")
            return False
        except Exception as e:
            self.log(f"Error processing '{word}': {str(e)}")
            return False
