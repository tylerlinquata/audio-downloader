"""Review tab widget for flashcard review and editing."""

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                            QTableWidget, QTableWidgetItem, QLabel, QPushButton,
                            QCheckBox, QHeaderView, QAbstractItemView,
                            QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QPixmap
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import csv
import requests
from io import BytesIO


class ImageLoader(QThread):
    """Thread for loading images asynchronously."""
    image_loaded = pyqtSignal(int, int, QPixmap)  # row, col, pixmap
    
    def __init__(self, row, col, url):
        super().__init__()
        self.row = row
        self.col = col
        self.url = url
    
    def run(self):
        """Load image from URL."""
        try:
            # Validate URL
            if not self.url or not isinstance(self.url, str):
                print(f"Error loading image: Invalid URL: {self.url}")
                return
                
            # Use requests library instead of Qt networking to avoid Qt object lifecycle issues
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible)',
                'Accept': 'image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = requests.get(self.url, headers=headers, timeout=10, stream=True)
            response.raise_for_status()
            
            # Read the image data
            image_data = BytesIO(response.content)
            pixmap = QPixmap()
            
            if pixmap.loadFromData(image_data.getvalue()):
                # Scale the image to fit the cell
                scaled_pixmap = pixmap.scaled(90, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_loaded.emit(self.row, self.col, scaled_pixmap)
            else:
                print(f"Failed to load image data from {self.url}")
                
        except requests.exceptions.RequestException as e:
            print(f"Network error loading image from '{self.url}': {e}")
        except Exception as e:
            print(f"Error loading image from URL '{self.url}': {e}")
            print(f"URL type: {type(self.url)}")
            print(f"URL value: {repr(self.url)}")


class ReviewTab(QWidget):
    """Review tab for editing flashcards before export."""
    
    # Signals
    export_cards_requested = pyqtSignal(list)  # List of selected card data
    back_to_processing_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.generated_cards = []
        self.image_loaders = []
        self.setup_ui()
    
    def setup_ui(self):
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
        instructions.setStyleSheet(
            "QLabel { padding: 10px; background-color: #4CAF50; "
            "border: 1px solid #d0d0d0; border-radius: 5px; }"
        )
        header_layout.addWidget(instructions)
        
        header_group.setLayout(header_layout)
        
        # Card table
        table_group = QGroupBox("Generated Cards")
        table_layout = QVBoxLayout()
        
        self.card_table = QTableWidget()
        self.card_table.setColumnCount(10)  # Include checkbox column + preview columns
        headers = [
            "Include", "Preview: Image", "Preview: English", "Front (Example)", 
            "Front (Image)", "Front (Definition)", "Back (Word)", "Full Sentence", 
            "Grammar Info", "Make 2 Cards"
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
        select_all_btn.clicked.connect(self._select_all_cards)
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All Cards")
        deselect_all_btn.clicked.connect(self._deselect_all_cards)
        button_layout.addWidget(deselect_all_btn)
        
        button_layout.addStretch()
        
        # Navigation buttons
        back_to_process_btn = QPushButton("← Back to Processing")
        back_to_process_btn.clicked.connect(self.back_to_processing_requested.emit)
        button_layout.addWidget(back_to_process_btn)
        
        self.export_csv_btn = QPushButton("Export Selected Cards to CSV")
        self.export_csv_btn.clicked.connect(self._export_cards)
        self.export_csv_btn.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 10px; "
            "background-color: #4CAF50; color: white; }"
        )
        button_layout.addWidget(self.export_csv_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def populate_cards(self, cards_data):
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
                # Fallback for old format
                card = card_info
                danish_word = "Unknown"
                english_word = "Unknown"
                image_url = None
            
            # Include checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(True)  # Default to selected
            checkbox.stateChanged.connect(self._update_card_status)
            self.card_table.setCellWidget(row, 0, checkbox)
            
            # Column 1: Preview Image
            if image_url and isinstance(image_url, str) and image_url.strip():
                image_label = QLabel()
                image_label.setAlignment(Qt.AlignCenter)
                image_label.setText("🖼️ Loading...")
                image_label.setToolTip(f"Image URL: {image_url}")
                image_label.setStyleSheet("QLabel { padding: 5px; }")
                image_label.setMinimumSize(90, 70)
                image_label.setMaximumSize(90, 70)
                self.card_table.setCellWidget(row, 1, image_label)
                loader = ImageLoader(row, 1, image_url)
                loader.image_loaded.connect(self._on_image_loaded)
                loader.start()
                self.image_loaders.append(loader)
            else:
                no_image_label = QLabel("❌ No Image")
                no_image_label.setAlignment(Qt.AlignCenter)
                no_image_label.setStyleSheet("QLabel { padding: 5px; }")
                no_image_label.setMinimumSize(90, 70)
                no_image_label.setMaximumSize(90, 70)
                self.card_table.setCellWidget(row, 1, no_image_label)
            
            # Column 2: Preview English Word
            english_preview = QTableWidgetItem(f"🇬🇧 {english_word}")
            english_preview.setToolTip(f"Danish: {danish_word} → English: {english_word}")
            english_preview.setFlags(Qt.ItemIsEnabled)  # Read-only
            self.card_table.setItem(row, 2, english_preview)
            
            # Card data columns (shifted by +2)
            for col, value in enumerate(card, 3):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() | Qt.ItemIsEditable)  # Make cells editable
                if col in [3, 5, 7, 8]:  # Example, Definition, Full Sentence, Grammar columns
                    item.setToolTip(str(value))
                self.card_table.setItem(row, col, item)
        
        # Update status
        self._update_card_status()
    
    def _on_image_loaded(self, row, col, pixmap):
        """Callback when an image is successfully loaded."""
        widget = self.card_table.cellWidget(row, col)
        if widget and isinstance(widget, QLabel):
            widget.setPixmap(pixmap)
            widget.setText("")  # Clear the loading text
    
    def _update_card_status(self):
        """Update the status label showing selected card count."""
        selected_count = 0
        total_count = self.card_table.rowCount()
        
        for row in range(total_count):
            checkbox = self.card_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_count += 1
        
        self.card_status_label.setText(f"Cards: {selected_count} selected of {total_count} total")
    
    def _select_all_cards(self):
        """Select all cards in the review table."""
        for row in range(self.card_table.rowCount()):
            checkbox = self.card_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
        self._update_card_status()
    
    def _deselect_all_cards(self):
        """Deselect all cards in the review table."""
        for row in range(self.card_table.rowCount()):
            checkbox = self.card_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
        self._update_card_status()
    
    def _export_cards(self):
        """Export selected cards to CSV."""
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
        default_dir = os.path.expanduser("~/Downloads")
        default_filename = os.path.join(default_dir, "anki_cards.csv")
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Anki CSV", default_filename, "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    # Don't write header for Anki import - Anki doesn't expect headers
                    # Write selected cards only
                    writer.writerows(selected_cards)
                
                # Emit signal with selected cards for audio file copying
                self.export_cards_requested.emit(selected_cards)
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save CSV file:\n{str(e)}")
    
    def cleanup(self):
        """Stop any running image loaders and clean up resources."""
        for loader in self.image_loaders:
            if loader.isRunning():
                loader.terminate()
                loader.wait()
        self.image_loaders.clear()
        
        # Clear data
        self.generated_cards = []
        self.card_table.setRowCount(0)
        self.card_status_label.setText("No cards loaded")
