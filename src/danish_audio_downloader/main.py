"""
Main entry point for the Danish Audio Downloader package.
"""

import sys
from PyQt5.QtWidgets import QApplication
from .gui.app import DanishAudioApp


def main():
    """Main function to start the application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = DanishAudioApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
