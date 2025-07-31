"""Settings tab widget."""

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                            QLineEdit, QPushButton, QComboBox, QFormLayout,
                            QFileDialog)
from PyQt5.QtCore import pyqtSignal


class SettingsTab(QWidget):
    """Settings tab for configuration."""
    
    # Signals
    settings_saved = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the settings tab UI."""
        layout = QVBoxLayout()
        
        # Folders settings
        folders_group = QGroupBox("Folders")
        folders_layout = QFormLayout()
        
        # Output directory
        self.output_dir_input = QLineEdit()
        default_output_dir = os.path.expanduser("~/Documents/danish_pronunciations")
        self.output_dir_input.setText(default_output_dir)
        browse_output_button = QPushButton("Browse...")
        browse_output_button.clicked.connect(self._browse_output_dir)
        
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_dir_input)
        output_layout.addWidget(browse_output_button)
        
        folders_layout.addRow("Output Directory:", output_layout)
        
        # Anki media folder
        self.anki_dir_input = QLineEdit()
        default_anki_folder = os.path.expanduser(
            "~/Library/Application Support/Anki2/User 1/collection.media"
        )
        self.anki_dir_input.setText(default_anki_folder)
        browse_anki_button = QPushButton("Browse...")
        browse_anki_button.clicked.connect(self._browse_anki_dir)
        
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
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter your OpenAI API key")
        api_layout.addRow("OpenAI API Key:", self.api_key_input)
        
        # Forvo API Key
        self.forvo_api_key_input = QLineEdit()
        self.forvo_api_key_input.setEchoMode(QLineEdit.Password)
        self.forvo_api_key_input.setPlaceholderText("Enter your Forvo API key")
        api_layout.addRow("Forvo API Key:", self.forvo_api_key_input)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # Save settings button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.settings_saved.emit)
        layout.addWidget(save_button)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        self.setLayout(layout)
    
    def _browse_output_dir(self):
        """Browse for output directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.output_dir_input.text()
        )
        
        if dir_path:
            self.output_dir_input.setText(dir_path)
    
    def _browse_anki_dir(self):
        """Browse for Anki media directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Anki Media Folder", self.anki_dir_input.text()
        )
        
        if dir_path:
            self.anki_dir_input.setText(dir_path)
    
    def get_settings(self):
        """Get current settings as a dictionary."""
        return {
            'output_dir': self.output_dir_input.text(),
            'anki_dir': self.anki_dir_input.text(),
            'openai_api_key': self.api_key_input.text(),
            'forvo_api_key': self.forvo_api_key_input.text(),
            'cefr_level': self.cefr_combo.currentText()
        }
    
    def load_settings(self, settings_dict):
        """Load settings from a dictionary."""
        if 'output_dir' in settings_dict and settings_dict['output_dir']:
            self.output_dir_input.setText(settings_dict['output_dir'])
        
        if 'anki_dir' in settings_dict and settings_dict['anki_dir']:
            self.anki_dir_input.setText(settings_dict['anki_dir'])
            
        if 'openai_api_key' in settings_dict and settings_dict['openai_api_key']:
            self.api_key_input.setText(settings_dict['openai_api_key'])
            
        if 'forvo_api_key' in settings_dict and settings_dict['forvo_api_key']:
            self.forvo_api_key_input.setText(settings_dict['forvo_api_key'])
            
        if 'cefr_level' in settings_dict and settings_dict['cefr_level']:
            self.cefr_combo.setCurrentText(settings_dict['cefr_level'])
