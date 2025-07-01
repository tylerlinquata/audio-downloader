"""
Worker thread for downloading audio files with concurrent processing.
"""

from typing import List
from PyQt5.QtCore import QThread, pyqtSignal
from .concurrent_downloader import ConcurrentAudioDownloader


class Worker(QThread):
    """Worker thread for downloading audio files."""
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(list, list)  # successful, failed

    def __init__(self, words: List[str], output_dir: str, copy_to_anki: bool, anki_folder: str) -> None:
        super().__init__()
        self.words = words
        self.output_dir = output_dir
        self.copy_to_anki = copy_to_anki
        self.anki_folder = anki_folder
        self.abort_flag = False

    def run(self) -> None:
        """Run the download process with concurrent processing."""
        downloader = ConcurrentAudioDownloader(
            output_dir=self.output_dir,
            anki_folder=self.anki_folder,
            signal_handler=self
        )
        successful, failed = downloader.download_audio_for_words(self.words)
        if not self.abort_flag:
            self.finished_signal.emit(successful, failed)

    def abort(self) -> None:
        """Abort the download process."""
        self.abort_flag = True
        self.update_signal.emit("Aborting download process...")
