"""Main processing tab widget."""

import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                            QTextEdit, QProgressBar, QLabel, QPushButton)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal, QTimer, QMimeData


class MainTab(QWidget):
    """Main processing tab for word input and progress tracking."""
    
    # Signals
    process_words_requested = pyqtSignal(list)  # List of words to process
    cancel_processing_requested = pyqtSignal()
    save_csv_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.app_state = "idle"  # idle, processing, results_ready
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the main processing tab UI."""
        layout = QVBoxLayout()
        
        # Word input area
        word_group = QGroupBox("Danish Words to Process")
        word_layout = QVBoxLayout()
        
        # Text area for words
        self.word_input = QTextEdit()
        self.word_input.setPlaceholderText(
            "Enter Danish words, one per line\n\n"
            "This will generate:\n"
            "• Audio pronunciations\n"
            "• Example sentences with grammar info\n"
            "• Images from dictionary sources\n"
            "• Anki-ready CSV export\n\n"
            "Text is automatically cleaned and formatted as you type."
        )
        self.word_input.setMinimumHeight(120)
        
        # Override paste event to clean formatting
        original_paste = self.word_input.insertFromMimeData
        self.word_input.insertFromMimeData = self._on_paste
        self._original_paste = original_paste
        
        # Connect text change event for other cleaning (less aggressive now)
        self.word_input.textChanged.connect(self._auto_clean_text)
        self._cleaning_in_progress = False  # Flag to prevent recursion
        
        # Also clean on focus lost for better UX
        self.word_input.focusOutEvent = self._on_focus_out
        
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
        self.action_button.clicked.connect(self._handle_action_button)
        self.action_button.setStyleSheet("QPushButton { font-weight: bold; padding: 12px; }")
        button_layout.addWidget(self.action_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def _handle_action_button(self):
        """Handle clicks on the dynamic action button based on current state."""
        if self.app_state == "idle":
            self._request_process_words()
        elif self.app_state == "processing":
            self.cancel_processing_requested.emit()
        elif self.app_state == "results_ready":
            self.save_csv_requested.emit()
    
    def _request_process_words(self):
        """Parse words from input and emit processing request."""
        word_text = self.word_input.toPlainText()
        if not word_text:
            # This should be handled by the main app with a message box
            return
        
        # Text is already cleaned by auto-cleaning, just filter out empty lines
        words = [line.strip() for line in word_text.split('\n') if line.strip()]
        
        if words:
            self.process_words_requested.emit(words)
    
    def _clean_text_input(self, text):
        """Clean text input by stripping formatting and converting to lowercase."""
        if not text:
            return ""
        
        # Strip all formatting and convert to lowercase
        cleaned = text.strip().lower()
        
        # Remove any HTML tags or markup
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # Remove any markdown formatting (bold, italic, etc.)
        cleaned = re.sub(r'[*_`~]', '', cleaned)
        
        # Normalize whitespace but preserve line breaks
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)  # Replace multiple spaces/tabs with single space
        cleaned = re.sub(r'\n+', '\n', cleaned)   # Replace multiple newlines with single newline
        
        # Keep only valid Danish characters, spaces, and newlines
        cleaned = re.sub(r'[^a-zA-ZæøåÆØÅ\-\'\s\n]', '', cleaned)
        
        return cleaned.strip()
    
    def _on_paste(self, source):
        """Handle paste events and clean the pasted text."""
        # Get the text from the clipboard
        if source.hasText():
            pasted_text = source.text()
            
            # Clean each line of the pasted text
            cleaned_lines = []
            for line in pasted_text.split('\n'):
                cleaned_line = self._clean_text_input(line)
                if cleaned_line:  # Only keep non-empty cleaned lines
                    cleaned_lines.append(cleaned_line)
            
            cleaned_text = '\n'.join(cleaned_lines)
            
            # Create a new mime data object with cleaned text
            cleaned_mime = QMimeData()
            cleaned_mime.setText(cleaned_text)
            
            # Call the original paste method with cleaned data
            self._original_paste(cleaned_mime)
        else:
            # If no text, use original paste behavior
            self._original_paste(source)
    
    def _auto_clean_text(self):
        """Automatically clean text - now mainly for converting to lowercase."""
        if self._cleaning_in_progress:
            return  # Prevent recursion
        
        # Get current text
        current_text = self.word_input.toPlainText()
        if not current_text:
            return
        
        # Simple cleaning - mainly lowercase conversion for typed text
        cleaned_lines = []
        text_changed = False
        
        for line in current_text.split('\n'):
            original_line = line
            # Convert to lowercase if it's not already
            if line != line.lower():
                cleaned_line = line.lower()
                text_changed = True
            else:
                cleaned_line = line
            
            cleaned_lines.append(cleaned_line)
        
        # Only update if text actually changed
        if text_changed:
            self._cleaning_in_progress = True
            
            # Get current cursor position
            cursor = self.word_input.textCursor()
            cursor_position = cursor.position()
            
            cleaned_text = '\n'.join(cleaned_lines)
            
            # Update the text
            self.word_input.setPlainText(cleaned_text)
            
            # Restore cursor position
            new_length = len(cleaned_text)
            if cursor_position > new_length:
                cursor_position = new_length
            
            cursor = self.word_input.textCursor()
            cursor.setPosition(cursor_position)
            self.word_input.setTextCursor(cursor)
            
            self._cleaning_in_progress = False
    
    def _on_focus_out(self, event):
        """Perform thorough cleaning when user finishes editing."""
        # Call the original focus out event first
        QTextEdit.focusOutEvent(self.word_input, event)
        
        # Now do thorough cleaning
        current_text = self.word_input.toPlainText()
        if not current_text:
            return
        
        # Clean each line thoroughly
        cleaned_lines = []
        for line in current_text.split('\n'):
            cleaned_line = self._clean_text_input(line)
            if cleaned_line:  # Only keep non-empty lines after thorough cleaning
                cleaned_lines.append(cleaned_line)
        
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Update if different
        if cleaned_text != current_text:
            self.word_input.setPlainText(cleaned_text)
    
    def update_button_state(self, new_state):
        """Update the dynamic button based on application state."""
        self.app_state = new_state
        
        if new_state == "idle":
            self.action_button.setText("Process Words (Audio + Sentences + Images)")
            self.action_button.setStyleSheet(
                "QPushButton { font-weight: bold; padding: 12px; "
                "background-color: #4CAF50; color: white; }"
            )
            self.action_button.setEnabled(True)
        elif new_state == "processing":
            self.action_button.setText("Cancel Processing")
            self.action_button.setStyleSheet(
                "QPushButton { font-weight: bold; padding: 12px; "
                "background-color: #f44336; color: white; }"
            )
            self.action_button.setEnabled(True)
        elif new_state == "results_ready":
            self.action_button.setText("Save as Anki CSV")
            self.action_button.setStyleSheet(
                "QPushButton { font-weight: bold; padding: 12px; "
                "background-color: #2196F3; color: white; }"
            )
            self.action_button.setEnabled(True)
    
    def update_audio_progress(self, current, total):
        """Update the audio download progress bar."""
        percentage = int((current / total) * 100) if total > 0 else 0
        self.audio_progress_bar.setValue(percentage)
    
    def update_sentence_progress(self, current, total):
        """Update the sentence generation progress bar."""
        percentage = int((current / total) * 100) if total > 0 else 0
        self.sentence_progress_bar.setValue(percentage)
    
    def update_image_progress(self, current, total):
        """Update the image fetching progress bar."""
        percentage = int((current / total) * 100) if total > 0 else 0
        self.image_progress_bar.setValue(percentage)
    
    def reset_progress(self):
        """Reset all progress bars to 0."""
        self.audio_progress_bar.setValue(0)
        self.sentence_progress_bar.setValue(0)
        self.image_progress_bar.setValue(0)
        self.sentence_results.clear()
    
    def log_message(self, message):
        """Add a message to the log output."""
        self.log_output.append(message)
        # Scroll to the bottom
        cursor = self.log_output.textCursor()
        cursor.movePosition(cursor.End)
        self.log_output.setTextCursor(cursor)
    
    def set_results(self, results_text):
        """Set the results text area content."""
        self.sentence_results.setText(results_text)
    
    def get_results(self):
        """Get the current results text."""
        return self.sentence_results.toPlainText()
