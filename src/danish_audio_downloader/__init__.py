"""
Danish Audio Downloader

A Python application for downloading Danish word pronunciations from Forvo API
and managing them for use with Anki flashcards. Also fetches dictionary data from Ordnet.
"""

__version__ = "1.0.0"
__author__ = "Tyler Joseph Linquata"
__email__ = "your.email@example.com"

from .core.downloader import DanishAudioDownloader
from .core.worker import Worker
from .core.sentence_worker import SentenceWorker
from .core.image_worker import ImageWorker
from .core.audio_provider import ForvoAudioProvider
from .core.forvo_api import ForvoAPIClient

__all__ = [
    "DanishAudioDownloader",
    "Worker", 
    "SentenceWorker",
    "ImageWorker",
    "ForvoAudioProvider",
    "ForvoAPIClient"
]
