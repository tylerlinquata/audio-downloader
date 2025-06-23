"""
Danish Audio Downloader

A Python application for downloading Danish word pronunciations from ordnet.dk
and managing them for use with Anki flashcards.
"""

__version__ = "1.0.0"
__author__ = "Tyler Joseph Linquata"
__email__ = "your.email@example.com"

from .core.downloader import DanishAudioDownloader
from .core.worker import Worker
from .core.sentence_worker import SentenceWorker

__all__ = [
    "DanishAudioDownloader",
    "Worker", 
    "SentenceWorker"
]
