#!/usr/bin/env python3
"""
Unit tests for Danish Audio Downloader GUI components.
"""

import unittest
import sys
import os
import csv
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from danish_audio_downloader.gui.app import DanishAudioApp


class TestDanishAudioApp(unittest.TestCase):
    """Test cases for the DanishAudioApp GUI class."""
    
    @classmethod
    def setUpClass(cls):
        """Set up QApplication for all tests."""
        # Only create QApplication if it doesn't exist
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create the main window
        self.main_window = DanishAudioApp()
        
        # Mock QSettings to avoid writing to actual system settings
        self.settings_patcher = patch.object(self.main_window, 'settings', spec=QSettings)
        self.mock_settings = self.settings_patcher.start()
        
    def tearDown(self):
        """Clean up after each test method."""
        self.settings_patcher.stop()
        self.main_window.close()
    
    def test_window_initialization(self):
        """Test that the main window initializes correctly."""
        self.assertIsNotNone(self.main_window)
        self.assertEqual(self.main_window.windowTitle(), "Danish Word Learning Assistant")
        self.assertTrue(self.main_window.minimumSize().width() >= 800)
        self.assertTrue(self.main_window.minimumSize().height() >= 600)
    
    def test_tabs_creation(self):
        """Test that all tabs are created correctly."""
        # Should have 2 tabs: Process Words, Settings
        self.assertEqual(self.main_window.tabs.count(), 2)
        
        # Check tab titles
        tab_titles = []
        for i in range(self.main_window.tabs.count()):
            tab_titles.append(self.main_window.tabs.tabText(i))
        
        expected_titles = ["Process Words", "Settings"]
        self.assertEqual(tab_titles, expected_titles)
    
    def test_main_tab_widgets(self):
        """Test that main tab widgets are created correctly."""
        # Check that essential widgets exist
        self.assertIsNotNone(self.main_window.word_input)
        self.assertIsNotNone(self.main_window.audio_progress_bar)
        self.assertIsNotNone(self.main_window.sentence_progress_bar)
        self.assertIsNotNone(self.main_window.image_progress_bar)
        self.assertIsNotNone(self.main_window.log_output)
        self.assertIsNotNone(self.main_window.action_button)
        self.assertIsNotNone(self.main_window.sentence_results)
        
        # Check initial states
        self.assertEqual(self.main_window.app_state, "idle")
    
    def test_settings_tab_widgets(self):
        """Test that settings tab widgets are created correctly."""
        # Check that essential widgets exist
        self.assertIsNotNone(self.main_window.output_dir_input)
        self.assertIsNotNone(self.main_window.anki_dir_input)
        self.assertIsNotNone(self.main_window.settings_api_key_input)
        self.assertIsNotNone(self.main_window.cefr_combo)
        
        # Check default values
        self.assertTrue(self.main_window.output_dir_input.text().endswith("danish_pronunciations"))
        self.assertTrue("collection.media" in self.main_window.anki_dir_input.text())
        self.assertEqual(self.main_window.cefr_combo.currentText(), "B1")
    @patch('danish_audio_downloader.gui.app.QFileDialog.getExistingDirectory')
    def test_browse_output_dir(self, mock_dir_dialog):
        """Test browsing for output directory."""
        test_dir = "/tmp/test_output"
        mock_dir_dialog.return_value = test_dir
        
        self.main_window.browse_output_dir()
        
        self.assertEqual(self.main_window.output_dir_input.text(), test_dir)
    
    @patch('danish_audio_downloader.gui.app.QFileDialog.getExistingDirectory')
    def test_browse_anki_dir(self, mock_dir_dialog):
        """Test browsing for Anki directory."""
        test_dir = "/tmp/test_anki"
        mock_dir_dialog.return_value = test_dir
        
        self.main_window.browse_anki_dir()
        
        self.assertEqual(self.main_window.anki_dir_input.text(), test_dir)
    
    def test_save_settings(self):
        """Test saving settings."""
        # Set some test values
        test_output_dir = "/tmp/test_output"
        test_anki_dir = "/tmp/test_anki"
        test_api_key = "test_api_key"
        test_cefr_level = "C1"
        
        self.main_window.output_dir_input.setText(test_output_dir)
        self.main_window.anki_dir_input.setText(test_anki_dir)
        self.main_window.settings_api_key_input.setText(test_api_key)
        self.main_window.cefr_combo.setCurrentText(test_cefr_level)
        
        with patch('danish_audio_downloader.gui.app.QMessageBox.information'):
            self.main_window.save_settings()
        
        # Check that settings were saved
        self.mock_settings.setValue.assert_any_call("output_dir", test_output_dir)
        self.mock_settings.setValue.assert_any_call("anki_dir", test_anki_dir)
        self.mock_settings.setValue.assert_any_call("openai_api_key", test_api_key)
        self.mock_settings.setValue.assert_any_call("cefr_level", test_cefr_level)
    
    def test_load_settings(self):
        """Test loading settings."""
        # Mock settings values
        test_output_dir = "/tmp/test_output"
        test_anki_dir = "/tmp/test_anki"
        test_api_key = "test_api_key"
        test_cefr_level = "A2"
        
        def mock_value(key):
            values = {
                "output_dir": test_output_dir,
                "anki_dir": test_anki_dir,
                "openai_api_key": test_api_key,
                "cefr_level": test_cefr_level
            }
            return values.get(key)
        
        self.mock_settings.value.side_effect = mock_value
        
        self.main_window.load_settings()
        
        # Check that values were loaded into widgets
        self.assertEqual(self.main_window.output_dir_input.text(), test_output_dir)
        self.assertEqual(self.main_window.anki_dir_input.text(), test_anki_dir)
        self.assertEqual(self.main_window.settings_api_key_input.text(), test_api_key)
        self.assertEqual(self.main_window.cefr_combo.currentText(), test_cefr_level)
    
    @patch('danish_audio_downloader.gui.app.QMessageBox.warning')
    def test_start_processing_no_words(self, mock_warning):
        """Test starting processing with no words."""
        # Clear the word input
        self.main_window.word_input.clear()
        
        self.main_window.start_processing()
        
        # Should show warning
        mock_warning.assert_called_once()
    
    @patch('danish_audio_downloader.gui.app.QMessageBox.warning')
    def test_start_processing_no_api_key(self, mock_warning):
        """Test starting processing with no API key."""
        # Set up test words but no API key in settings
        self.main_window.word_input.setPlainText("hund\nkat\nhus")
        self.main_window.settings_api_key_input.clear()
        
        self.main_window.start_processing()
        
        # Should show warning about missing API key
        mock_warning.assert_called_once()
    
    @patch('danish_audio_downloader.gui.app.Worker')
    @patch('os.makedirs')
    def test_start_processing_success(self, mock_makedirs, mock_worker_class):
        """Test successful start of unified processing."""
        # Set up test words and API key in settings
        self.main_window.word_input.setPlainText("hund\nkat\nhus")
        self.main_window.settings_api_key_input.setText("test-api-key")
        
        # Mock worker
        mock_worker = Mock()
        mock_worker_class.return_value = mock_worker
        
        self.main_window.start_processing()
        
        # Check that worker was created and started
        mock_worker_class.assert_called_once()
        mock_worker.start.assert_called_once()
        
        # Check UI state changes
        self.assertEqual(self.main_window.app_state, "processing")
        self.assertEqual(self.main_window.action_button.text(), "Cancel Processing")
    
    def test_update_audio_progress(self):
        """Test audio progress bar update."""
        self.main_window.update_audio_progress(3, 10)
        self.assertEqual(self.main_window.audio_progress_bar.value(), 30)
        
        self.main_window.update_audio_progress(10, 10)
        self.assertEqual(self.main_window.audio_progress_bar.value(), 100)
    
    def test_update_sentence_progress(self):
        """Test sentence progress bar update."""
        self.main_window.update_sentence_progress(3, 10)
        self.assertEqual(self.main_window.sentence_progress_bar.value(), 30)
        
        self.main_window.update_sentence_progress(10, 10)
        self.assertEqual(self.main_window.sentence_progress_bar.value(), 100)
    
    def test_update_image_progress(self):
        """Test image progress bar update."""
        self.main_window.update_image_progress(2, 5)
        self.assertEqual(self.main_window.image_progress_bar.value(), 40)
        
        self.main_window.update_image_progress(5, 5)
        self.assertEqual(self.main_window.image_progress_bar.value(), 100)
    
    def test_log_message(self):
        """Test logging a message."""
        test_message = "Test log message"
        initial_text = self.main_window.log_output.toPlainText()
        
        self.main_window.log(test_message)
        
        final_text = self.main_window.log_output.toPlainText()
        self.assertIn(test_message, final_text)
        self.assertNotEqual(initial_text, final_text)
    
    def test_audio_download_finished(self):
        """Test audio download finished callback and transition to sentence generation."""
        successful = ["hund", "kat"]
        failed = ["invalidword"]
        
        # Mock the sentence generation phase
        with patch.object(self.main_window, 'start_sentence_generation_phase') as mock_start_sentences:
            self.main_window.audio_download_finished(successful, failed)
        
        # Check that sentence generation phase is started
        mock_start_sentences.assert_called_once()
    
    def test_unified_processing_finished(self):
        """Test unified processing finished callback."""
        test_results = "**hund**\n\n1. Hunden løber hurtigt. - The dog runs fast.\n\n---"
        self.main_window.pending_sentence_generation = {
            'words': ['hund', 'kat'],
            'api_key': 'test-key',
            'cefr_level': 'B1'
        }
        self.main_window.final_sentence_results = test_results
        # Simulate image URLs for the words
        self.main_window.word_image_urls = {'hund': 'https://dictionary.langeek.co/assets/img/hund.jpg', 'kat': None}
        with patch('danish_audio_downloader.gui.app.QMessageBox.information') as mock_info:
            self.main_window.unified_processing_finished()
        mock_info.assert_called_once()
        self.assertEqual(self.main_window.app_state, "results_ready")
        self.assertEqual(self.main_window.action_button.text(), "Save as Anki CSV")
        self.assertEqual(self.main_window.sentence_results.toPlainText(), test_results)
        # Check that the image progress bar is at 0 or 100 (should not error)
        self.main_window.update_image_progress(1, 2)
        self.assertEqual(self.main_window.image_progress_bar.value(), 50)
        self.main_window.update_image_progress(2, 2)
        self.assertEqual(self.main_window.image_progress_bar.value(), 100)
    
    @patch('danish_audio_downloader.gui.app.QFileDialog.getSaveFileName')
    @patch('danish_audio_downloader.gui.app.QMessageBox.warning')
    def test_save_sentence_results_csv_no_content(self, mock_warning, mock_save_dialog):
        """Test saving sentence results as CSV when there's no content."""
        # Clear results
        self.main_window.sentence_results.clear()
        
        self.main_window.save_sentence_results_csv()
        
        # Should show warning and not open save dialog
        mock_warning.assert_called_once()
        mock_save_dialog.assert_not_called()

    @patch('danish_audio_downloader.gui.app.QFileDialog.getSaveFileName')
    def test_save_sentence_results_csv_success(self, mock_save_dialog):
        """Test successful saving of sentence results as CSV for Anki import."""
        # Set the button to results ready state first
        self.main_window.update_button_state("results_ready")
        
        # Set some properly formatted results with at least 3 sentences per word
        test_results = """**hund**

**Example Sentences:**
1. Min hund elsker at lege i parken. - My dog loves to play in the park.
2. Hunden løb hurtigt efter bolden. - The dog ran quickly after the ball.
3. Vi har en stor, venlig hund. - We have a big, friendly dog.

---

**kat**

**Example Sentences:**
1. Katten sover på sofaen. - The cat sleeps on the sofa.
2. Min kat fanger mus i kælderen. - My cat catches mice in the basement.
3. Den lille kat miaver højt. - The little cat meows loudly.

---"""
        self.main_window.sentence_results.setPlainText(test_results)
        
        # Mock file dialog
        test_file_path = "/tmp/test_results.csv"
        mock_save_dialog.return_value = (test_file_path, "")
        
        with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            with patch('danish_audio_downloader.gui.app.QMessageBox.information'):
                with patch('csv.writer') as mock_csv_writer:
                    mock_writer_instance = mock_csv_writer.return_value
                    
                    self.main_window.save_sentence_results_csv()
                    
                    # Check that file was opened correctly
                    mock_file.assert_called_once_with(test_file_path, 'w', newline='', encoding='utf-8')
                    
                    # Check that CSV writer was created
                    mock_csv_writer.assert_called_once()
                    
                    # Check that Anki header was written
                    expected_header = [
                        'Front (Eksempel med ord fjernet eller blankt)',
                        'Front (Billede)', 
                        'Front (Definition, grundform, osv.)',
                        'Back (et enkelt ord/udtryk, uden kontekst)',
                        '- Hele sætningen (intakt)',
                        '- Ekstra info (IPA, køn, bøjning)',
                        '• Lav 2 kort?'
                    ]
                    mock_writer_instance.writerow.assert_any_call(expected_header)
                    
                    # Should have written 6 data rows (3 cards for hund + 3 cards for kat)
                    self.assertEqual(mock_writer_instance.writerows.call_count, 1)
                    written_data = mock_writer_instance.writerows.call_args[0][0]
                    self.assertEqual(len(written_data), 6)
                    
                    # Check first card (Card Type 1 for 'hund')
                    self.assertIn('___', written_data[0][0])  # Should have blank
                    self.assertEqual(written_data[0][1], '<img src="myimage.jpg">')  # Image
                    self.assertTrue(isinstance(written_data[0][2], str) and written_data[0][2])  # Definition should not be empty
                    self.assertIn('hund', written_data[0][2])  # Definition should contain the word
                    self.assertEqual(written_data[0][3], 'hund')  # Back word
                    self.assertEqual(written_data[0][4], 'Min hund elsker at lege i parken.')  # Full sentence
                    self.assertIn('[sound:hund.mp3]', written_data[0][5])  # Audio file
                    self.assertEqual(written_data[0][6], 'y')  # Make 2 cards
                    
                    # Check second card (Card Type 2 for 'hund') 
                    self.assertNotIn('hund', written_data[1][0].lower())  # Word should be removed
                    self.assertEqual(written_data[1][1], '<img src="myimage.jpg">')  # Image
                    self.assertIn('hund', written_data[1][2])  # Should have definition
                    self.assertEqual(written_data[1][3], '')  # No back word for card 2
                    self.assertEqual(written_data[1][4], 'Min hund elsker at lege i parken.')  # Full sentence (should match Card 1)
                    self.assertIn('[sound:hund.mp3]', written_data[1][5])  # Audio file
                    self.assertEqual(written_data[1][6], '')  # No make 2 cards
                    
                    # Check third card (Card Type 3 for 'hund')
                    self.assertIn('___', written_data[2][0])  # Should have blank
                    self.assertEqual(written_data[2][1], '<img src="myimage.jpg">')  # Image
                    self.assertTrue(isinstance(written_data[2][2], str) and written_data[2][2])  # Definition should not be empty
                    self.assertIn('hund', written_data[2][2])  # Definition should contain the word
                    self.assertEqual(written_data[2][3], 'hund')  # Back word
                    self.assertEqual(written_data[2][4], 'Hunden løb hurtigt efter bolden.')  # Full sentence (should match Card 2)
                    self.assertIn('[sound:hund.mp3]', written_data[2][5])  # Audio file
                    self.assertEqual(written_data[2][6], '')  # No make 2 cards
                    
                    # Check that state transitions back to idle after successful save
                    self.assertEqual(self.main_window.app_state, "idle")

    def test_dynamic_button_states(self):
        """Test that the dynamic action button changes states correctly."""
        # Initial state should be idle
        self.assertEqual(self.main_window.app_state, "idle")
        self.assertEqual(self.main_window.action_button.text(), "Process Words (Audio + Sentences + Images)")
        
        # Test transition to processing state
        self.main_window.update_button_state("processing")
        self.assertEqual(self.main_window.app_state, "processing")
        self.assertEqual(self.main_window.action_button.text(), "Cancel Processing")
        
        # Test transition to results ready state
        self.main_window.update_button_state("results_ready")
        self.assertEqual(self.main_window.app_state, "results_ready")
        self.assertEqual(self.main_window.action_button.text(), "Save as Anki CSV")
        
        # Test transition back to idle
        self.main_window.update_button_state("idle")
        self.assertEqual(self.main_window.app_state, "idle")
        self.assertEqual(self.main_window.action_button.text(), "Process Words (Audio + Sentences + Images)")
    
    def test_action_button_handler(self):
        """Test that the action button handler calls the correct methods based on state."""
        # Test idle state calls start_processing
        self.main_window.update_button_state("idle")
        with patch.object(self.main_window, 'start_processing') as mock_start:
            self.main_window.handle_action_button()
            mock_start.assert_called_once()
        
        # Test processing state calls cancel_processing
        self.main_window.update_button_state("processing")
        with patch.object(self.main_window, 'cancel_processing') as mock_cancel:
            self.main_window.handle_action_button()
            mock_cancel.assert_called_once()
        
        # Test results_ready state calls save_sentence_results_csv
        self.main_window.update_button_state("results_ready")
        with patch.object(self.main_window, 'save_sentence_results_csv') as mock_save:
            self.main_window.handle_action_button()
            mock_save.assert_called_once()


if __name__ == '__main__':
    # Import here to avoid issues if PyQt5 is not available
    import unittest.mock
    
    # Create a test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestDanishAudioApp))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
