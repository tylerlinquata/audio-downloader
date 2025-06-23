#!/usr/bin/env python3
"""
Danish Word Audio Downloader - GUI Application

A macOS application with a graphical user interface for downloading 
Danish word pronunciations from ordnet.dk and saving them to your Anki collection.
"""

import os
import sys
import re
import time
import requests
import threading
import shutil
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QTextEdit, 
                            QFileDialog, QProgressBar, QCheckBox, QMessageBox,
                            QLineEdit, QGroupBox, QFormLayout, QTabWidget,
                            QComboBox, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon, QFont, QTextCursor
import openai

class Worker(QThread):
    """Worker thread for downloading audio files."""
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(list, list)  # successful, failed

    def __init__(self, words, output_dir, copy_to_anki, anki_folder):
        super().__init__()
        self.words = words
        self.output_dir = output_dir
        self.copy_to_anki = copy_to_anki
        self.anki_folder = anki_folder
        self.abort_flag = False

    def run(self):
        """Run the download process."""
        downloader = DanishAudioDownloader(
            output_dir=self.output_dir,
            anki_folder=self.anki_folder,
            signal_handler=self
        )
        successful, failed = downloader.download_audio_for_words(self.words)
        if not self.abort_flag:
            self.finished_signal.emit(successful, failed)

    def abort(self):
        """Abort the download process."""
        self.abort_flag = True
        self.update_signal.emit("Aborting download process...")


class DanishAudioDownloader:
    """Downloads audio pronunciations for Danish words from ordnet.dk."""

    def __init__(self, output_dir="danish_pronunciations", anki_folder="", signal_handler=None):
        """Initialize the downloader with the given output directory."""
        self.output_dir = output_dir
        self.anki_folder = anki_folder
        self.signal = signal_handler
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

    def log(self, message):
        """Log a message to the GUI."""
        if self.signal:
            self.signal.update_signal.emit(message)
        else:
            print(message)

    def download_audio_for_words(self, words):
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
            max_retries = 3
            
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
            self.log(f"Error: File {file_path} does not exist")
            return False
            
        # Check file size (should be at least 1KB for a valid audio file)
        file_size = os.path.getsize(file_path)
        if file_size < 1024:
            self.log(f"Error: File {file_path} is too small ({file_size} bytes)")
            return False
            
        # Basic validation: mp3 files start with ID3 or have an MPEG frame header
        try:
            with open(file_path, 'rb') as f:
                header = f.read(10)
                if not (header.startswith(b'ID3') or b'\xff\xfb' in header):
                    self.log(f"Error: File {file_path} does not appear to be a valid MP3 file")
                    return False
        except Exception as e:
            self.log(f"Error checking file header: {str(e)}")
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
            output_path = os.path.join(self.output_dir, f"{word.lower()}.mp3")
            with open(output_path, 'wb') as f:
                for chunk in audio_response.iter_content(chunk_size=1024):
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


