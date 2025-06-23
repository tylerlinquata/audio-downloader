"""
Main GUI application for Danish Audio Downloader.
"""

import os
import sys
import csv
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QTextEdit, 
                            QFileDialog, QProgressBar, QCheckBox, QMessageBox,
                            QLineEdit, QGroupBox, QFormLayout, QTabWidget,
                            QComboBox, QSplitter)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QIcon, QFont, QTextCursor

from ..core.worker import Worker
from ..core.sentence_worker import SentenceWorker


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
        self.setWindowTitle("Danish Word Learning Assistant")
        self.setMinimumSize(900, 700)
        
        # Create tabs - simplified to just main processing and settings
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Create the main processing tab
        self.main_tab = QWidget()
        self.tabs.addTab(self.main_tab, "Process Words")
        
        # Create the settings tab
        self.settings_tab = QWidget()
        self.tabs.addTab(self.settings_tab, "Settings")
        
        # Set up the main tab
        self.setup_main_tab()
        
        # Set up the settings tab
        self.setup_settings_tab()
        
    def setup_main_tab(self):
        """Set up the main processing tab UI."""
        layout = QVBoxLayout()
        
        # Word input area
        word_group = QGroupBox("Danish Words to Process")
        word_layout = QVBoxLayout()
        
        # Text area for words
        self.word_input = QTextEdit()
        self.word_input.setPlaceholderText("Enter Danish words, one per line\n\nThis will generate:\n• Audio pronunciations\n• Example sentences with grammar info\n• Anki-ready CSV export")
        self.word_input.setMinimumHeight(120)
        word_layout.addWidget(self.word_input)
        
        word_group.setLayout(word_layout)
        layout.addWidget(word_group)
        
        # Processing options
        options_group = QGroupBox("Processing Options")
        options_layout = QFormLayout()
        
        # CEFR Level dropdown
        self.cefr_combo = QComboBox()
        self.cefr_combo.addItems(["A1", "A2", "B1", "B2", "C1", "C2"])
        self.cefr_combo.setCurrentText("B1")
        options_layout.addRow("CEFR Level for Sentences:", self.cefr_combo)
        
        # OpenAI API Key input
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter your OpenAI API key (required for sentence generation)")
        options_layout.addRow("OpenAI API Key:", self.api_key_input)
        
        # Save to Anki checkbox
        self.anki_checkbox = QCheckBox("Copy audio files to Anki Media Folder")
        self.anki_checkbox.setChecked(True)
        options_layout.addRow("", self.anki_checkbox)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Progress area
        progress_group = QGroupBox("Processing Progress")
        progress_layout = QVBoxLayout()
        
        # Progress bars
        audio_progress_layout = QHBoxLayout()
        audio_progress_layout.addWidget(QLabel("Audio Download:"))
        self.audio_progress_bar = QProgressBar()
        self.audio_progress_bar.setValue(0)
        audio_progress_layout.addWidget(self.audio_progress_bar)
        progress_layout.addLayout(audio_progress_layout)
        
        sentence_progress_layout = QHBoxLayout()
        sentence_progress_layout.addWidget(QLabel("Sentence Generation:"))
        self.sentence_progress_bar = QProgressBar()
        self.sentence_progress_bar.setValue(0)
        sentence_progress_layout.addWidget(self.sentence_progress_bar)
        progress_layout.addLayout(sentence_progress_layout)
        
        # Combined log area
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Courier New", 10))
        self.log_output.setMaximumHeight(150)
        progress_layout.addWidget(self.log_output)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Results area
        results_group = QGroupBox("Generated Results")
        results_layout = QVBoxLayout()
        
        # Results text area (larger and more readable)
        self.sentence_results = QTextEdit()
        self.sentence_results.setReadOnly(True)
        self.sentence_results.setFont(QFont("Georgia", 12))
        self.sentence_results.setMinimumHeight(300)
        results_layout.addWidget(self.sentence_results)
        
        # Save buttons layout
        save_buttons_layout = QHBoxLayout()
        
        # Save results as CSV button
        save_csv_button = QPushButton("Save as Anki CSV")
        save_csv_button.clicked.connect(self.save_sentence_results_csv)
        save_buttons_layout.addWidget(save_csv_button)
        
        results_layout.addLayout(save_buttons_layout)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Main action buttons
        button_layout = QHBoxLayout()
        
        # Process button
        self.process_button = QPushButton("Process Words (Audio + Sentences)")
        self.process_button.clicked.connect(self.start_processing)
        self.process_button.setStyleSheet("QPushButton { font-weight: bold; padding: 10px; }")
        button_layout.addWidget(self.process_button)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel Processing")
        self.cancel_button.clicked.connect(self.cancel_processing)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.main_tab.setLayout(layout)
        
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
    
    def start_processing(self):
        """Start the unified processing (audio download + sentence generation)."""
        # Get the list of words from the text area
        word_text = self.word_input.toPlainText().strip()
        if not word_text:
            QMessageBox.warning(self, "No Words", "Please enter words to process.")
            return
            
        words = [line.strip() for line in word_text.split('\n') if line.strip()]
        
        # Get API key for sentence generation
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "No API Key", "Please enter your OpenAI API key for sentence generation.")
            return
        
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
        
        # Update UI for processing state
        self.process_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.audio_progress_bar.setValue(0)
        self.sentence_progress_bar.setValue(0)
        self.sentence_results.clear()
        
        self.log("Starting unified processing...")
        self.log(f"Processing {len(words)} words:")
        for word in words:
            self.log(f"  - {word}")
        
        # Start with audio download first
        self.start_audio_download(words, output_dir, copy_to_anki, anki_folder, api_key)
    
    def start_audio_download(self, words, output_dir, copy_to_anki, anki_folder, api_key):
        """Start the audio download phase."""
        self.log("\n=== Phase 1: Downloading Audio Files ===")
        
        # Store the sentence generation parameters for later
        self.pending_sentence_generation = {
            'words': words,
            'api_key': api_key,
            'cefr_level': self.cefr_combo.currentText()
        }
        
        # Create and start the audio worker thread
        self.worker = Worker(words, output_dir, copy_to_anki, anki_folder)
        self.worker.update_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_audio_progress)
        self.worker.finished_signal.connect(self.audio_download_finished)
        self.worker.start()
    
    def audio_download_finished(self, successful, failed):
        """Handle completion of audio download and start sentence generation."""
        self.log("\n=== Audio Download Complete ===")
        self.log(f"Successfully downloaded: {len(successful)} audio files")
        if failed:
            self.log(f"Failed to download: {len(failed)} audio files")
            for word in failed:
                self.log(f"  - {word}")
        
        # Start sentence generation phase
        self.start_sentence_generation_phase()
    
    def start_sentence_generation_phase(self):
        """Start the sentence generation phase."""
        self.log("\n=== Phase 2: Generating Example Sentences ===")
        
        params = self.pending_sentence_generation
        
        # Create and start the sentence worker thread
        self.sentence_worker = SentenceWorker(params['words'], params['cefr_level'], params['api_key'])
        self.sentence_worker.update_signal.connect(self.log)
        self.sentence_worker.progress_signal.connect(self.update_sentence_progress)
        self.sentence_worker.finished_signal.connect(self.unified_processing_finished)
        self.sentence_worker.error_signal.connect(self.sentence_generation_error)
        self.sentence_worker.start()
    
    def unified_processing_finished(self, results):
        """Handle completion of the entire unified processing."""
        self.sentence_results.setText(results)
        self.log("\n=== Processing Complete! ===")
        self.log("Both audio files and example sentences have been generated.")
        
        # Update UI
        self.process_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        # Show completion message
        word_count = len(self.pending_sentence_generation['words'])
        QMessageBox.information(
            self, 
            "Processing Complete!", 
            f"Successfully processed {word_count} words!\n\n" +
            "✓ Audio files downloaded\n" +
            "✓ Example sentences generated\n" +
            "✓ Ready for Anki import"
        )
    
    def cancel_processing(self):
        """Cancel the unified processing."""
        # Cancel audio worker if running
        if self.worker and self.worker.isRunning():
            self.worker.abort()
            self.worker.wait()
            self.log("Audio download cancelled.")
        
        # Cancel sentence worker if running
        if hasattr(self, 'sentence_worker') and self.sentence_worker.isRunning():
            self.sentence_worker.abort()
            self.sentence_worker.wait()
            self.log("Sentence generation cancelled.")
        
        self.log("Processing cancelled.")
        
        # Update UI
        self.process_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
    
    def update_audio_progress(self, current, total):
        """Update the audio download progress bar."""
        percentage = int((current / total) * 100) if total > 0 else 0
        self.audio_progress_bar.setValue(percentage)
    
    def sentence_generation_error(self, error_msg):
        """Handle errors in sentence generation."""
        self.log(f"Error in sentence generation: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)
        
        # Update UI
        self.process_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
    
    def update_sentence_progress(self, current, total):
        """Update the sentence generation progress bar."""
        percentage = int((current / total) * 100) if total > 0 else 0
        self.sentence_progress_bar.setValue(percentage)
    
    def log(self, message):
        """Log a message to the unified log area."""
        self.log_output.append(message)
        # Scroll to the bottom
        cursor = self.log_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_output.setTextCursor(cursor)
    
    def save_sentence_results_csv(self):
        """Save the generated sentences to a CSV file."""
        if not self.sentence_results.toPlainText().strip():
            QMessageBox.warning(self, "No Results", "No sentences to save.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Sentence Results as CSV", "danish_example_sentences.csv", 
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                self._export_sentences_to_csv(file_path)
                QMessageBox.information(self, "Saved", f"Results saved to {file_path}")
                self.log(f"Anki CSV export saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error saving CSV file: {str(e)}")

    def _export_sentences_to_csv(self, file_path):
        """Export sentences to CSV format for Anki import with specific card types."""
        content = self.sentence_results.toPlainText()
        
        # Parse the content to extract words and sentences
        csv_data = []
        
        # Split by word blocks - looking for pattern like "**word**" at start of line, followed by content
        word_blocks = re.split(r'\n\s*---\s*\n', content)
        
        for block in word_blocks:
            block = block.strip()
            if not block:
                continue
                
            # Extract the word from the beginning of the block
            word_match = re.match(r'\*\*([^*]+)\*\*', block)
            if not word_match:
                continue
                
            word = word_match.group(1).strip()
            
            # Skip if this is formatting text
            if word.lower() in ['example sentences', 'eksempel sætninger']:
                continue
            
            # Extract grammar information from the block
            grammar_info = self._extract_grammar_info(block)
            
            # Extract sentences from the block
            sentence_pattern = r'(\d+)\.\s*([^-\n]+?)\s*-\s*([^\n]+?)(?=\n\d+\.|\n\n|\Z)'
            matches = re.findall(sentence_pattern, block, re.DOTALL)
            
            if not matches:
                continue
            
            sentences = []
            for match in matches:
                sentence_num, danish, english = match
                danish = danish.strip()
                english = english.strip()
                if danish and english:
                    sentences.append(danish)
            
            if len(sentences) >= 3:
                # Generate the three card types for this word with grammar info
                csv_data.extend(self._generate_anki_cards(word, sentences[:3], grammar_info))
        
        # Write to CSV file
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # Write header - Anki import format
            writer.writerow([
                'Front (Eksempel med ord fjernet eller blankt)',
                'Front (Billede)', 
                'Front (Definition, grundform, osv.)',
                'Back (et enkelt ord/udtryk, uden kontekst)',
                '- Hele sætningen (intakt)',
                '- Ekstra info (IPA, køn, bøjning)',
                '• Lav 2 kort?'
            ])
            # Write data
            writer.writerows(csv_data)
    
    def _extract_grammar_info(self, block):
        """Extract grammar information from a word block."""
        grammar_info = {
            'ipa': '',
            'type': '',
            'gender': '',
            'plural': '',
            'inflections': '',
            'definition': ''
        }
        
        # Look for grammar info section
        grammar_match = re.search(r'\*\*Grammar Info:\*\*(.*?)(?=\*\*Example Sentences:\*\*|\Z)', block, re.DOTALL)
        if grammar_match:
            grammar_section = grammar_match.group(1).strip()
            
            # Extract IPA
            ipa_match = re.search(r'IPA:\s*([^\n]+)', grammar_section)
            if ipa_match:
                grammar_info['ipa'] = ipa_match.group(1).strip()
            
            # Extract type
            type_match = re.search(r'Type:\s*([^\n]+)', grammar_section)
            if type_match:
                grammar_info['type'] = type_match.group(1).strip()
            
            # Extract gender
            gender_match = re.search(r'Gender:\s*([^\n]+)', grammar_section)
            if gender_match:
                grammar_info['gender'] = gender_match.group(1).strip()
            
            # Extract plural
            plural_match = re.search(r'Plural:\s*([^\n]+)', grammar_section)
            if plural_match:
                grammar_info['plural'] = plural_match.group(1).strip()
            
            # Extract inflections
            inflections_match = re.search(r'Inflections:\s*([^\n]+)', grammar_section)
            if inflections_match:
                grammar_info['inflections'] = inflections_match.group(1).strip()
            
            # Extract definition
            definition_match = re.search(r'Definition:\s*([^\n]+)', grammar_section)
            if definition_match:
                grammar_info['definition'] = definition_match.group(1).strip()
        
        return grammar_info
    
    def _generate_anki_cards(self, word, sentences, grammar_info=None):
        """Generate three card types for a word with the given sentences."""
        cards = []
        
        if len(sentences) < 3:
            return cards
        
        # Helper function to remove word from sentence
        def remove_word_from_sentence(sentence, word_to_remove, use_blank=True):
            # Create patterns for the word and common inflected forms
            base_word = word_to_remove.lower()
            patterns = [
                r'\b' + re.escape(word_to_remove) + r'\b',  # exact match
                r'\b' + re.escape(word_to_remove.capitalize()) + r'\b',  # capitalized
                r'\b' + re.escape(word_to_remove.upper()) + r'\b',  # uppercase
            ]
            
            # Add common Danish inflections
            if base_word.endswith('e'):
                # For words ending in 'e', try without 'e' + common endings
                stem = base_word[:-1]
                patterns.extend([
                    r'\b' + re.escape(stem + 'en') + r'\b',  # definite form
                    r'\b' + re.escape(stem + 'er') + r'\b',  # plural
                    r'\b' + re.escape(stem + 'erne') + r'\b',  # definite plural
                ])
            else:
                # For words not ending in 'e', add common endings
                patterns.extend([
                    r'\b' + re.escape(base_word + 'en') + r'\b',  # definite form (en-words)
                    r'\b' + re.escape(base_word + 'et') + r'\b',  # neuter definite (et-words)
                    r'\b' + re.escape(base_word + 'e') + r'\b',   # adjective/verb form
                    r'\b' + re.escape(base_word + 'er') + r'\b',  # plural/present
                    r'\b' + re.escape(base_word + 'erne') + r'\b', # definite plural
                ])
            
            # Special case for common double consonant patterns (e.g., kat -> katten)
            if len(base_word) >= 2 and base_word[-1] == base_word[-2]:
                # Double consonant at end (like "kat" -> "katt")
                single_consonant = base_word[:-1]
                patterns.extend([
                    r'\b' + re.escape(single_consonant + 'en') + r'\b',  # katten
                    r'\b' + re.escape(single_consonant + 'er') + r'\b',  # katter
                    r'\b' + re.escape(single_consonant + 'erne') + r'\b', # katterne
                ])
            elif len(base_word) >= 2:
                # Try adding double consonant for inflection (kat -> katt -> katten)
                last_consonant = base_word[-1]
                if last_consonant not in 'aeiouæøå':  # if last letter is consonant
                    double_consonant_stem = base_word + last_consonant
                    patterns.extend([
                        r'\b' + re.escape(double_consonant_stem + 'en') + r'\b',  # katten
                        r'\b' + re.escape(double_consonant_stem + 'er') + r'\b',  # katter
                        r'\b' + re.escape(double_consonant_stem + 'erne') + r'\b', # katterne
                    ])
            
            # Try each pattern
            result_sentence = sentence
            for pattern in patterns:
                if re.search(pattern, result_sentence, flags=re.IGNORECASE):
                    if use_blank:
                        result_sentence = re.sub(pattern, '___', result_sentence, flags=re.IGNORECASE)
                    else:
                        result_sentence = re.sub(pattern, '', result_sentence, flags=re.IGNORECASE)
                    break
            
            if not use_blank:
                # Clean up extra spaces and punctuation
                result_sentence = re.sub(r'\s+', ' ', result_sentence).strip()
                result_sentence = re.sub(r'\s+([,.!?])', r'\1', result_sentence)
                
            return result_sentence
        
        # Initialize grammar info if not provided
        if grammar_info is None:
            grammar_info = {
                'ipa': f'IPA_for_{word}',
                'type': 'ukendt',
                'gender': '',
                'plural': '',
                'inflections': f'Grammatik info for {word}',
                'definition': f'Definition af {word}'
            }
        
        # Card Type 1: Fill-in-the-blank + IPA
        sentence1_with_blank = remove_word_from_sentence(sentences[0], word, use_blank=True)
        definition_text = self._format_definition(word, grammar_info)
        grammar_details = self._format_grammar_details(grammar_info)
        ipa_info = grammar_info['ipa'] if grammar_info['ipa'] else f'/IPA_for_{word}/'
        if not ipa_info.startswith('/'):
            ipa_info = f'/{ipa_info}/'
        cards.append([
            sentence1_with_blank,                    # Front (Eksempel med ord fjernet eller blankt)
            '<img src="myimage.jpg">',               # Front (Billede)
            definition_text,                                      # Front (Definition, grundform, osv.) - empty for card 1
            word,                                    # Back (et enkelt ord/udtryk, uden kontekst)
            sentences[0],                            # - Hele sætningen (intakt)
            f'{ipa_info} {grammar_details} [sound:{word}.mp3]',        # - Ekstra info (IPA, køn, bøjning)
            'y'                                      # • Lav 2 kort?
        ])
        
        # Card Type 2: Fill-in-the-blank + definition
        sentence2_no_word = remove_word_from_sentence(sentences[1], word, use_blank=False)
        cards.append([
            sentence2_no_word,                       # Front (Eksempel med ord fjernet eller blankt)
            '<img src="myimage.jpg">',               # Front (Billede)
            f'{word} {definition_text}',                         # Front (Definition, grundform, osv.)
            '',                                      # Back (et enkelt ord/udtryk, uden kontekst) - empty for card 2
            sentences[0],                            # - Hele sætningen (intakt)
            f'{ipa_info} {grammar_details} [sound:{word}.mp3]', # - Ekstra info (IPA, køn, bøjning)
            ''                                       # • Lav 2 kort? - empty for card 2
        ])
        
        # Card Type 3: New sentence with blank
        sentence3_with_blank = remove_word_from_sentence(sentences[2], word, use_blank=True)
        cards.append([
            sentence3_with_blank,                    # Front (Eksempel med ord fjernet eller blankt)
            '<img src="myimage.jpg">',               # Front (Billede)
            definition_text,                                      # Front (Definition, grundform, osv.) - empty for card 3
            word,                                    # Back (et enkelt ord/udtryk, uden kontekst)
            sentences[1],                            # - Hele sætningen (intakt)
            f'{ipa_info} {grammar_details} [sound:{word}.mp3]', # - Ekstra info (IPA, køn, bøjning)
            ''                                       # • Lav 2 kort? - empty for card 3
        ])
        
        return cards
    
    def _format_definition(self, word, grammar_info):
        """Format definition text for Card Type 2."""
        definition_parts = [word]
        
        if grammar_info.get('type'):
            definition_parts.append(f"({grammar_info['type']})")
        
        # Add gender for nouns
        if grammar_info.get('gender'):
            definition_parts.append(f"[{grammar_info['gender']}]")
        
        # Add basic definition if available
        if grammar_info.get('definition'):
            definition_parts.append(grammar_info['definition'])
        else:
            definition_parts.append("Definition nødvendig")
        
        return "\n".join(definition_parts)
    
    def _format_grammar_details(self, grammar_info):
        """Format detailed grammar information."""
        details = []
        
        # Add IPA if available
        if grammar_info.get('ipa'):
            ipa = grammar_info['ipa']
            if not ipa.startswith('/'):
                ipa = f'/{ipa}/'
            details.append(ipa)
        
        # Add type
        if grammar_info.get('type'):
            details.append(grammar_info['type'])
        
        # Add gender for nouns
        if grammar_info.get('gender'):
            details.append(f"køn: {grammar_info['gender']}")
        
        # Add plural form
        if grammar_info.get('plural'):
            details.append(f"flertal: {grammar_info['plural']}")
        
        # Add inflections
        if grammar_info.get('inflections'):
            details.append(f"bøjning: {grammar_info['inflections']}")
        
        return " | ".join(details) if details else "Grammatik info nødvendig"


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    
    # Set up application style
    app.setStyle("Fusion")
    
    window = DanishAudioApp()
    window.show()
    
    sys.exit(app.exec_())
