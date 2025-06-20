#!/usr/bin/env python3
"""
Danish Word Audio Downloader (Simple Version)

This script downloads audio pronunciations for Danish words from ordnet.dk using requests.
It takes a list of Danish words, searches for them on ordnet.dk, and downloads
the corresponding audio files if they exist.
"""

import os
import re
import time
import requests
import argparse
import shutil
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class DanishAudioDownloader:
    def __init__(self, output_dir="danish_pronunciations", copy_to_anki=True):
        """Initialize the downloader with the given output directory."""
        self.output_dir = output_dir
        self.copy_to_anki = copy_to_anki
        self.base_url = "https://ordnet.dk/ddo/ordbog"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,da;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        })
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def download_audio_for_words(self, words, max_retries=3):
        """
        Download audio files for a list of Danish words.
        
        Args:
            words: List of Danish words to download audio for.
            max_retries: Maximum number of retries if a download fails.
        
        Returns:
            tuple: (list of successful downloads, list of failed downloads)
        """
        successful = []
        failed = []
        
        total_words = len(words)
        
        for i, word in enumerate(words):
            print(f"Processing {i+1}/{total_words}: {word}")
            
            success = False
            retries = 0
            
            while not success and retries < max_retries:
                try:
                    if self._download_word_audio(word):
                        successful.append(word)
                        success = True
                        print(f"✅ Successfully downloaded audio for '{word}'")
                    else:
                        retries += 1
                        if retries >= max_retries:
                            failed.append(word)
                            print(f"❌ Failed to find audio for '{word}' after {max_retries} attempts")
                        else:
                            print(f"Retrying ({retries}/{max_retries})...")
                            time.sleep(2)  # Wait before retrying
                except Exception as e:
                    print(f"Error processing '{word}': {str(e)}")
                    retries += 1
                    if retries >= max_retries:
                        failed.append(word)
                        print(f"❌ Failed to download audio for '{word}' after {max_retries} attempts")
                    else:
                        print(f"Retrying ({retries}/{max_retries})...")
                        time.sleep(2)  # Wait before retrying
            
            # Add a short delay between requests to avoid rate limiting
            time.sleep(1)
        
        return successful, failed
    
    def _move_to_anki_media(self, file_path, word):
        """
        Move the validated audio file to Anki media collection folder.
        
        Args:
            file_path: Path to the validated audio file
            word: The word for which the audio was downloaded
            
        Returns:
            bool: True if the file was successfully moved, False otherwise
        """
        anki_media_folder = "/Users/tylerjosephlinquata/Library/Application Support/Anki2/User 1/collection.media"
        
        # Make sure the destination folder exists
        if not os.path.exists(anki_media_folder):
            print(f"Error: Anki media folder does not exist: {anki_media_folder}")
            return False
            
        # Create the destination path with the same filename
        dest_path = os.path.join(anki_media_folder, f"{word.lower()}.mp3")
        
        try:
            # Copy the file to the Anki media folder
            shutil.copy2(file_path, dest_path)
            print(f"Audio file copied to Anki media folder: {dest_path}")
            return True
        except Exception as e:
            print(f"Error copying file to Anki media folder: {str(e)}")
            return False
    
    def _validate_audio_file(self, file_path):
        """
        Validate that the downloaded file is a valid audio file.
        Simple validation that just checks file size.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            bool: True if the file is valid, False otherwise
        """
        # Check if file exists and has content
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} does not exist")
            return False
            
        # Check file size (should be at least 1KB for a valid audio file)
        file_size = os.path.getsize(file_path)
        if file_size < 1024:
            print(f"Error: File {file_path} is too small ({file_size} bytes)")
            return False
            
        # Basic validation: mp3 files start with ID3 or have an MPEG frame header
        try:
            with open(file_path, 'rb') as f:
                header = f.read(10)
                if not (header.startswith(b'ID3') or b'\xff\xfb' in header):
                    print(f"Error: File {file_path} does not appear to be a valid MP3 file")
                    return False
        except Exception as e:
            print(f"Error checking file header: {str(e)}")
            return False
        
        return True
    
    def _download_word_audio(self, word):
        """
        Download the audio file for a single Danish word from ordnet.dk.
        
        Args:
            word: The Danish word to download audio for.
            
        Returns:
            bool: True if download was successful, False otherwise.
        """
        # Construct the URL for ordnet.dk search
        url = f"{self.base_url}?query={word}"
        print(f"Searching for '{word}' at URL: {url}")
        
        try:
            # Get the search results page
            response = self.session.get(url)
            response.raise_for_status()
            print(f"Response status: {response.status_code}")
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for pronunciation section
            udtale_div = soup.find('div', id='id-udt')
            if not udtale_div:
                print(f"No pronunciation section found for '{word}'")
                
                # Save the HTML for debugging
                with open(f"{word}_debug.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                print(f"Saved HTML to {word}_debug.html for debugging")
                
                return False
            
            # Find all audio fallback links
            audio_links = udtale_div.find_all('a', id=lambda x: x and x.endswith('_fallback'))
            
            if not audio_links:
                print(f"No audio links found for '{word}'")
                return False
            
            # Get the first audio URL
            audio_url = audio_links[0].get('href')
            if not audio_url:
                print(f"No audio URL found for '{word}'")
                return False
            
            print(f"Found audio URL: {audio_url}")
            
            # Make sure we have a full URL
            if not audio_url.startswith('http'):
                audio_url = urljoin('https://ordnet.dk', audio_url)
                print(f"Full audio URL: {audio_url}")
            
            # Download the audio file
            print(f"Downloading audio file...")
            audio_response = self.session.get(audio_url, stream=True)
            audio_response.raise_for_status()
            
            # Save the file with lowercase name
            output_path = os.path.join(self.output_dir, f"{word.lower()}.mp3")
            with open(output_path, 'wb') as f:
                for chunk in audio_response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            
            # Validate the downloaded file
            if not self._validate_audio_file(output_path):
                print(f"Downloaded file for '{word}' is not valid")
                # Remove invalid file
                os.remove(output_path)
                return False
                
            print(f"Audio file saved to {output_path}")
            
            # Move to Anki media folder if enabled
            if self.copy_to_anki:
                self._move_to_anki_media(output_path, word)
            
            return True
                
        except requests.RequestException as e:
            print(f"Request error for '{word}': {str(e)}")
            return False
        except Exception as e:
            print(f"Error processing '{word}': {str(e)}")
            return False

def main():
    """Main function to handle command-line arguments and run the downloader."""
    parser = argparse.ArgumentParser(description="Download audio pronunciations for Danish words from ordnet.dk")
    parser.add_argument("input_file", help="Text file with Danish words (one per line)")
    parser.add_argument("--output-dir", default="danish_pronunciations", help="Directory to save audio files (default: danish_pronunciations)")
    parser.add_argument("--no-anki", action="store_true", help="Do not copy files to Anki media folder")
    args = parser.parse_args()
    
    # Read the list of words from the input file
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            words = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading input file: {str(e)}")
        return
    
    if not words:
        print("No words found in the input file.")
        return
    
    print(f"Found {len(words)} words to process.")
    
    # Create and run the downloader
    downloader = DanishAudioDownloader(
        output_dir=args.output_dir, 
        copy_to_anki=not args.no_anki
    )
    
    try:
        successful, failed = downloader.download_audio_for_words(words)
        
        print("\nDownload Summary:")
        print(f"Total words: {len(words)}")
        print(f"Successfully downloaded: {len(successful)}")
        print(f"Failed to download: {len(failed)}")
        
        if failed:
            print("\nFailed words:")
            for word in failed:
                print(f"- {word}")
                
            # Save failed words to a file for later retry
            with open("failed_words.txt", "w", encoding="utf-8") as f:
                for word in failed:
                    f.write(f"{word}\n")
            print("\nFailed words have been saved to 'failed_words.txt'")
            
    except KeyboardInterrupt:
        print("\nDownload interrupted by user.")

if __name__ == "__main__":
    main()
