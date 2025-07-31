"""
Audio provider that uses Forvo API for downloading pronunciations.
"""

import os
import shutil
from typing import Optional, List, Tuple, Any, Dict

from .forvo_api import ForvoAPIClient
from ..utils.config import AppConfig
from ..utils.validators import FileValidator
from ..utils.ordnet_parser import OrdnetParser
import requests
from bs4 import BeautifulSoup
from ..utils.config import HTTPConfig


class ForvoAudioProvider:
    """Audio provider that downloads pronunciations from Forvo API."""
    
    def __init__(self, forvo_api_key: str, output_dir: str = "danish_pronunciations", 
                 anki_folder: str = "", signal_handler: Optional[Any] = None):
        """
        Initialize the Forvo audio provider.
        
        Args:
            forvo_api_key: Forvo API key
            output_dir: Directory to save audio files
            anki_folder: Optional Anki media folder
            signal_handler: Optional signal handler for GUI communication
        """
        self.forvo_client = ForvoAPIClient(forvo_api_key, signal_handler)
        self.output_dir = os.path.expanduser(output_dir)
        self.anki_folder = os.path.expanduser(anki_folder) if anki_folder else ""
        self.signal = signal_handler
        
        # For dictionary data (still using Ordnet)
        self.session = requests.Session()
        self.session.headers.update(HTTPConfig.HEADERS)
        self.base_url = AppConfig.BASE_URL
        
        # Store dictionary data collected during download
        self.word_dictionary_data = {}
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
    
    def log(self, message: str) -> None:
        """Log a message to the GUI."""
        if self.signal:
            self.signal.update_signal.emit(message)
        else:
            print(message)
    
    def download_audio_for_words(self, words: List[str]) -> Tuple[List[str], List[str]]:
        """
        Download audio files for a list of Danish words using Forvo API.
        
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
                    result = self._download_word_audio_and_data(word)
                    if result['success']:
                        successful.append(word)
                        success = True
                        self.log(f"✅ Successfully downloaded audio for '{word}'")
                        # Store dictionary data for later use
                        self.word_dictionary_data[word] = result['dictionary_data']
                    else:
                        retries += 1
                        if retries >= max_retries:
                            failed.append(word)
                            self.log(f"❌ Failed to find audio for '{word}' after {max_retries} attempts")
                            # Store dictionary data even for failed downloads (might have definition)
                            if result.get('dictionary_data'):
                                self.word_dictionary_data[word] = result['dictionary_data']
                        else:
                            self.log(f"Retrying ({retries}/{max_retries})...")
                
                except Exception as e:
                    self.log(f"Error processing '{word}': {str(e)}")
                    retries += 1
                    if retries >= max_retries:
                        failed.append(word)
                        self.log(f"❌ Failed to download audio for '{word}' after {max_retries} attempts")
        
        return successful, failed
    
    def _download_word_audio_and_data(self, word: str) -> Dict:
        """
        Download audio from Forvo and dictionary data from Ordnet for a single word.
        
        Args:
            word: The Danish word to process.
            
        Returns:
            dict: Result containing success status and dictionary data
        """
        result = {
            'success': False,
            'dictionary_data': None
        }
        
        # First, get dictionary data from Ordnet (we still want this)
        self.log(f"Fetching dictionary data for '{word}' from Ordnet...")
        dictionary_data = self._get_ordnet_dictionary_data(word)
        result['dictionary_data'] = dictionary_data
        
        # Log dictionary data extraction
        if dictionary_data and dictionary_data.get('ordnet_found'):
            self.log(f"✅ Extracted dictionary data for '{word}'")
            if dictionary_data.get('danish_definition'):
                self.log(f"   Definition: {dictionary_data['danish_definition'][:100]}...")
            if dictionary_data.get('word_type'):
                self.log(f"   Type: {dictionary_data['word_type']}")
            if dictionary_data.get('pronunciation'):
                self.log(f"   Pronunciation: {dictionary_data['pronunciation']}")
        else:
            self.log(f"⚠️  No dictionary data found for '{word}' - {dictionary_data.get('error', 'Unknown error') if dictionary_data else 'Failed to fetch'}")
        
        # Now download audio from Forvo
        self.log(f"Downloading audio for '{word}' from Forvo...")
        forvo_result = self.forvo_client.download_best_pronunciation(word, self.output_dir)
        
        if not forvo_result['success']:
            self.log(f"❌ Forvo download failed: {forvo_result['error']}")
            return result
        
        # Validate the audio file
        audio_file_path = forvo_result['file_path']
        if not self._validate_audio_file(audio_file_path):
            self.log(f"Downloaded file for '{word}' is not valid")
            if os.path.exists(audio_file_path):
                os.remove(audio_file_path)
            return result
        
        self.log(f"Audio file saved to {audio_file_path}")
        
        # Move to Anki media folder if path is provided
        if self.anki_folder:
            self._move_to_anki_media(audio_file_path, word)
        
        # Log pronunciation info
        if 'pronunciation_info' in forvo_result:
            info = forvo_result['pronunciation_info']
            self.log(f"   Pronounced by: {info['username']} ({info['country']})")
            self.log(f"   Votes: {info['votes']}")
        
        result['success'] = True
        return result
    
    def _get_ordnet_dictionary_data(self, word: str) -> Dict:
        """
        Get dictionary data from Ordnet for a word.
        
        Args:
            word: The word to look up
            
        Returns:
            Dictionary data from Ordnet
        """
        try:
            # Construct the URL for ordnet.dk search
            url = f"{self.base_url}?query={word}"
            
            # Get the search results page
            response = self.session.get(url, timeout=(10, 30))
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract dictionary data
            return OrdnetParser.parse_word_data(soup, word)
            
        except Exception as e:
            self.log(f"Error fetching dictionary data for '{word}': {str(e)}")
            return {'ordnet_found': False, 'error': str(e)}
    
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
    
    def get_dictionary_data(self) -> Dict[str, Dict]:
        """
        Get the dictionary data collected during the download process.
        
        Returns:
            dict: Dictionary mapping words to their dictionary data
        """
        return self.word_dictionary_data
