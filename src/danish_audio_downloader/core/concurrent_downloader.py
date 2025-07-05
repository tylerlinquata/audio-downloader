"""
Concurrent audio downloader for improved performance.
"""

import os
import time
from typing import List, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from ..utils.config import AppConfig, HTTPConfig
from .downloader import DanishAudioDownloader


class ConcurrentAudioDownloader(DanishAudioDownloader):
    """Concurrent version of the audio downloader for better performance."""
    
    def __init__(self, output_dir: str = "danish_pronunciations", anki_folder: str = "", signal_handler: Optional[Any] = None) -> None:
        super().__init__(output_dir, anki_folder, signal_handler)
        self.max_workers = AppConfig.MAX_CONCURRENT_DOWNLOADS
    
    def download_audio_for_words(self, words: List[str]) -> Tuple[List[str], List[str]]:
        """
        Download audio files for a list of Danish words using concurrent processing.
        
        Args:
            words: List of Danish words to download audio for.
        
        Returns:
            tuple: (list of successful downloads, list of failed downloads)
        """
        if len(words) <= 3:
            # For small batches, use sequential processing to avoid overhead
            return super().download_audio_for_words(words)
        
        self.log(f"Starting concurrent download for {len(words)} words with {self.max_workers} workers")
        
        successful = []
        failed = []
        completed_count = 0
        total_words = len(words)
        
        # Use ThreadPoolExecutor for concurrent downloads
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all download tasks
            future_to_word = {
                executor.submit(self._download_word_with_retries, word): word 
                for word in words
            }
            
            # Process completed downloads
            for future in as_completed(future_to_word):
                if hasattr(self.signal, 'abort_flag') and self.signal.abort_flag:
                    # Cancel remaining futures
                    for f in future_to_word:
                        f.cancel()
                    break
                
                word = future_to_word[future]
                completed_count += 1
                
                try:
                    success = future.result()
                    if success:
                        successful.append(word)
                        self.log(f"✅ [{completed_count}/{total_words}] Downloaded: {word}")
                    else:
                        failed.append(word)
                        self.log(f"❌ [{completed_count}/{total_words}] Failed: {word}")
                except Exception as e:
                    failed.append(word)
                    self.log(f"❌ [{completed_count}/{total_words}] Error with {word}: {str(e)}")
                
                # Update progress
                if self.signal:
                    self.signal.progress_signal.emit(completed_count, total_words)
        
        self.log(f"Concurrent download complete: {len(successful)} successful, {len(failed)} failed")
        return successful, failed
    
    def _download_word_with_retries(self, word: str) -> bool:
        """Download audio for a single word with retry logic."""
        max_retries = AppConfig.MAX_RETRIES
        
        for attempt in range(max_retries):
            try:
                result = self._download_word_audio(word)
                if result['success']:
                    # Store dictionary data for later use
                    if result.get('dictionary_data'):
                        self.word_dictionary_data[word] = result['dictionary_data']
                    return True
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
            except Exception as e:
                if attempt == max_retries - 1:
                    self.log(f"Final attempt failed for {word}: {str(e)}")
                else:
                    time.sleep(0.5 * (attempt + 1))
        
        return False