class SentenceWorker(QThread):
    """Worker thread for generating example sentences using ChatGPT."""
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(str)  # generated sentences
    error_signal = pyqtSignal(str)  # error message

    def __init__(self, words, cefr_level, api_key):
        super().__init__()
        self.words = words
        self.cefr_level = cefr_level
        self.api_key = api_key
        self.abort_flag = False

    def run(self):
        """Run the sentence generation process."""
        try:
            # Set up OpenAI client
            openai.api_key = self.api_key
            client = openai.OpenAI(api_key=self.api_key)
            
            all_sentences = []
            total_words = len(self.words)
            
            for i, word in enumerate(self.words):
                if self.abort_flag:
                    break
                    
                self.update_signal.emit(f"Generating sentences for: {word}")
                self.progress_signal.emit(i + 1, total_words)
                
                # Create the prompt
                prompt = f"""Give me some example sentences for "{word}" in Danish, and give me translations for each sentence. Please make sure that you're pulling these examples from sources that aren't likely to be incorrect or machine-translated; it's better to give me a few correct sentences than a lot of sentences where some may be incorrect. Make sure the sentences are appropriate for a {self.cefr_level} learner.

Format your response like this:
**{word}**

**Example Sentences:**
1. [Danish sentence] - [English translation]
2. [Danish sentence] - [English translation]
3. [Danish sentence] - [English translation]

---"""
                
                try:
                    # Make API call
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful Danish language teacher who provides accurate example sentences and usage tips for Danish words."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=800,
                        temperature=0.7
                    )
                    
                    sentence_content = response.choices[0].message.content
                    all_sentences.append(sentence_content)
                    
                    # Add a small delay to respect rate limits
                    time.sleep(1)
                    
                except Exception as e:
                    error_msg = f"Error generating sentences for '{word}': {str(e)}"
                    self.update_signal.emit(error_msg)
                    all_sentences.append(f"**{word}**\n\nError: Could not generate sentences for this word.\n\n---")
            
            if not self.abort_flag:
                final_result = "\n\n".join(all_sentences)
                self.finished_signal.emit(final_result)
            
        except Exception as e:
            self.error_signal.emit(f"Failed to initialize OpenAI: {str(e)}")

    def abort(self):
        """Abort the sentence generation process."""
        self.abort_flag = True
        self.update_signal.emit("Aborting sentence generation...")


