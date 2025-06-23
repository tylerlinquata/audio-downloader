#!/usr/bin/env python3
"""
Simple smoke test to verify the app can be imported and basic functionality works.
"""

import sys
import os
import tempfile
import shutil

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_imports():
    """Test that we can import the main classes."""
    print("Testing basic imports...")
    
    try:
        # Dynamic import
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "danish_gui", 
            os.path.join(os.path.dirname(__file__), "Danish Word Audio Downloader GUI.py")
        )
        danish_gui = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(danish_gui)
        
        # Test that classes can be instantiated
        temp_dir = tempfile.mkdtemp()
        try:
            downloader = danish_gui.DanishAudioDownloader(output_dir=temp_dir)
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
        
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "danish_gui", 
            os.path.join(os.path.dirname(__file__), "Danish Word Audio Downloader GUI.py")
        )
        danish_gui = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(danish_gui)
        
        # Test GUI class
        main_window = danish_gui.DanishAudioApp()
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
