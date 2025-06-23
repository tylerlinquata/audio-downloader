#!/usr/bin/env python3
"""
Simplified unit tests for Danish Audio Downloader application.
"""

import unittest
import os
import tempfile
import shutil
import sys
from unittest.mock import Mock, patch


def load_danish_gui():
    """Load the Danish GUI module."""
    import importlib.util
    
    spec = importlib.util.spec_from_file_location(
        "danish_gui", 
        "Danish Word Audio Downloader GUI.py"
    )
    danish_gui = importlib.util.module_from_spec(spec)
    sys.modules["danish_gui"] = danish_gui
    spec.loader.exec_module(danish_gui)
    return danish_gui


class TestBasicFunctionality(unittest.TestCase):
    """Basic functionality tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.danish_gui = load_danish_gui()
    
    def tearDown(self):
        """Clean up after tests."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_downloader_initialization(self):
        """Test that DanishAudioDownloader can be initialized."""
        downloader = self.danish_gui.DanishAudioDownloader(output_dir=self.temp_dir)
        self.assertIsNotNone(downloader)
        self.assertEqual(downloader.output_dir, self.temp_dir)
        self.assertTrue(os.path.exists(self.temp_dir))
    
    def test_worker_initialization(self):
        """Test that Worker can be initialized."""
        worker = self.danish_gui.Worker(["test"], self.temp_dir, False, "")
        self.assertIsNotNone(worker)
        self.assertEqual(worker.words, ["test"])
        self.assertFalse(worker.abort_flag)
    
    def test_sentence_worker_initialization(self):
        """Test that SentenceWorker can be initialized."""
        worker = self.danish_gui.SentenceWorker(["test"], "B1", "api_key")
        self.assertIsNotNone(worker)
        self.assertEqual(worker.words, ["test"])
        self.assertEqual(worker.cefr_level, "B1")
        self.assertFalse(worker.abort_flag)
    
    def test_audio_file_validation_nonexistent(self):
        """Test audio file validation for non-existent file."""
        downloader = self.danish_gui.DanishAudioDownloader(output_dir=self.temp_dir)
        result = downloader._validate_audio_file("/nonexistent/file.mp3")
        self.assertFalse(result)
    
    def test_audio_file_validation_too_small(self):
        """Test audio file validation for file that's too small."""
        downloader = self.danish_gui.DanishAudioDownloader(output_dir=self.temp_dir)
        
        small_file = os.path.join(self.temp_dir, "small.mp3")
        with open(small_file, 'wb') as f:
            f.write(b"tiny")  # Less than 1KB
        
        result = downloader._validate_audio_file(small_file)
        self.assertFalse(result)
    
    def test_audio_file_validation_valid_mp3(self):
        """Test audio file validation for valid MP3."""
        downloader = self.danish_gui.DanishAudioDownloader(output_dir=self.temp_dir)
        
        valid_file = os.path.join(self.temp_dir, "valid.mp3")
        with open(valid_file, 'wb') as f:
            f.write(b'ID3' + b'\x00' * 1021)  # ID3 header + padding
        
        result = downloader._validate_audio_file(valid_file)
        self.assertTrue(result)
    
    def test_log_functionality(self):
        """Test logging functionality."""
        downloader = self.danish_gui.DanishAudioDownloader(output_dir=self.temp_dir)
        
        # Test without signal handler (should print)
        with patch('builtins.print') as mock_print:
            downloader.log("test message")
            mock_print.assert_called_once_with("test message")
        
        # Test with signal handler
        mock_signal = Mock()
        downloader.signal = mock_signal
        downloader.log("test signal message")
        mock_signal.update_signal.emit.assert_called_once_with("test signal message")
    
    def test_session_configuration(self):
        """Test that HTTP session is configured correctly."""
        downloader = self.danish_gui.DanishAudioDownloader(output_dir=self.temp_dir)
        
        headers = downloader.session.headers
        self.assertIn('User-Agent', headers)
        self.assertIn('Mozilla', headers['User-Agent'])
        self.assertIn('Chrome', headers['User-Agent'])
    
    def test_worker_abort_functionality(self):
        """Test worker abort functionality."""
        worker = self.danish_gui.Worker(["test"], self.temp_dir, False, "")
        
        self.assertFalse(worker.abort_flag)
        worker.abort()
        self.assertTrue(worker.abort_flag)
    
    def test_sentence_worker_abort_functionality(self):
        """Test sentence worker abort functionality."""
        worker = self.danish_gui.SentenceWorker(["test"], "B1", "api_key")
        
        self.assertFalse(worker.abort_flag)
        worker.abort()
        self.assertTrue(worker.abort_flag)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