class DanishAudioApp(QMainWindow):
    """Main application window for Danish Audio Downloader."""
    
    def __init__(self):
        super().__init__()
        
        # Set up the UI
        self.init_ui()
        
        # Load settings
        self.settings = QSettings("TylerLinquata", "DanishAudioDownloader")
        self.load_settings()
        
        # Initialize member variables
        self.worker = None
        self.sentence_worker = None
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Danish Word Audio Downloader")
        self.setMinimumSize(800, 600)
        
        # Create tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Create the download tab
        self.download_tab = QWidget()
        self.tabs.addTab(self.download_tab, "Download")
        
        # Create the sentence generation tab
        self.sentences_tab = QWidget()
        self.tabs.addTab(self.sentences_tab, "Example Sentences")
        
        # Create the settings tab
        self.settings_tab = QWidget()
        self.tabs.addTab(self.settings_tab, "Settings")
        
        # Set up the download tab
        self.setup_download_tab()
        
        # Set up the sentence generation tab
        self.setup_sentences_tab()
        
        # Set up the settings tab
        self.setup_settings_tab()
        
    def setup_download_tab(self):
        """Set up the download tab UI."""
        layout = QVBoxLayout()
        
        # Word input area
        word_group = QGroupBox("Words to Download")
        word_layout = QVBoxLayout()
        
        # Text area for words
        self.word_input = QTextEdit()
        self.word_input.setPlaceholderText("Enter Danish words, one per line")
        word_layout.addWidget(self.word_input)
        
        # Load from file button
        load_button = QPushButton("Load from File")
        load_button.clicked.connect(self.load_from_file)
        word_layout.addWidget(load_button)
        
        word_group.setLayout(word_layout)
        layout.addWidget(word_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QHBoxLayout()
        
        # Save to Anki checkbox
        self.anki_checkbox = QCheckBox("Copy to Anki Media Folder")
        self.anki_checkbox.setChecked(True)
        options_layout.addWidget(self.anki_checkbox)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Progress area
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        # Log area
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Courier New", 10))
        self.log_output.setMinimumHeight(200)
        progress_layout.addWidget(self.log_output)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Download button
        self.download_button = QPushButton("Start Download")
        self.download_button.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_button)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.download_tab.setLayout(layout)
        
    def setup_sentences_tab(self):
        """Set up the sentence generation tab UI."""
        layout = QVBoxLayout()
        
        # Word input area
        word_group = QGroupBox("Words for Example Sentences")
        word_layout = QVBoxLayout()
        
        # Text area for words
        self.sentence_word_input = QTextEdit()
        self.sentence_word_input.setPlaceholderText("Enter Danish words, one per line")
        self.sentence_word_input.setMaximumHeight(150)
        word_layout.addWidget(self.sentence_word_input)
        
        # Load from file button
        load_sentence_button = QPushButton("Load from File")
        load_sentence_button.clicked.connect(self.load_sentence_words_from_file)
        word_layout.addWidget(load_sentence_button)
        
        word_group.setLayout(word_layout)
        layout.addWidget(word_group)
        
        # Settings group
        settings_group = QGroupBox("Settings")
        settings_layout = QFormLayout()
        
        # CEFR Level dropdown
        self.cefr_combo = QComboBox()
        self.cefr_combo.addItems(["A1", "A2", "B1", "B2", "C1", "C2"])
        self.cefr_combo.setCurrentText("B1")
        settings_layout.addRow("CEFR Level:", self.cefr_combo)
        
        # OpenAI API Key input
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter your OpenAI API key (get one at platform.openai.com)")
        settings_layout.addRow("OpenAI API Key:", self.api_key_input)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Progress area
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        
        # Progress bar
        self.sentence_progress_bar = QProgressBar()
        self.sentence_progress_bar.setValue(0)
        progress_layout.addWidget(self.sentence_progress_bar)
        
        # Log area
        self.sentence_log_output = QTextEdit()
        self.sentence_log_output.setReadOnly(True)
        self.sentence_log_output.setFont(QFont("Courier New", 10))
        self.sentence_log_output.setMaximumHeight(100)
        progress_layout.addWidget(self.sentence_log_output)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Results area
        results_group = QGroupBox("Generated Example Sentences")
        results_layout = QVBoxLayout()
        
        # Results text area (larger and more readable)
        self.sentence_results = QTextEdit()
        self.sentence_results.setReadOnly(True)
        self.sentence_results.setFont(QFont("Georgia", 12))
        self.sentence_results.setMinimumHeight(300)
        results_layout.addWidget(self.sentence_results)
        
        # Save results button
        save_results_button = QPushButton("Save Results to File")
        save_results_button.clicked.connect(self.save_sentence_results)
        results_layout.addWidget(save_results_button)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Generate button
        self.generate_button = QPushButton("Generate Example Sentences")
        self.generate_button.clicked.connect(self.start_sentence_generation)
        button_layout.addWidget(self.generate_button)
        
        # Cancel button
        self.cancel_sentence_button = QPushButton("Cancel")
        self.cancel_sentence_button.clicked.connect(self.cancel_sentence_generation)
        self.cancel_sentence_button.setEnabled(False)
        button_layout.addWidget(self.cancel_sentence_button)
        
        layout.addLayout(button_layout)
        
        self.sentences_tab.setLayout(layout)
        
    def setup_settings_tab(self):
        """Set up the settings tab UI."""
        layout = QVBoxLayout()
        
        # Folders settings
        folders_group = QGroupBox("Folders")
        folders_layout = QFormLayout()
        
        # Output directory
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setText(os.path.abspath("danish_pronunciations"))
        browse_output_button = QPushButton("Browse...")
        browse_output_button.clicked.connect(self.browse_output_dir)
        
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_dir_input)
        output_layout.addWidget(browse_output_button)
        
        folders_layout.addRow("Output Directory:", output_layout)
        
        # Anki media folder
        self.anki_dir_input = QLineEdit()
        default_anki_folder = os.path.expanduser("~/Library/Application Support/Anki2/User 1/collection.media")
        self.anki_dir_input.setText(default_anki_folder)
        browse_anki_button = QPushButton("Browse...")
        browse_anki_button.clicked.connect(self.browse_anki_dir)
        
        anki_layout = QHBoxLayout()
        anki_layout.addWidget(self.anki_dir_input)
        anki_layout.addWidget(browse_anki_button)
        
        folders_layout.addRow("Anki Media Folder:", anki_layout)
        
        folders_group.setLayout(folders_layout)
        layout.addWidget(folders_group)
        
        # API settings
        api_group = QGroupBox("API Settings")
        api_layout = QFormLayout()
        
        # OpenAI API Key
        self.settings_api_key_input = QLineEdit()
        self.settings_api_key_input.setEchoMode(QLineEdit.Password)
        self.settings_api_key_input.setPlaceholderText("Enter your OpenAI API key")
        api_layout.addRow("OpenAI API Key:", self.settings_api_key_input)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # Save settings button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        self.settings_tab.setLayout(layout)
        
    def load_from_file(self):
        """Load words from a text file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Word List File", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    words = [line.strip() for line in f if line.strip()]
                    self.word_input.setText("\n".join(words))
                    self.log(f"Loaded {len(words)} words from {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading file: {str(e)}")
    
    def load_sentence_words_from_file(self):
        """Load words from a text file for sentence generation."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Word List File", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    words = [line.strip() for line in f if line.strip()]
                    self.sentence_word_input.setText("\n".join(words))
                    self.sentence_log(f"Loaded {len(words)} words from {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading file: {str(e)}")
    
    def browse_output_dir(self):
        """Browse for output directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.output_dir_input.text()
        )
        
        if dir_path:
            self.output_dir_input.setText(dir_path)
    
    def browse_anki_dir(self):
        """Browse for Anki media directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Anki Media Folder", self.anki_dir_input.text()
        )
        
        if dir_path:
            self.anki_dir_input.setText(dir_path)
    
    def save_settings(self):
        """Save settings to QSettings."""
        self.settings.setValue("output_dir", self.output_dir_input.text())
        self.settings.setValue("anki_dir", self.anki_dir_input.text())
        self.settings.setValue("openai_api_key", self.settings_api_key_input.text())
        
        # Also update the sentence tab API key if it's empty
        if not self.api_key_input.text().strip():
            self.api_key_input.setText(self.settings_api_key_input.text())
        
        QMessageBox.information(self, "Settings Saved", "Settings have been saved.")
    
    def load_settings(self):
        """Load settings from QSettings."""
        output_dir = self.settings.value("output_dir")
        anki_dir = self.settings.value("anki_dir")
        api_key = self.settings.value("openai_api_key")
        
        if output_dir:
            self.output_dir_input.setText(output_dir)
        
        if anki_dir:
            self.anki_dir_input.setText(anki_dir)
            
        if api_key:
            self.settings_api_key_input.setText(api_key)
            self.api_key_input.setText(api_key)
    
    def start_download(self):
        """Start the download process."""
        # Get the list of words from the text area
        word_text = self.word_input.toPlainText().strip()
        if not word_text:
            QMessageBox.warning(self, "No Words", "Please enter words to download.")
            return
            
        words = [line.strip() for line in word_text.split('\n') if line.strip()]
        
        # Get output directory and Anki settings
        output_dir = self.output_dir_input.text()
        copy_to_anki = self.anki_checkbox.isChecked()
        anki_folder = self.anki_dir_input.text() if copy_to_anki else ""
        
        # Create directory if it doesn't exist
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create output directory: {str(e)}")
                return
        
        # Create and start the worker thread
        self.worker = Worker(words, output_dir, copy_to_anki, anki_folder)
        self.worker.update_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.download_finished)
        self.worker.start()
        
        # Update UI
        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log("Starting download process...")
    
    def cancel_download(self):
        """Cancel the download process."""
        if self.worker and self.worker.isRunning():
            self.worker.abort()
            self.worker.wait()
            self.log("Download process aborted.")
            
            # Update UI
            self.download_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
    
    def download_finished(self, successful, failed):
        """Handle the completion of the download process."""
        self.log("\nDownload Summary:")
        self.log(f"Total words: {len(successful) + len(failed)}")
        self.log(f"Successfully downloaded: {len(successful)}")
        self.log(f"Failed to download: {len(failed)}")
        
        if failed:
            self.log("\nFailed words:")
            for word in failed:
                self.log(f"- {word}")
            
            # Save failed words to a file
            failed_file = os.path.join(self.output_dir_input.text(), "failed_words.txt")
            try:
                with open(failed_file, "w", encoding="utf-8") as f:
                    for word in failed:
                        f.write(f"{word}\n")
                self.log(f"\nFailed words have been saved to {failed_file}")
            except Exception as e:
                self.log(f"Error saving failed words: {str(e)}")
        
        # Update UI
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        # Show message box
        QMessageBox.information(
            self, 
            "Download Complete", 
            f"Downloaded {len(successful)} of {len(successful) + len(failed)} words."
        )
    
    def update_progress(self, current, total):
        """Update the progress bar."""
        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(percentage)
    
    def log(self, message):
        """Log a message to the log area."""
        self.log_output.append(message)
        # Scroll to the bottom
        cursor = self.log_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_output.setTextCursor(cursor)
    
    def start_sentence_generation(self):
        """Start the sentence generation process."""
        # Get the list of words from the sentence word input
        word_text = self.sentence_word_input.toPlainText().strip()
        if not word_text:
            QMessageBox.warning(self, "No Words", "Please enter words for sentence generation.")
            return
            
        words = [line.strip() for line in word_text.split('\n') if line.strip()]
        
        # Get API key
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "No API Key", "Please enter your OpenAI API key.")
            return
        
        # Get CEFR level
        cefr_level = self.cefr_combo.currentText()
        
        # Clear results
        self.sentence_results.clear()
        
        # Create and start the worker thread
        self.sentence_worker = SentenceWorker(words, cefr_level, api_key)
        self.sentence_worker.update_signal.connect(self.sentence_log)
        self.sentence_worker.progress_signal.connect(self.update_sentence_progress)
        self.sentence_worker.finished_signal.connect(self.sentence_generation_finished)
        self.sentence_worker.error_signal.connect(self.sentence_generation_error)
        self.sentence_worker.start()
        
        # Update UI
        self.generate_button.setEnabled(False)
        self.cancel_sentence_button.setEnabled(True)
        self.sentence_progress_bar.setValue(0)
        self.sentence_log("Starting sentence generation...")
    
    def cancel_sentence_generation(self):
        """Cancel the sentence generation process."""
        if hasattr(self, 'sentence_worker') and self.sentence_worker.isRunning():
            self.sentence_worker.abort()
            self.sentence_worker.wait()
            self.sentence_log("Sentence generation aborted.")
            
            # Update UI
            self.generate_button.setEnabled(True)
            self.cancel_sentence_button.setEnabled(False)
    
    def sentence_generation_finished(self, results):
        """Handle the completion of the sentence generation process."""
        self.sentence_results.setText(results)
        self.sentence_log("Sentence generation completed!")
        
        # Update UI
        self.generate_button.setEnabled(True)
        self.cancel_sentence_button.setEnabled(False)
        
        # Show message box
        word_count = len([line.strip() for line in self.sentence_word_input.toPlainText().split('\n') if line.strip()])
        QMessageBox.information(
            self, 
            "Generation Complete", 
            f"Generated example sentences for {word_count} words."
        )
    
    def sentence_generation_error(self, error_msg):
        """Handle errors in sentence generation."""
        self.sentence_log(f"Error: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)
        
        # Update UI
        self.generate_button.setEnabled(True)
        self.cancel_sentence_button.setEnabled(False)
    
    def update_sentence_progress(self, current, total):
        """Update the sentence generation progress bar."""
        percentage = int((current / total) * 100) if total > 0 else 0
        self.sentence_progress_bar.setValue(percentage)
    
    def sentence_log(self, message):
        """Log a message to the sentence generation log area."""
        self.sentence_log_output.append(message)
        # Scroll to the bottom
        cursor = self.sentence_log_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.sentence_log_output.setTextCursor(cursor)
    
    def save_sentence_results(self):
        """Save the generated sentences to a file."""
        if not self.sentence_results.toPlainText().strip():
            QMessageBox.warning(self, "No Results", "No sentences to save.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Sentence Results", "danish_example_sentences.txt", 
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.sentence_results.toPlainText())
                QMessageBox.information(self, "Saved", f"Results saved to {file_path}")
                self.sentence_log(f"Results saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error saving file: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set up application style
    app.setStyle("Fusion")
    
    window = DanishAudioApp()
    window.show()
    
    sys.exit(app.exec_())
