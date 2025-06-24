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
                            QComboBox, QSplitter, QTableWidget, QTableWidgetItem,
                            QHeaderView, QAbstractItemView, QFrame)
from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QTextCursor, QColor, QPixmap
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
import requests

from ..core.worker import Worker
from ..core.sentence_worker import SentenceWorker
from ..core.image_worker import ImageWorker


class ImageLoader(QThread):
    """Helper class to load images from URLs without blocking the UI."""
    image_loaded = pyqtSignal(int, int, QPixmap)  # row, column, pixmap
    
    def __init__(self, row, col, url):
        super().__init__()
        self.row = row
        self.col = col
        self.url = url
    
    def run(self):
        try:
            response = requests.get(self.url, timeout=10)
            if response.status_code == 200:
                pixmap = QPixmap()
                if pixmap.loadFromData(response.content):
                    # Scale image to fit in table cell
                    scaled_pixmap = pixmap.scaled(80, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.image_loaded.emit(self.row, self.col, scaled_pixmap)
        except Exception as e:
            # If image loading fails, we'll just keep the text indicator
            pass


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
        self.image_worker = None
        self.word_image_urls = {}  # Store image URLs for CSV export
        self.generated_cards = []  # Store generated cards for review
        self.image_loaders = []  # Track image loading threads
        
        # Set initial button state
        self.update_button_state("idle")
        
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
        
        # Create the card review tab
        self.review_tab = QWidget()
        self.tabs.addTab(self.review_tab, "Review Cards")
        
        # Set up the main tab
        self.setup_main_tab()
        
        # Set up the settings tab
        self.setup_settings_tab()
        
        # Set up the review tab
        self.setup_review_tab()
        
    def setup_main_tab(self):
        """Set up the main processing tab UI."""
        layout = QVBoxLayout()
        
        # Word input area
        word_group = QGroupBox("Danish Words to Process")
        word_layout = QVBoxLayout()
        
        # Text area for words
        self.word_input = QTextEdit()
        self.word_input.setPlaceholderText("Enter Danish words, one per line\n\nThis will generate:\n• Audio pronunciations\n• Example sentences with grammar info\n• Images from dictionary sources\n• Anki-ready CSV export")
        self.word_input.setMinimumHeight(120)
        word_layout.addWidget(self.word_input)
        
        word_group.setLayout(word_layout)
        layout.addWidget(word_group)
        
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
        
        image_progress_layout = QHBoxLayout()
        image_progress_layout.addWidget(QLabel("Image Fetching:"))
        self.image_progress_bar = QProgressBar()
        self.image_progress_bar.setValue(0)
        image_progress_layout.addWidget(self.image_progress_bar)
        progress_layout.addLayout(image_progress_layout)
        
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
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Main action button (dynamic)
        button_layout = QHBoxLayout()
        
        # Dynamic action button that changes based on application state
        self.action_button = QPushButton("Process Words (Audio + Sentences)")
        self.action_button.clicked.connect(self.handle_action_button)
        self.action_button.setStyleSheet("QPushButton { font-weight: bold; padding: 12px; }")
        button_layout.addWidget(self.action_button)
        
        # Initialize button state
        self.app_state = "idle"  # idle, processing, results_ready
        
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
        
        # Processing options
        processing_group = QGroupBox("Processing Options")
        processing_layout = QFormLayout()
        
        # CEFR Level dropdown
        self.cefr_combo = QComboBox()
        self.cefr_combo.addItems(["A1", "A2", "B1", "B2", "C1", "C2"])
        self.cefr_combo.setCurrentText("B1")
        processing_layout.addRow("CEFR Level for Sentences:", self.cefr_combo)
        
        processing_group.setLayout(processing_layout)
        layout.addWidget(processing_group)
        
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
        
    def setup_review_tab(self):
        """Set up the card review tab UI."""
        layout = QVBoxLayout()
        
        # Header with instructions
        header_group = QGroupBox("Review and Edit Flashcards")
        header_layout = QVBoxLayout()
        
        instructions = QLabel(
            "Review and edit your generated flashcards below. You can modify any field or uncheck cards you don't want to include.\n"
            "Cards are generated in sets of 3 for each word: Fill-in-blank, Definition, and Additional sentence.\n\n"
            "💡 The 'Preview' columns show the source image and English translation for reference only - they are NOT included in your Anki cards."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("QLabel { padding: 10px; background-color: #4CAF50; border: 1px solid #d0d0d0; border-radius: 5px; }")
        header_layout.addWidget(instructions)
        
        header_group.setLayout(header_layout)
        # layout.addWidget(header_group)
        
        # Card table
        table_group = QGroupBox("Generated Cards")
        table_layout = QVBoxLayout()
        
        self.card_table = QTableWidget()
        self.card_table.setColumnCount(10)  # Include checkbox column + preview columns
        headers = [
            "Include", "Preview: Image", "Preview: English", "Front (Example)", "Front (Image)", "Front (Definition)", 
            "Back (Word)", "Full Sentence", "Grammar Info", "Make 2 Cards"
        ]
        self.card_table.setHorizontalHeaderLabels(headers)
        
        # Configure table appearance
        self.card_table.horizontalHeader().setStretchLastSection(False)
        self.card_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Include checkbox
        self.card_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Preview: Image
        self.card_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Preview: English
        self.card_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # Front example
        self.card_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Front image
        self.card_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)  # Definition
        self.card_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Back word
        self.card_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)  # Full sentence
        self.card_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.Stretch)  # Grammar
        self.card_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Make 2 cards
        
        self.card_table.setAlternatingRowColors(True)
        self.card_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.card_table.verticalHeader().setVisible(False)
        self.card_table.setMinimumHeight(400)  # Give more space for the table
        
        # Add row height for better readability and image display
        self.card_table.verticalHeader().setDefaultSectionSize(80)
        
        table_layout.addWidget(self.card_table)
        
        # Add status label
        self.card_status_label = QLabel("No cards loaded")
        self.card_status_label.setStyleSheet("QLabel { padding: 5px; font-weight: bold; }")
        table_layout.addWidget(self.card_status_label)
        
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        # Select/Deselect buttons
        select_all_btn = QPushButton("Select All Cards")
        select_all_btn.clicked.connect(self.select_all_cards)
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All Cards")
        deselect_all_btn.clicked.connect(self.deselect_all_cards)
        button_layout.addWidget(deselect_all_btn)
        
        button_layout.addStretch()
        
        # Navigation buttons
        back_to_process_btn = QPushButton("← Back to Processing")
        back_to_process_btn.clicked.connect(self.back_to_processing)
        button_layout.addWidget(back_to_process_btn)
        
        self.export_csv_btn = QPushButton("Export Selected Cards to CSV")
        self.export_csv_btn.clicked.connect(self.export_reviewed_cards_to_csv)
        self.export_csv_btn.setStyleSheet("QPushButton { font-weight: bold; padding: 10px; background-color: #4CAF50; color: white; }")
        button_layout.addWidget(self.export_csv_btn)
        
        layout.addLayout(button_layout)
        
        self.review_tab.setLayout(layout)
        
        # Initially disable the review tab
        self.tabs.setTabEnabled(2, False)  # Review tab is index 2
    
    def on_image_loaded(self, row, col, pixmap):
        """Callback when an image is successfully loaded."""
        widget = self.card_table.cellWidget(row, col)
        if widget and isinstance(widget, QLabel):
            widget.setPixmap(pixmap)
            widget.setText("")  # Clear the loading text
    
    def populate_card_review_table(self, cards_data):
        """Populate the review table with generated cards."""
        self.generated_cards = cards_data
        self.card_table.setRowCount(len(cards_data))
        
        for row, card_info in enumerate(cards_data):
            # Extract card data and metadata
            if isinstance(card_info, dict):
                card = card_info['card_data']
                danish_word = card_info['danish_word']
                english_word = card_info['english_word']
                image_url = card_info['image_url']
            else:
                # Fallback for old format (shouldn't happen with new code)
                card = card_info
                danish_word = "Unknown"
                english_word = "Unknown"
                image_url = None
            
            # Include checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(True)  # Default to selected
            checkbox.stateChanged.connect(self.update_card_status)  # Connect to status update
            self.card_table.setCellWidget(row, 0, checkbox)
            
            # Column 1: Preview Image
            if image_url:
                image_label = QLabel()
                image_label.setAlignment(Qt.AlignCenter)
                image_label.setText("🖼️ Loading...")
                image_label.setToolTip(f"Image URL: {image_url}")
                image_label.setStyleSheet("QLabel { background-color: rgb(144, 238, 144); padding: 5px; }")
                image_label.setMinimumSize(90, 70)
                image_label.setMaximumSize(90, 70)
                self.card_table.setCellWidget(row, 1, image_label)
                loader = ImageLoader(row, 1, image_url)
                loader.image_loaded.connect(self.on_image_loaded)
                loader.start()
                self.image_loaders.append(loader)
            else:
                no_image_label = QLabel("❌ No Image")
                no_image_label.setAlignment(Qt.AlignCenter)
                no_image_label.setStyleSheet("QLabel { background-color: rgb(211, 211, 211); padding: 5px; }")
                no_image_label.setMinimumSize(90, 70)
                no_image_label.setMaximumSize(90, 70)
                self.card_table.setCellWidget(row, 1, no_image_label)
            
            # Column 2: Preview English Word
            english_preview = QTableWidgetItem(f"🇬🇧 {english_word}")
            english_preview.setToolTip(f"Danish: {danish_word} → English: {english_word}")
            english_preview.setFlags(Qt.ItemIsEnabled)  # Read-only
            english_preview.setBackground(QColor(173, 216, 230))  # Light blue
            self.card_table.setItem(row, 2, english_preview)
            
            # Card data columns (shifted by +2)
            for col, value in enumerate(card, 3):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() | Qt.ItemIsEditable)  # Make cells editable
                if col in [3, 5, 7, 8]:  # Example, Definition, Full Sentence, Grammar columns (shifted)
                    item.setToolTip(str(value))
                self.card_table.setItem(row, col, item)
        
        # Update status
        self.update_card_status()
        
        # Enable the review tab and switch to it
        self.tabs.setTabEnabled(2, True)
        self.tabs.setCurrentIndex(2)
    
    def update_card_status(self):
        """Update the status label showing selected card count."""
        selected_count = 0
        total_count = self.card_table.rowCount()
        
        for row in range(total_count):
            checkbox = self.card_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_count += 1
        
        self.card_status_label.setText(f"Cards: {selected_count} selected of {total_count} total")
    def select_all_cards(self):
        """Select all cards in the review table."""
        for row in range(self.card_table.rowCount()):
            checkbox = self.card_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
        self.update_card_status()
    
    def deselect_all_cards(self):
        """Deselect all cards in the review table."""
        for row in range(self.card_table.rowCount()):
            checkbox = self.card_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
        self.update_card_status()
    
    def back_to_processing(self):
        """Go back to the processing tab."""
        self.tabs.setCurrentIndex(0)
    
    def export_reviewed_cards_to_csv(self):
        """Export only the selected cards to CSV."""
        # Get selected cards
        selected_cards = []
        for row in range(self.card_table.rowCount()):
            checkbox = self.card_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                # Get the edited values from the table (exclude preview columns 1 and 2)
                card_data = []
                for col in range(3, 10):  # Columns 3-9 (skip checkbox and preview columns 1-2)
                    item = self.card_table.item(row, col)
                    card_data.append(item.text() if item else "")
                selected_cards.append(card_data)
        
        if not selected_cards:
            QMessageBox.warning(self, "No Cards Selected", "Please select at least one card to export.")
            return
        
        # Show file dialog to save CSV
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Anki CSV", "anki_cards.csv", "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    # Don't write header for Anki import - Anki doesn't expect headers
                    # Write selected cards only
                    writer.writerows(selected_cards)
                
                # After successful CSV export, copy audio files to Anki
                self._copy_audio_files_to_anki(selected_cards)
                
                QMessageBox.information(
                    self, "Export Complete", 
                    f"Successfully exported {len(selected_cards)} cards to:\n{file_path}\n\n" +
                    "Audio files have been copied to your Anki media folder."
                )
                
                # Reset the app state and go back to processing tab
                self.reset_for_new_processing()
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save CSV file:\n{str(e)}")
    
    def _copy_audio_files_to_anki(self, selected_cards):
        """Copy audio files for selected cards to Anki media folder."""
        try:
            anki_folder = self.anki_dir_input.text()
            output_dir = self.output_dir_input.text()
            
            if not anki_folder or not os.path.exists(anki_folder):
                self.log("Warning: Anki media folder not found. Audio files not copied to Anki.")
                return
            
            if not output_dir or not os.path.exists(output_dir):
                self.log("Warning: Output directory not found. Audio files not copied to Anki.")
                return
            
            # Extract unique words from selected cards that have audio references
            words_to_copy = set()
            for card in selected_cards:
                # Check the grammar info column (index 5) for audio references
                if len(card) > 5 and '[sound:' in card[5]:
                    # Extract word from audio reference like "[sound:word.mp3]"
                    import re
                    audio_match = re.search(r'\[sound:([^.]+)\.mp3\]', card[5])
                    if audio_match:
                        words_to_copy.add(audio_match.group(1))
            
            copied_count = 0
            failed_copies = []
            
            for word in words_to_copy:
                source_file = os.path.join(output_dir, f"{word}.mp3")
                dest_file = os.path.join(anki_folder, f"{word}.mp3")
                
                if os.path.exists(source_file):
                    try:
                        import shutil
                        shutil.copy2(source_file, dest_file)
                        copied_count += 1
                        self.log(f"✓ Copied {word}.mp3 to Anki media folder")
                    except Exception as e:
                        failed_copies.append(word)
                        self.log(f"✗ Failed to copy {word}.mp3: {str(e)}")
                else:
                    failed_copies.append(word)
                    self.log(f"✗ Audio file not found: {word}.mp3")
            
            self.log(f"\nAudio copy summary: {copied_count} files copied successfully")
            if failed_copies:
                self.log(f"Failed to copy {len(failed_copies)} files: {', '.join(failed_copies)}")
            
        except Exception as e:
            self.log(f"Error copying audio files to Anki: {str(e)}")
    
    def reset_for_new_processing(self):
        """Reset the app for new processing."""
        # Stop any running image loaders
        for loader in self.image_loaders:
            if loader.isRunning():
                loader.terminate()
                loader.wait()
        self.image_loaders.clear()
        
        # Clear data
        self.generated_cards = []
        self.word_image_urls = {}
        self.card_table.setRowCount(0)
        self.card_status_label.setText("No cards loaded")
        
        # Disable review tab and go back to processing
        self.tabs.setTabEnabled(2, False)
        self.tabs.setCurrentIndex(0)
        
        # Reset UI state
        self.update_button_state("idle")
        self.sentence_results.clear()
        self.audio_progress_bar.setValue(0)
        self.sentence_progress_bar.setValue(0)
        self.image_progress_bar.setValue(0)
    
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
        self.settings.setValue("cefr_level", self.cefr_combo.currentText())
        
        QMessageBox.information(self, "Settings Saved", "Settings have been saved.")
    
    def load_settings(self):
        """Load settings from QSettings."""
        output_dir = self.settings.value("output_dir")
        anki_dir = self.settings.value("anki_dir")
        api_key = self.settings.value("openai_api_key")
        cefr_level = self.settings.value("cefr_level")
        
        if output_dir:
            self.output_dir_input.setText(output_dir)
        
        if anki_dir:
            self.anki_dir_input.setText(anki_dir)
            
        if api_key:
            self.settings_api_key_input.setText(api_key)
            
        if cefr_level:
            self.cefr_combo.setCurrentText(cefr_level)
    
    def start_processing(self):
        """Start the unified processing (audio download + sentence generation)."""
        # Get the list of words from the text area
        word_text = self.word_input.toPlainText().strip()
        if not word_text:
            QMessageBox.warning(self, "No Words", "Please enter words to process.")
            return
            
        words = [line.strip() for line in word_text.split('\n') if line.strip()]
        
        # Get API key for sentence generation from settings
        api_key = self.settings_api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "No API Key", "Please enter your OpenAI API key in the Settings tab.")
            return
        
        # Get output directory and Anki settings - DON'T copy to Anki yet
        output_dir = self.output_dir_input.text()
        copy_to_anki = False  # Don't copy to Anki until CSV is exported
        anki_folder = self.anki_dir_input.text()
        
        # Create directory if it doesn't exist
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create output directory: {str(e)}")
                return
        
        # Update UI for processing state
        self.update_button_state("processing")
        self.audio_progress_bar.setValue(0)
        self.sentence_progress_bar.setValue(0)
        self.image_progress_bar.setValue(0)
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
        self.sentence_worker.finished_signal.connect(self.sentence_generation_finished)
        self.sentence_worker.error_signal.connect(self.sentence_generation_error)
        self.sentence_worker.start()
    
    def sentence_generation_finished(self, results, word_translations):
        """Handle completion of sentence generation and start image fetching."""
        self.sentence_results.setText(results)
        self.log("\n=== Sentence Generation Complete ===")
        self.log(f"Generated sentences for {len(word_translations)} words")
        
        # Store the sentence results for final completion
        self.final_sentence_results = results
        
        # Start image fetching phase
        self.start_image_fetching_phase(word_translations)
    
    def start_image_fetching_phase(self, word_translations):
        """Start the image fetching phase."""
        self.log("\n=== Phase 3: Fetching Images ===")
        
        # Create and start the image worker thread
        api_key = self.pending_sentence_generation['api_key']
        self.image_worker = ImageWorker(word_translations, api_key)
        self.image_worker.update_signal.connect(self.log)
        self.image_worker.progress_signal.connect(self.update_image_progress)
        self.image_worker.finished_signal.connect(self.image_fetching_finished)
        self.image_worker.error_signal.connect(self.image_fetching_error)
        self.image_worker.start()
    
    def image_fetching_finished(self, image_urls):
        """Handle completion of image fetching and finish unified processing."""
        self.log("\n=== Image Fetching Complete ===")
        successful_images = len([url for url in image_urls.values() if url])
        self.log(f"Found images for {successful_images} out of {len(image_urls)} words")
        
        # Store image URLs for CSV export
        self.word_image_urls = image_urls
        
        # Complete the unified processing
        self.unified_processing_finished()
    def image_fetching_error(self, error_msg):
        """Handle errors in image fetching."""
        self.log(f"Image fetching error: {error_msg}")
        # Continue without images - set empty image URLs
        self.word_image_urls = {}
        self.unified_processing_finished()
    
    def unified_processing_finished(self):
        """Handle completion of the entire unified processing."""
        if hasattr(self, 'final_sentence_results'):
            # Ensure sentence results are displayed
            self.sentence_results.setText(self.final_sentence_results)
        
        self.log("\n=== Processing Complete! ===")
        self.log("Audio files, example sentences, and images have been processed.")
        self.log("Generating cards for review...")
        
        # Generate cards for review
        try:
            cards_data = self._generate_cards_for_review()
            if cards_data:
                self.log(f"Generated {len(cards_data)} cards for review.")
                
                # Show completion message and redirect to review
                word_count = len(self.pending_sentence_generation['words'])
                image_count = len([url for url in self.word_image_urls.values() if url]) if hasattr(self, 'word_image_urls') else 0
                
                result = QMessageBox.information(
                    self, 
                    "Processing Complete!", 
                    f"Successfully processed {word_count} words!\n\n" +
                    "✓ Audio files downloaded\n" +
                    "✓ Example sentences generated\n" +
                    f"✓ Images found for {image_count} words\n" +
                    f"✓ Generated {len(cards_data)} flashcards\n\n" +
                    "Click OK to review and edit your cards.",
                    QMessageBox.Ok
                )
                
                # Populate the review table and switch to review tab
                self.populate_card_review_table(cards_data)
                
                # Update button state to idle since we're now in review mode
                self.update_button_state("idle")
                
            else:
                self.log("No cards were generated. Check the sentence results format.")
                QMessageBox.warning(self, "No Cards Generated", "No cards could be generated from the results. Please check the output format.")
                self.update_button_state("results_ready")  # Fall back to old workflow
                
        except Exception as e:
            self.log(f"Error generating cards for review: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error generating cards for review: {str(e)}")
            self.update_button_state("results_ready")  # Fall back to old workflow
    def handle_action_button(self):
        """Handle clicks on the dynamic action button based on current state."""
        if self.app_state == "idle":
            self.start_processing()
        elif self.app_state == "processing":
            self.cancel_processing()
        elif self.app_state == "results_ready":
            self.save_sentence_results_csv()
    
    def update_button_state(self, new_state):
        """Update the dynamic button based on application state."""
        self.app_state = new_state
        
        if new_state == "idle":
            self.action_button.setText("Process Words (Audio + Sentences + Images)")
            self.action_button.setStyleSheet("QPushButton { font-weight: bold; padding: 12px; background-color: #4CAF50; color: white; }")
            self.action_button.setEnabled(True)
        elif new_state == "processing":
            self.action_button.setText("Cancel Processing")
            self.action_button.setStyleSheet("QPushButton { font-weight: bold; padding: 12px; background-color: #f44336; color: white; }")
            self.action_button.setEnabled(True)
        elif new_state == "results_ready":
            self.action_button.setText("Save as Anki CSV")
            self.action_button.setStyleSheet("QPushButton { font-weight: bold; padding: 12px; background-color: #2196F3; color: white; }")
            self.action_button.setEnabled(True)
    
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
        
        # Cancel image worker if running
        if hasattr(self, 'image_worker') and self.image_worker.isRunning():
            self.image_worker.abort()
            self.image_worker.wait()
            self.log("Image fetching cancelled.")
        
        self.log("Processing cancelled.")
        
        # Update UI
        self.update_button_state("idle")
        
        # Update button state to idle
        self.update_button_state("idle")
    
    def update_audio_progress(self, current, total):
        """Update the audio download progress bar."""
        percentage = int((current / total) * 100) if total > 0 else 0
        self.audio_progress_bar.setValue(percentage)
    
    def sentence_generation_error(self, error_msg):
        """Handle errors in sentence generation."""
        self.log(f"Error in sentence generation: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)
        
        # Update UI
        self.update_button_state("idle")
    
    def update_sentence_progress(self, current, total):
        """Update the sentence generation progress bar."""
        percentage = int((current / total) * 100) if total > 0 else 0
        self.sentence_progress_bar.setValue(percentage)
    
    def update_image_progress(self, current, total):
        """Update the image fetching progress bar."""
        percentage = int((current / total) * 100) if total > 0 else 0
        self.image_progress_bar.setValue(percentage)
    
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
                QMessageBox.information(self, "Saved", f"Results saved to {file_path}\n\nAudio files have been copied to your Anki media folder.")
                self.log(f"Anki CSV export saved to {file_path}")
                # Transition button back to processing mode to allow new processing
                self.update_button_state("idle")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error saving CSV file: {str(e)}")

    def _generate_cards_for_review(self):
        """Generate cards from sentence results for review interface."""
        content = self.sentence_results.toPlainText()
        
        # Parse the content to extract words and sentences
        cards_data = []
        
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
                word_cards = self._generate_anki_cards(word, sentences[:3], grammar_info)
                
                # Add metadata for each card
                english_translation = grammar_info.get('english_word', 'Unknown')
                image_url = self.word_image_urls.get(word, None) if hasattr(self, 'word_image_urls') else None
                
                for card in word_cards:
                    # Add preview information (Danish word, English translation, image status)
                    card_with_metadata = {
                        'card_data': card,
                        'danish_word': word,
                        'english_word': english_translation,
                        'image_url': image_url
                    }
                    cards_data.append(card_with_metadata)
        
        return cards_data

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
            # Don't write header for Anki import - Anki doesn't expect headers
            # Write data directly
            writer.writerows(csv_data)
        
        # After successful CSV export, copy audio files to Anki
        self._copy_audio_files_to_anki(csv_data)
    
    def _extract_grammar_info(self, block):
        """Extract grammar information from a word block."""
        grammar_info = {
            'ipa': '',
            'type': '',
            'gender': '',
            'plural': '',
            'inflections': '',
            'definition': '',
            'english_word': ''
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
            
            # Extract English word
            english_word_match = re.search(r'English word:\s*([^\n]+)', grammar_section)
            if english_word_match:
                grammar_info['english_word'] = english_word_match.group(1).strip()
        
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
        
        # Helper function to get image URL for a word
        def get_image_url(word):
            """Get the image URL for a word, or return placeholder if not available."""
            if hasattr(self, 'word_image_urls') and word in self.word_image_urls:
                image_url = self.word_image_urls[word]
                if image_url:
                    return f'<image src="{image_url}">'
            return '<image src="myimage.jpg">'  # Fallback placeholder
        
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
        grammar_details = self._format_grammar_details(grammar_info)
        ipa_info = grammar_info['ipa'] if grammar_info['ipa'] else f'/IPA_for_{word}/'
        if not ipa_info.startswith('/'):
            ipa_info = f'/{ipa_info}/'
        # Remove English part from definition (if present)
        def strip_english_from_definition(definition):
            # Remove any English translation after a dash or parenthesis, e.g. "en kat - a cat" or "en kat (cat)"
            if not definition:
                return ''
            # Remove dash + English
            definition = re.sub(r'\s*[-–—]\s*[A-Za-z ,;\'\"()]+$', '', definition)
            # Remove parenthetical English at end
            definition = re.sub(r'\s*\([A-Za-z ,;\'\"-]+\)\s*$', '', definition)
            return definition.strip()
        definition_clean = strip_english_from_definition(grammar_info.get('definition', ''))
        cards.append([
            sentence1_with_blank,                    # Front (Eksempel med ord fjernet eller blankt)
            get_image_url(word),                     # Front (Billede)
            definition_clean,                        # Front (Definition, grundform, osv.)
            word,                                    # Back (et enkelt ord/udtryk, uden kontekst)
            sentences[0],                            # - Hele sætningen (intakt)
            f'{grammar_details} [sound:{word}.mp3]',        # - Ekstra info (IPA, køn, bøjning)
            'y'                                      # • Lav 2 kort?
        ])
        
        # Card Type 2: Fill-in-the-blank + definition (definition present, no English)
        sentence1_no_word = remove_word_from_sentence(sentences[0], word, use_blank=False)
        cards.append([
            sentence1_no_word,                       # Front (Eksempel med ord fjernet eller blankt)
            get_image_url(word),                     # Front (Billede)
            f'{word} - {definition_clean}',                        # Front (Definition, grundform, osv.)
            '',                                      # Back (et enkelt ord/udtryk, uden kontekst) - empty for card 2
            sentences[0],                            # - Hele sætningen (intakt)
            f'{grammar_details} [sound:{word}.mp3]', # - Ekstra info (IPA, køn, bøjning)
            ''                                       # • Lav 2 kort? - empty for card 2
        ])
        
        # Card Type 3: New sentence with blank
        sentence2_with_blank = remove_word_from_sentence(sentences[1], word, use_blank=True)
        cards.append([
            sentence2_with_blank,                    # Front (Eksempel med ord fjernet eller blankt)
            get_image_url(word),                     # Front (Billede)
            definition_clean,                        # Front (Definition, grundform, osv.)
            word,                                    # Back (et enkelt ord/udtryk, uden kontekst)
            sentences[1],                            # - Hele sætningen (intakt)
            f'{grammar_details} [sound:{word}.mp3]', # - Ekstra info (IPA, køn, bøjning)
            ''                                       # • Lav 2 kort? - empty for card 3
        ])
        
        return cards
    
    def _format_definition(self, word, grammar_info):
        """Format definition text for Card Type 2."""
        # Add basic definition if available
        if grammar_info.get('definition'):
            definition = grammar_info['definition']
            
            # Remove the word itself from the definition if it appears at the beginning
            # This handles cases where ChatGPT includes the word redundantly
            word_lower = word.lower()
            definition_lower = definition.lower()
            
            # Check if definition starts with the word (with optional punctuation/formatting)
            if definition_lower.startswith(word_lower):
                # Remove the word and any following punctuation/whitespace
                remaining = definition[len(word):].lstrip(' :-–—')
                if remaining:
                    definition = remaining
                else:
                    definition = "Definition nødvendig"
            
            return definition
        else:
            return "Definition nødvendig"
    
    def _format_grammar_details(self, grammar_info):
        """Format detailed grammar information in the format: /IPA/ – type, inflections."""
        parts = []
        
        # Add IPA if available
        if grammar_info.get('ipa'):
            ipa = grammar_info['ipa']
            if not ipa.startswith('/'):
                ipa = f'/{ipa}/'
            parts.append(ipa)
        
        # Build the main grammar section
        grammar_parts = []
        
        # Add type (verbum, substantiv, etc.)
        if grammar_info.get('type'):
            grammar_parts.append(grammar_info['type'])
        
        # Add gender for nouns (if applicable)
        if grammar_info.get('gender'):
            grammar_parts.append(f"køn: {grammar_info['gender']}")
        
        # Add inflections or plural form
        if grammar_info.get('inflections'):
            grammar_parts.append(grammar_info['inflections'])
        elif grammar_info.get('plural'):
            grammar_parts.append(f"flertal: {grammar_info['plural']}")
        
        # Combine parts with proper formatting
        if parts and grammar_parts:
            return f"{parts[0]} – {', '.join(grammar_parts)}"
        elif parts:
            return parts[0]
        elif grammar_parts:
            return ', '.join(grammar_parts)
        else:
            return "Grammatik info nødvendig"


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    
    # Set up application style
    app.setStyle("Fusion")
    
    window = DanishAudioApp()
    window.show()
    
    sys.exit(app.exec_())
