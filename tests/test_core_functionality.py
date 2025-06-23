#!/usr/bin/env python3
"""
Unit tests for Danish Audio Downloader application - Working version.
"""

import unittest
import os
import tempfile
import shutil
import json
import sys
from unittest.mock import Mock, patch, MagicMock, mock_open

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from danish_audio_downloader.core.downloader import DanishAudioDownloader
from danish_audio_downloader.core.worker import Worker
from danish_audio_downloader.core.sentence_worker import SentenceWorker


class TestDanishAudioDownloader(unittest.TestCase):
    """Test cases for the DanishAudioDownloader class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.downloader = DanishAudioDownloader(
            output_dir=self.temp_dir,
            anki_folder="",
            signal_handler=None
        )
    
    def tearDown(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init_creates_output_directory(self):
        """Test that initializing the downloader creates the output directory."""
        new_temp_dir = os.path.join(self.temp_dir, "new_output_dir")
        self.assertFalse(os.path.exists(new_temp_dir))
        
        downloader = DanishAudioDownloader(output_dir=new_temp_dir)
        self.assertTrue(os.path.exists(new_temp_dir))
    
    def test_log_with_signal_handler(self):
        """Test logging with a signal handler."""
        mock_signal = Mock()
        downloader = DanishAudioDownloader(
            output_dir=self.temp_dir,
            signal_handler=mock_signal
        )
        
        test_message = "Test log message"
        downloader.log(test_message)
        
        mock_signal.update_signal.emit.assert_called_once_with(test_message)
    
    def test_log_without_signal_handler(self):
        """Test logging without a signal handler (should print)."""
        with patch('builtins.print') as mock_print:
            test_message = "Test log message"
            self.downloader.log(test_message)
            mock_print.assert_called_once_with(test_message)
    
    def test_validate_audio_file_nonexistent(self):
        """Test validation of non-existent file."""
        non_existent_file = os.path.join(self.temp_dir, "nonexistent.mp3")
        result = self.downloader._validate_audio_file(non_existent_file)
        self.assertFalse(result)
    
    def test_validate_audio_file_too_small(self):
        """Test validation of file that's too small."""
        small_file = os.path.join(self.temp_dir, "small.mp3")
        with open(small_file, 'wb') as f:
            f.write(b"tiny")  # Less than 1KB
        
        result = self.downloader._validate_audio_file(small_file)
        self.assertFalse(result)
    
    def test_validate_audio_file_valid_mp3(self):
        """Test validation of a valid MP3 file."""
        valid_file = os.path.join(self.temp_dir, "valid.mp3")
        # Create a file with MP3-like header and sufficient size
        with open(valid_file, 'wb') as f:
            f.write(b'ID3' + b'\x00' * 1021)  # ID3 header + padding to make it >1KB
        
        result = self.downloader._validate_audio_file(valid_file)
        self.assertTrue(result)
    
    def test_validate_audio_file_valid_mpeg(self):
        """Test validation of a valid MPEG file."""
        valid_file = os.path.join(self.temp_dir, "valid_mpeg.mp3")
        # Create a file with MPEG frame header and sufficient size
        with open(valid_file, 'wb') as f:
            f.write(b'\xff\xfb' + b'\x00' * 1022)  # MPEG header + padding
        
        result = self.downloader._validate_audio_file(valid_file)
        self.assertTrue(result)
    
    def test_move_to_anki_media_no_folder(self):
        """Test moving to Anki media when no folder is specified."""
        source_file = os.path.join(self.temp_dir, "test.mp3")
        with open(source_file, 'wb') as f:
            f.write(b'test content')
        
        # Test with empty anki_folder
        downloader = DanishAudioDownloader(
            output_dir=self.temp_dir,
            anki_folder=""
        )
        
        with patch('os.path.exists', return_value=False):
            result = downloader._move_to_anki_media(source_file, "test")
            self.assertFalse(result)
    
    def test_move_to_anki_media_success(self):
        """Test successful move to Anki media folder."""
        # Create a temporary Anki folder
        anki_folder = os.path.join(self.temp_dir, "anki_media")
        os.makedirs(anki_folder)
        
        source_file = os.path.join(self.temp_dir, "test.mp3")
        with open(source_file, 'wb') as f:
            f.write(b'test content')
        
        downloader = DanishAudioDownloader(
            output_dir=self.temp_dir,
            anki_folder=anki_folder
        )
        
        result = downloader._move_to_anki_media(source_file, "test")
        self.assertTrue(result)
        
        # Check that file was copied
        dest_file = os.path.join(anki_folder, "test.mp3")
        self.assertTrue(os.path.exists(dest_file))
    
    def test_session_headers_configuration(self):
        """Test that the session headers are configured correctly."""
        downloader = DanishAudioDownloader(output_dir=self.temp_dir)
        
        headers = downloader.session.headers
        self.assertIn('User-Agent', headers)
        self.assertIn('Accept-Language', headers)
        self.assertIn('Accept', headers)
        
        # Check that User-Agent contains expected browser info
        self.assertIn('Mozilla', headers['User-Agent'])
        self.assertIn('Chrome', headers['User-Agent'])


class TestWorkerThread(unittest.TestCase):
    """Test cases for the Worker thread class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up after tests."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_worker_initialization(self):
        """Test Worker thread initialization."""
        words = ["test1", "test2"]
        worker = Worker(words, self.temp_dir, False, "")
        
        self.assertEqual(worker.words, words)
        self.assertEqual(worker.output_dir, self.temp_dir)
        self.assertFalse(worker.copy_to_anki)
        self.assertEqual(worker.anki_folder, "")
        self.assertFalse(worker.abort_flag)
    
    def test_worker_abort(self):
        """Test Worker thread abort functionality."""
        worker = Worker(["test"], self.temp_dir, False, "")
        
        # Initially abort_flag should be False
        self.assertFalse(worker.abort_flag)
        
        # Call abort method
        worker.abort()
        
        # Now abort_flag should be True
        self.assertTrue(worker.abort_flag)


class TestSentenceWorker(unittest.TestCase):
    """Test cases for the SentenceWorker thread class."""
    
    def test_sentence_worker_initialization(self):
        """Test SentenceWorker thread initialization."""
        words = ["hund", "kat"]
        cefr_level = "B1"
        api_key = "test_key"
        
        worker = SentenceWorker(words, cefr_level, api_key)
        
        self.assertEqual(worker.words, words)
        self.assertEqual(worker.cefr_level, cefr_level)
        self.assertEqual(worker.api_key, api_key)
        self.assertFalse(worker.abort_flag)
    
    def test_sentence_worker_abort(self):
        """Test SentenceWorker thread abort functionality."""
        worker = SentenceWorker(["test"], "B1", "test_key")
        
        # Initially abort_flag should be False
        self.assertFalse(worker.abort_flag)
        
        # Call abort method
        worker.abort()
        
        # Now abort_flag should be True
        self.assertTrue(worker.abort_flag)


if __name__ == '__main__':
    # Create a test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestDanishAudioDownloader))
    test_suite.addTest(unittest.makeSuite(TestWorkerThread))
    test_suite.addTest(unittest.makeSuite(TestSentenceWorker))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
