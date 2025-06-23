#!/usr/bin/env python3
"""
Simple smoke test to verify the app can be imported and basic functionality works.
"""

import sys
import os
import tempfile
import shutil

# Add the parent directory to the path (project root)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_basic_imports():
    """Test that we can import the main classes."""
    print("Testing basic imports...")
    
    try:
        # Import from new modular structure
        from src.danish_audio_downloader.core.downloader import DanishAudioDownloader
        
        # Test that classes can be instantiated
        temp_dir = tempfile.mkdtemp()
        try:
            downloader = DanishAudioDownloader(output_dir=temp_dir)
            print("✓ DanishAudioDownloader can be instantiated")
            
            # Test basic functionality
            result = downloader._validate_audio_file("/nonexistent/file.mp3")
            assert result == False, "Validation should fail for non-existent file"
            print("✓ Audio file validation works")
            
        finally:
            shutil.rmtree(temp_dir)
        
        print("✓ All basic imports and instantiations successful")
        return True
        
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False


def test_gui_imports():
    """Test GUI imports (may fail in headless environment)."""
    print("Testing GUI imports...")
    
    try:
        from PyQt5.QtWidgets import QApplication
        
        # Only create QApplication if it doesn't exist
        if not QApplication.instance():
            app = QApplication([])
        
        # Import from new modular structure
        from src.danish_audio_downloader.gui.app import DanishAudioApp
        
        # Test GUI class
        main_window = DanishAudioApp()
        print("✓ DanishAudioApp can be instantiated")
        
        # Test basic properties
        assert main_window.windowTitle() == "Danish Word Audio Downloader"
        print("✓ Window title is correct")
        
        main_window.close()
        print("✓ GUI tests successful")
        return True
        
    except Exception as e:
        print(f"⚠ GUI test failed (this is normal in headless environments): {e}")
        return False


if __name__ == "__main__":
    print("Running smoke tests for Danish Audio Downloader...")
    print("=" * 50)
    
    success = True
    
    # Test basic functionality
    if not test_basic_imports():
        success = False
    
    print()
    
    # Test GUI (optional)
    test_gui_imports()  # Don't fail on GUI issues
    
    print()
    print("=" * 50)
    if success:
        print("✓ Smoke tests PASSED")
        sys.exit(0)
    else:
        print("✗ Smoke tests FAILED")
        sys.exit(1)
