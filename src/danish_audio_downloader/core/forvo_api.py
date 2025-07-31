"""
Forvo API client for downloading audio pronunciations.
"""

import requests
import json
import time
import os
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode

from ..utils.config import AppConfig, HTTPConfig


class ForvoAPIClient:
    """Client for accessing the Forvo API to download pronunciations."""
    
    def __init__(self, api_key: str, signal_handler: Optional[Any] = None):
        """
        Initialize the Forvo API client.
        
        Args:
            api_key: Forvo API key
            signal_handler: Optional signal handler for GUI communication
        """
        self.api_key = api_key
        self.base_url = AppConfig.FORVO_API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update(HTTPConfig.HEADERS)
        self.signal = signal_handler
        
    def log(self, message: str) -> None:
        """Log a message to the GUI or console."""
        if self.signal:
            self.signal.update_signal.emit(message)
        else:
            print(message)
    
    def get_word_pronunciations(self, word: str, language: str = "da") -> Dict[str, Any]:
        """
        Get pronunciation data for a word from Forvo.
        
        Args:
            word: The word to get pronunciations for
            language: Language code (default: "da" for Danish)
            
        Returns:
            Dict containing pronunciation data or error information
        """
        try:
            # Build the API URL
            params = {
                'key': self.api_key,
                'format': 'json',
                'action': 'word-pronunciations',
                'word': word,
                'language': language
            }
            
            url = f"{self.base_url}/key/{self.api_key}/format/json/action/word-pronunciations/word/{word}/language/{language}/"
            
            self.log(f"Requesting pronunciations for '{word}' from Forvo API")
            
            response = self.session.get(url, timeout=(10, 30))
            response.raise_for_status()
            
            data = response.json()
            
            if 'error' in data:
                self.log(f"Forvo API error for '{word}': {data['error']}")
                return {'success': False, 'error': data['error']}
            
            if 'items' not in data or not data['items']:
                self.log(f"No pronunciations found for '{word}' on Forvo")
                return {'success': False, 'error': 'No pronunciations found'}
            
            self.log(f"Found {len(data['items'])} pronunciation(s) for '{word}'")
            return {'success': True, 'data': data}
            
        except requests.RequestException as e:
            error_msg = f"Request error when fetching pronunciations for '{word}': {str(e)}"
            self.log(error_msg)
            return {'success': False, 'error': error_msg}
        except json.JSONDecodeError as e:
            error_msg = f"JSON decode error for '{word}': {str(e)}"
            self.log(error_msg)
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Unexpected error for '{word}': {str(e)}"
            self.log(error_msg)
            return {'success': False, 'error': error_msg}
    
    def download_best_pronunciation(self, word: str, output_dir: str, language: str = "da") -> Dict[str, Any]:
        """
        Download the best pronunciation for a word.
        
        Args:
            word: The word to download pronunciation for
            output_dir: Directory to save the audio file
            language: Language code (default: "da" for Danish)
            
        Returns:
            Dict containing download result
        """
        result = {'success': False, 'file_path': None, 'error': None}
        
        # Get pronunciations
        pronunciations_result = self.get_word_pronunciations(word, language)
        
        if not pronunciations_result['success']:
            result['error'] = pronunciations_result['error']
            return result
        
        items = pronunciations_result['data']['items']
        
        # Find the best pronunciation (prioritize by votes, then by native speakers)
        best_pronunciation = self._select_best_pronunciation(items)
        
        if not best_pronunciation:
            result['error'] = "No suitable pronunciation found"
            return result
        
        # Download the audio file
        audio_url = best_pronunciation['pathmp3']
        username = best_pronunciation.get('username', 'unknown')
        votes = best_pronunciation.get('num_votes', 0)
        
        self.log(f"Downloading pronunciation by {username} (votes: {votes})")
        
        try:
            # Download the audio
            audio_response = self.session.get(audio_url, stream=True, timeout=(10, 60))
            audio_response.raise_for_status()
            
            # Save the file
            output_path = os.path.join(output_dir, f"{word.lower()}.mp3")
            
            with open(output_path, 'wb') as f:
                for chunk in audio_response.iter_content(chunk_size=AppConfig.CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
            
            # Validate file size
            if os.path.getsize(output_path) < AppConfig.MIN_AUDIO_FILE_SIZE:
                os.remove(output_path)
                result['error'] = "Downloaded file is too small (likely invalid)"
                return result
            
            self.log(f"✅ Successfully downloaded pronunciation for '{word}'")
            result['success'] = True
            result['file_path'] = output_path
            result['pronunciation_info'] = {
                'username': username,
                'votes': votes,
                'country': best_pronunciation.get('country', ''),
                'male': best_pronunciation.get('sex') == 'm'
            }
            
            return result
            
        except requests.RequestException as e:
            error_msg = f"Error downloading audio for '{word}': {str(e)}"
            self.log(error_msg)
            result['error'] = error_msg
            return result
        except Exception as e:
            error_msg = f"Unexpected error downloading '{word}': {str(e)}"
            self.log(error_msg)
            result['error'] = error_msg
            return result
    
    def _select_best_pronunciation(self, pronunciations: List[Dict]) -> Optional[Dict]:
        """
        Select the best pronunciation from a list of options.
        
        Args:
            pronunciations: List of pronunciation dictionaries
            
        Returns:
            Best pronunciation dictionary or None
        """
        if not pronunciations:
            return None
        
        # Filter to only include pronunciations with audio files
        valid_pronunciations = [p for p in pronunciations if p.get('pathmp3')]
        
        if not valid_pronunciations:
            return None
        
        # Sort by priority:
        # 1. Native speakers first (country = "Denmark")
        # 2. More votes is better
        # 3. Newer pronunciations (higher ID)
        def pronunciation_score(p):
            is_native = 1 if p.get('country', '').lower() == 'denmark' else 0
            votes = int(p.get('num_votes', 0))
            pronunciation_id = int(p.get('id', 0))
            
            # Weight: native speakers get priority, then votes, then recency
            return (is_native * 1000) + (votes * 10) + (pronunciation_id * 0.001)
        
        # Sort by score (highest first)
        sorted_pronunciations = sorted(valid_pronunciations, key=pronunciation_score, reverse=True)
        
        return sorted_pronunciations[0]
    
    def download_multiple_words(self, words: List[str], output_dir: str, language: str = "da") -> Dict[str, Any]:
        """
        Download pronunciations for multiple words.
        
        Args:
            words: List of words to download
            output_dir: Directory to save audio files
            language: Language code (default: "da" for Danish)
            
        Returns:
            Dict with success/failure lists and statistics
        """
        successful = []
        failed = []
        total_words = len(words)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        for i, word in enumerate(words):
            # Check for abort signal
            if hasattr(self.signal, 'abort_flag') and self.signal.abort_flag:
                break
            
            self.log(f"Processing {i+1}/{total_words}: {word}")
            
            # Update progress
            if self.signal:
                self.signal.progress_signal.emit(i+1, total_words)
            
            # Try to download the pronunciation
            result = self.download_best_pronunciation(word, output_dir, language)
            
            if result['success']:
                successful.append(word)
                self.log(f"✅ Downloaded: {word}")
            else:
                failed.append(word)
                self.log(f"❌ Failed: {word} - {result['error']}")
            
            # Add delay to avoid rate limiting
            time.sleep(AppConfig.REQUEST_DELAY)
        
        return {
            'successful': successful,
            'failed': failed,
            'total': total_words,
            'success_rate': len(successful) / total_words if total_words > 0 else 0
        }
