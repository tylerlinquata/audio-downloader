"""Review tab widget for flashcard review and editing."""

import os
import re
import gc  # For garbage collection
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                            QTableWidget, QTableWidgetItem, QLabel, QPushButton,
                            QCheckBox, QHeaderView, QAbstractItemView,
                            QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl, QTimer
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
        finally:
            # Always emit finished signal
            self.finished.emit()


class ReviewTab(QWidget):
    """Review tab for editing flashcards before export."""
    
    # Signals
    export_cards_requested = pyqtSignal(list)  # List of selected card data
    back_to_processing_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.generated_cards = []
        self.image_loaders = []
        self.word_to_rows = {}  # Map Danish words to list of row indices
        self.pending_image_loads = []  # Queue for pending image loads
        self.max_concurrent_loaders = 3  # Limit concurrent image loaders (reduced for stability)
        self.active_loaders = 0
        self._columns_manually_resized = False  # Track if user has manually resized columns
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
            "💡 The 'Preview' columns show the source image and English translation for reference only - they are NOT included in your Anki cards.\n"
            "🔄 When you change an image URL, all cards for the same Danish word will be updated automatically."
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
        
        # Configure table appearance with resizable columns
        header = self.card_table.horizontalHeader()
        header.setStretchLastSection(True)  # Make last column stretch to fill remaining space
        
        # Set initial column widths and make all columns resizable
        header.setSectionResizeMode(QHeaderView.Interactive)  # Make all columns manually resizable
        
        # Connect signal to track manual column resizing
        header.sectionResized.connect(self._on_section_resized)
        
        # Set reasonable initial widths for each column (will be adjusted by resizeEvent)
        initial_widths = [70, 120, 120, 200, 150, 250, 100, 300, 200, 90]
        for col, width in enumerate(initial_widths):
            self.card_table.setColumnWidth(col, width)
        
        # Set minimum column widths to prevent columns from becoming too small
        header.setMinimumSectionSize(50)  # Minimum width for any column
        
        # Enable horizontal scrolling when needed
        self.card_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        
        # Enable word wrapping for better text display
        self.card_table.setWordWrap(True)
        
        self.card_table.setAlternatingRowColors(True)
        self.card_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.card_table.verticalHeader().setVisible(False)
        self.card_table.setMinimumHeight(400)  # Give more space for the table
        
        # Add row height for better readability and image display
        self.card_table.verticalHeader().setDefaultSectionSize(80)
        
        table_layout.addWidget(self.card_table)
        
        # Connect table item changed signal to handle image URL updates
        self.card_table.itemChanged.connect(self._on_table_item_changed)
        
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
    
    def resizeEvent(self, event):
        """Handle window resize events to adjust column sizes proportionally."""
        super().resizeEvent(event)
        self._adjust_column_sizes()
    
    def _adjust_column_sizes(self):
        """Adjust column sizes based on available width."""
        try:
            available_width = self.card_table.viewport().width()
            if available_width < 100:  # Skip if table not properly sized yet
                return
            
            # Only auto-adjust if columns haven't been manually resized
            if not hasattr(self, '_columns_manually_resized'):
                # Define proportional widths (percentages of total width)
                column_proportions = {
                    0: 0.05,   # Include checkbox - 5%
                    1: 0.08,   # Preview: Image - 8%
                    2: 0.08,   # Preview: English - 8%
                    3: 0.15,   # Front example - 15%
                    4: 0.10,   # Front image - 10%
                    5: 0.20,   # Definition - 20%
                    6: 0.07,   # Back word - 7%
                    7: 0.20,   # Full sentence - 20%
                    8: 0.12,   # Grammar - 12%
                    9: 0.05    # Make 2 cards - 5%
                }
                
                # Calculate and set new widths
                for col, proportion in column_proportions.items():
                    new_width = max(50, int(available_width * proportion))  # Minimum 50px
                    self.card_table.setColumnWidth(col, new_width)
                
        except Exception as e:
            print(f"Error adjusting column sizes: {e}")
    
    def _on_section_resized(self, logicalIndex, oldSize, newSize):
        """Track when user manually resizes columns."""
        # Mark that columns have been manually resized
        self._columns_manually_resized = True
    
    def showEvent(self, event):
        """Handle show events to ensure proper column sizing."""
        super().showEvent(event)
        # Delay column adjustment to ensure table is properly rendered
        if hasattr(self, 'card_table'):
            QTimer.singleShot(100, self._adjust_column_sizes)
    
    def populate_cards(self, cards_data):
        """Populate the review table with generated cards."""
        if not cards_data:
            print("No cards data provided")
            return
            
        # Limit the number of cards to prevent system overload
        max_cards = 500  # Reasonable limit for GUI performance
        if len(cards_data) > max_cards:
            print(f"WARNING: Large dataset ({len(cards_data)} cards). Limiting to first {max_cards} for performance.")
            cards_data = cards_data[:max_cards]
            
        print(f"DEBUG: Starting to populate {len(cards_data)} cards...")
        
        self.generated_cards = cards_data
        self.card_table.setRowCount(len(cards_data))
        self.word_to_rows = {}  # Reset the word-to-rows mapping
        self.pending_image_loads = []  # Reset pending loads
        self.active_loaders = 0
        
        # Clear any existing image loaders to prevent resource leaks
        self._cleanup_image_loaders()
        
        for row, card_info in enumerate(cards_data):
            if row % 50 == 0:  # Log progress every 50 cards
                print(f"DEBUG: Processing card {row+1}/{len(cards_data)}")
            
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
            
            # Safely limit string lengths to prevent crashes
            danish_word = str(danish_word)[:100] if danish_word else "Unknown"
            english_word = str(english_word)[:100] if english_word else "Unknown"
            
            # Build mapping of Danish words to row indices
            if danish_word not in self.word_to_rows:
                self.word_to_rows[danish_word] = []
            self.word_to_rows[danish_word].append(row)
            
            # Include checkbox
            try:
                checkbox = QCheckBox()
                checkbox.setChecked(True)  # Default to selected
                checkbox.stateChanged.connect(self._update_card_status)
                self.card_table.setCellWidget(row, 0, checkbox)
            except Exception as e:
                print(f"Error creating checkbox for row {row}: {e}")
                continue  # Skip this row if checkbox creation fails
            
            # Column 1: Preview Image - Use queued loading system
            if image_url and isinstance(image_url, str) and image_url.strip():
                try:
                    image_label = QLabel()
                    image_label.setAlignment(Qt.AlignCenter)
                    image_label.setText("Queued")
                    image_label.setToolTip(f"Image URL: {image_url}")
                    image_label.setStyleSheet("QLabel { padding: 5px; background-color: #e3f2fd; }")
                    image_label.setMinimumSize(90, 70)
                    image_label.setMaximumSize(90, 70)
                    self.card_table.setCellWidget(row, 1, image_label)
                    
                    # Add to pending loads queue
                    self.pending_image_loads.append((row, 1, image_url))
                except Exception as e:
                    print(f"Error creating image label for row {row}: {e}")
            else:
                # Show placeholder for no image
                try:
                    no_image_label = QLabel("No Image")
                    no_image_label.setToolTip("No image URL available")
                    no_image_label.setAlignment(Qt.AlignCenter)
                    no_image_label.setStyleSheet("QLabel { padding: 5px; background-color: #ffebee; }")
                    no_image_label.setMinimumSize(90, 70)
                    no_image_label.setMaximumSize(90, 70)
                    self.card_table.setCellWidget(row, 1, no_image_label)
                except Exception as e:
                    print(f"Error creating no-image label for row {row}: {e}")
            
            # Column 2: Preview English Word
            try:
                english_preview = QTableWidgetItem(f"EN: {english_word}")
                english_preview.setToolTip(f"Danish: {danish_word} → English: {english_word}")
                english_preview.setFlags(Qt.ItemIsEnabled)  # Read-only
                self.card_table.setItem(row, 2, english_preview)
            except Exception as e:
                print(f"Error creating english preview for row {row}: {e}")
                # Create fallback item
                english_preview = QTableWidgetItem(str(english_word)[:50])  # Truncate long text
                self.card_table.setItem(row, 2, english_preview)
            
            # Card data columns (shifted by +2)
            for col, value in enumerate(card, 3):
                try:
                    # Safely convert value to string and limit length to prevent crashes
                    safe_value = str(value)[:1000] if value is not None else ""
                    item = QTableWidgetItem(safe_value)
                    item.setFlags(item.flags() | Qt.ItemIsEditable)  # Make cells editable
                    if col in [3, 5, 7, 8]:  # Example, Definition, Full Sentence, Grammar columns
                        item.setToolTip(safe_value[:500])  # Limit tooltip length
                    self.card_table.setItem(row, col, item)
                except Exception as e:
                    print(f"Error creating table item for row {row}, col {col}: {e}")
                    # Create minimal fallback item
                    fallback_item = QTableWidgetItem("Error")
                    self.card_table.setItem(row, col, fallback_item)
        
        print(f"DEBUG: Finished populating {len(cards_data)} cards. {len(self.pending_image_loads)} images queued for loading.")
        
        # Process images in smaller batches to prevent overwhelming the system
        self._batch_process_images()
        
        # Update status
        self._update_card_status()
        
        # Adjust column sizes after populating data
        QTimer.singleShot(200, self._adjust_column_sizes)
    
    def _batch_process_images(self):
        """Process images in smaller batches to prevent system overload."""
        # Limit initial batch size for large datasets
        if len(self.pending_image_loads) > 50:
            print(f"DEBUG: Large dataset detected ({len(self.pending_image_loads)} images). Processing in batches.")
            # Process first 10 images immediately, rest will be processed as they complete
            initial_batch = min(10, len(self.pending_image_loads))
            for _ in range(initial_batch):
                if self.pending_image_loads and self.active_loaders < self.max_concurrent_loaders:
                    row, col, url = self.pending_image_loads.pop(0)
                    self._start_image_load(row, col, url)
        else:
            # For smaller datasets, process normally
            self._process_image_queue()
    
    def _cleanup_image_loaders(self):
        """Clean up any existing image loaders to prevent resource leaks."""
        try:
            print(f"DEBUG: Cleaning up {len(self.image_loaders)} image loaders")
            for loader in self.image_loaders:
                try:
                    if loader.isRunning():
                        loader.wait(100)  # Wait up to 100ms for thread to finish
                    if loader.isRunning():
                        loader.terminate()  # Force terminate if still running
                    loader.deleteLater()  # Schedule for deletion
                except Exception as e:
                    print(f"Error cleaning up individual loader: {e}")
            
            self.image_loaders.clear()
            self.active_loaders = 0
            print("DEBUG: Cleaned up image loaders successfully")
        except Exception as e:
            print(f"Error cleaning up image loaders: {e}")
    
    def _process_image_queue(self):
        """Process the next batch of images from the queue."""
        while (self.active_loaders < self.max_concurrent_loaders and 
               self.pending_image_loads):
            
            row, col, url = self.pending_image_loads.pop(0)
            self._start_image_load(row, col, url)
    
    def _start_image_load(self, row, col, url):
        """Start loading a single image."""
        try:
            # Update label to show loading status
            widget = self.card_table.cellWidget(row, col)
            if widget and isinstance(widget, QLabel):
                widget.setText("Loading...")
                widget.setStyleSheet("QLabel { padding: 5px; background-color: #fff3e0; }")
            
            loader = ImageLoader(row, col, url)
            loader.image_loaded.connect(self._on_image_loaded)
            loader.finished.connect(lambda: self._on_loader_finished(loader))
            loader.start()
            
            self.image_loaders.append(loader)
            self.active_loaders += 1
            
        except Exception as e:
            print(f"Error starting image load for row {row}: {e}")
            # Mark as failed to load
            widget = self.card_table.cellWidget(row, col)
            if widget and isinstance(widget, QLabel):
                widget.setText("Failed")
                widget.setStyleSheet("QLabel { padding: 5px; background-color: #ffebee; }")
                widget.setToolTip(f"Failed to load image: {e}")
    
    def _on_loader_finished(self, loader):
        """Handle when an image loader finishes (success or failure)."""
        try:
            if loader in self.image_loaders:
                self.image_loaders.remove(loader)
            self.active_loaders = max(0, self.active_loaders - 1)
            
            # Process next item in queue
            self._process_image_queue()
            
        except Exception as e:
            print(f"Error handling loader finish: {e}")

    def _on_image_loaded(self, row, col, pixmap):
        """Callback when an image is successfully loaded."""
        try:
            # Validate row and column bounds
            if row < 0 or row >= self.card_table.rowCount():
                print(f"Invalid row {row} for image loading")
                return
            if col < 0 or col >= self.card_table.columnCount():
                print(f"Invalid column {col} for image loading")
                return
                
            widget = self.card_table.cellWidget(row, col)
            if widget and isinstance(widget, QLabel):
                widget.setPixmap(pixmap)
                widget.setText("")  # Clear the loading text
                widget.setStyleSheet("QLabel { padding: 5px; }")
        except Exception as e:
            print(f"Error setting loaded image for row {row}, col {col}: {e}")

    def _on_table_item_changed(self, item):
        """Handle changes to table items and refresh image preview if image URL changed."""
        if not item:
            return
        
        row = item.row()
        col = item.column()
        
        # Check if the changed item is in the "Front (Image)" column (column 4)
        if col == 4:
            new_image_url = item.text().strip()
            
            # Auto-wrap plain URLs with <image> tag
            formatted_url = self._format_image_url_for_anki(new_image_url)
            if formatted_url != new_image_url:
                # Update the cell with the formatted URL (this will prevent infinite recursion
                # because we're setting the same text that would result from this formatting)
                item.setText(formatted_url)
                new_image_url = formatted_url
            
            # Update all cards for the same Danish word
            self._update_image_for_word(row, new_image_url)
    
    def _update_image_for_word(self, changed_row, new_image_url):
        """Update the image URL for all cards belonging to the same Danish word."""
        # Find the Danish word for the changed row
        danish_word = self._get_danish_word_for_row(changed_row)
        if not danish_word or danish_word == "Unknown":
            # If we can't identify the word, just update the single row
            self._refresh_image_preview(changed_row, new_image_url)
            return
        
        # Get all rows for this Danish word
        word_rows = self.word_to_rows.get(danish_word, [changed_row])
        
        # Temporarily disconnect the itemChanged signal to prevent recursive calls
        self.card_table.itemChanged.disconnect(self._on_table_item_changed)
        
        try:
            # Update the Front (Image) column (column 4) for all cards of this word
            for row in word_rows:
                if row != changed_row:  # Skip the row that was just changed
                    item = self.card_table.item(row, 4)
                    if item:
                        item.setText(new_image_url)
                
                # Refresh the image preview for all rows (including the changed one)
                self._refresh_image_preview(row, new_image_url)
        finally:
            # Reconnect the signal
            self.card_table.itemChanged.connect(self._on_table_item_changed)
    
    def _get_danish_word_for_row(self, row):
        """Get the Danish word associated with a specific row."""
        if row < len(self.generated_cards):
            card_info = self.generated_cards[row]
            if isinstance(card_info, dict):
                return card_info.get('danish_word', "Unknown")
        return "Unknown"
    
    def _refresh_image_preview(self, row, image_url):
        """Refresh the image preview in column 1 for the given row with a new image URL."""
        try:
            # Validate row bounds
            if row < 0 or row >= self.card_table.rowCount():
                print(f"Invalid row {row} for image refresh")
                return
                
            # Extract the actual image URL from the Anki image tag format
            # Format: <image src="url"> or just the URL
            actual_url = self._extract_image_url_from_anki_format(image_url)
            
            if actual_url and actual_url.strip():
                # Create new loading label
                image_label = QLabel()
                image_label.setAlignment(Qt.AlignCenter)
                image_label.setText("Loading...")
                image_label.setToolTip(f"Image URL: {actual_url}")
                image_label.setStyleSheet("QLabel { padding: 5px; background-color: #fff3e0; }")
                image_label.setMinimumSize(90, 70)
                image_label.setMaximumSize(90, 70)
                self.card_table.setCellWidget(row, 1, image_label)
                
                # Load the new image
                loader = ImageLoader(row, 1, actual_url)
                loader.image_loaded.connect(self._on_image_loaded)
                loader.start()
                self.image_loaders.append(loader)
            else:
                # No valid URL, show "No Image" label
                no_image_label = QLabel("No Image")
                no_image_label.setAlignment(Qt.AlignCenter)
                no_image_label.setStyleSheet("QLabel { padding: 5px; background-color: #ffebee; }")
                no_image_label.setMinimumSize(90, 70)
                no_image_label.setMaximumSize(90, 70)
                self.card_table.setCellWidget(row, 1, no_image_label)
        except Exception as e:
            print(f"Error refreshing image preview for row {row}: {e}")
    
    def _extract_image_url_from_anki_format(self, image_text):
        """Extract the actual image URL from Anki image format or plain URL."""
        if not image_text:
            return None
        
        # Check if it's in Anki format: <image src="url">
        match = re.search(r'<image\s+src="([^"]+)">', image_text)
        if match:
            return match.group(1)
        
        # Check if it's a plain URL (starts with http:// or https://)
        if image_text.startswith(('http://', 'https://')):
            return image_text
        
        # Return None if no valid URL found
        return None
    
    def _format_image_url_for_anki(self, image_text):
        """Format image URL for Anki by wrapping plain URLs with <image> tag."""
        if not image_text:
            return image_text
        
        image_text = image_text.strip()
        
        # If it's already in Anki format, return as-is
        if re.match(r'<image\s+src="[^"]+">$', image_text):
            return image_text
        
        # If it's a plain URL, wrap it with <image> tag
        if image_text.startswith(('http://', 'https://')):
            return f'<image src="{image_text}">'
        
        # For other formats (like local files), also wrap them
        if image_text and not image_text.startswith('<'):
            return f'<image src="{image_text}">'
        
        # Return as-is for any other cases
        return image_text
    
    def _update_card_status(self):
        """Update the status label showing selected card count."""
        try:
            selected_count = 0
            total_count = self.card_table.rowCount()
            
            for row in range(total_count):
                try:
                    checkbox = self.card_table.cellWidget(row, 0)
                    if checkbox and isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                        selected_count += 1
                except Exception as e:
                    print(f"Error checking checkbox in row {row}: {e}")
                    # Continue counting, assuming this checkbox is unchecked
                    pass
            
            self.card_status_label.setText(f"Cards: {selected_count} selected of {total_count} total")
        except Exception as e:
            print(f"Error updating card status: {e}")
            # Fallback status text
            self.card_status_label.setText("Cards: Status update error")
    
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
        print("DEBUG: Starting cleanup of review tab resources...")
        self._cleanup_image_loaders()
        
        # Clear data
        self.generated_cards = []
        self.word_to_rows = {}
        self.pending_image_loads = []
        
        # Clear table widgets properly
        self.card_table.clearContents()
        self.card_table.setRowCount(0)
        self.card_status_label.setText("No cards loaded")
        
        # Force garbage collection to free memory
        gc.collect()
        print("DEBUG: Review tab cleanup completed")
    
    def closeEvent(self, event):
        """Handle widget close event to clean up resources."""
        self._cleanup_image_loaders()
        super().closeEvent(event)
    
    def hideEvent(self, event):
        """Handle widget hide event to clean up resources when switching tabs."""
        # Don't cleanup when just hiding, as user might come back
        # Only cleanup on explicit close or app exit
        super().hideEvent(event)
