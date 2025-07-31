"""Main application window for Danish Audio Downloader."""

import os
import gc  # For garbage collection monitoring
from PyQt5.QtWidgets import QMainWindow, QTabWidget, QMessageBox
from PyQt5.QtCore import pyqtSignal

from ..core.worker import Worker
from ..core.sentence_worker import SentenceWorker
from ..core.image_worker import ImageWorker
from .widgets.main_tab import MainTab
from .widgets.settings_tab import SettingsTab
from .widgets.review_tab import ReviewTab
from .logic.settings_manager import SettingsManager
from .logic.card_processor import CardProcessor


class DanishAudioApp(QMainWindow):
    """Main application window for Danish Audio Downloader."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize managers and processors
        self.settings_manager = SettingsManager()
        self.card_processor = CardProcessor()
        
        # Initialize worker threads
        self.worker = None
        self.sentence_worker = None
        self.image_worker = None
        
        # Initialize processing state
        self.pending_sentence_generation = {}
        self.final_sentence_results = ""
        self.structured_word_data = []  # Store structured data from sentence worker
        self.ordnet_dictionary_data = {}  # Store dictionary data from Ordnet
        
        # Set up the UI
        self.init_ui()
        
        # Load settings
        self.load_settings()
        
        # Set initial button state
        self.main_tab.update_button_state("idle")
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Danish Word Learning Assistant")
        self.setMinimumSize(900, 700)
        
        # Create tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Create tab widgets
        self.main_tab = MainTab()
        self.settings_tab = SettingsTab()
        self.review_tab = ReviewTab()
        
        # Add tabs
        self.tabs.addTab(self.main_tab, "Process Words")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.addTab(self.review_tab, "Review Cards")
        
        # Connect signals
        self._connect_signals()
        
        # Initially disable the review tab
        self.tabs.setTabEnabled(2, False)  # Review tab is index 2
    
    def _connect_signals(self):
        """Connect all widget signals to their handlers."""
        # Main tab signals
        self.main_tab.process_words_requested.connect(self._handle_process_words)
        self.main_tab.cancel_processing_requested.connect(self._cancel_processing)
        self.main_tab.save_csv_requested.connect(self._save_sentence_results_csv)
        
        # Settings tab signals
        self.settings_tab.settings_saved.connect(self._save_settings)
        
        # Review tab signals
        self.review_tab.export_cards_requested.connect(self._handle_export_cards)
        self.review_tab.back_to_processing_requested.connect(self._back_to_processing)
    
    def _handle_process_words(self, words):
        """Handle request to process words."""
        if not words:
            QMessageBox.warning(self, "No Words", "Please enter words to process.")
            return
        
        # Get API keys and settings
        settings = self.settings_tab.get_settings()
        
        # Check for OpenAI API key for sentence generation
        openai_api_key = settings.get('openai_api_key', '').strip()
        if not openai_api_key:
            QMessageBox.warning(self, "No OpenAI API Key", "Please enter your OpenAI API key in the Settings tab.")
            return
        
        # Check for Forvo API key for audio downloads
        forvo_api_key = settings.get('forvo_api_key', '').strip()
        if not forvo_api_key:
            QMessageBox.warning(self, "No Forvo API Key", "Please enter your Forvo API key in the Settings tab.")
            return
        
        # Get output directory settings
        output_dir = settings.get('output_dir', '')
        anki_folder = settings.get('anki_dir', '')
        
        # Expand user directory paths
        if output_dir:
            output_dir = os.path.expanduser(output_dir)
        if anki_folder:
            anki_folder = os.path.expanduser(anki_folder)
        
        # Create directory if it doesn't exist
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                self.main_tab.log_message(f"Created output directory: {output_dir}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create output directory: {str(e)}")
                return
        
        # Update UI for processing state
        self.main_tab.update_button_state("processing")
        self.main_tab.reset_progress()
        
        self.main_tab.log_message("Starting unified processing...")
        self.main_tab.log_message(f"Processing {len(words)} words:")
        
        # Warn about large batches
        if len(words) > 50:
            self.main_tab.log_message("⚠️  WARNING: Large batch detected! Processing more than 50 words may take significant time.")
            self.main_tab.log_message("    Images will be loaded gradually to prevent system overload.")
        elif len(words) > 25:
            self.main_tab.log_message("⚠️  Note: Processing more than 25 words may take several minutes.")
            self.main_tab.log_message("    Images will be loaded in batches for optimal performance.")
        
        for word in words:
            self.main_tab.log_message(f"  - {word}")
        
        # Start with audio download first
        self._start_audio_download(words, output_dir, anki_folder, openai_api_key, forvo_api_key, settings.get('cefr_level', 'B1'))
    
    def _start_audio_download(self, words, output_dir, anki_folder, openai_api_key, forvo_api_key, cefr_level):
        """Start the audio download phase."""
        self.main_tab.log_message("\n=== Phase 1: Downloading Audio Files from Forvo ===")
        
        # Store the sentence generation parameters for later
        self.pending_sentence_generation = {
            'words': words,
            'api_key': openai_api_key,
            'cefr_level': cefr_level
        }
        
        # Create and start the audio worker thread with Forvo API key
        self.worker = Worker(words, output_dir, False, anki_folder, forvo_api_key)
        self.worker.update_signal.connect(self.main_tab.log_message)
        self.worker.progress_signal.connect(self.main_tab.update_audio_progress)
        self.worker.finished_signal.connect(self._audio_download_finished)
        self.worker.start()
    
    def _audio_download_finished(self, successful, failed, dictionary_data):
        """Handle completion of audio download and start sentence generation."""
        self.main_tab.log_message("\n=== Audio Download Complete ===")
        self.main_tab.log_message(f"Successfully downloaded: {len(successful)} audio files from Forvo")
        if failed:
            self.main_tab.log_message(f"Failed to download: {len(failed)} audio files")
            for word in failed:
                self.main_tab.log_message(f"  - {word}")
        
        # Store dictionary data for later use (from Ordnet dictionary lookups)
        self.ordnet_dictionary_data = dictionary_data
        
        # Log dictionary data collection
        definitions_found = sum(1 for data in dictionary_data.values() if data.get('ordnet_found'))
        self.main_tab.log_message(f"Collected dictionary data for {definitions_found} words from Ordnet")
        
        # Start sentence generation phase
        self._start_sentence_generation_phase()
    
    def _start_sentence_generation_phase(self):
        """Start the sentence generation phase."""
        self.main_tab.log_message("\n=== Phase 2: Generating Example Sentences ===")
        
        params = self.pending_sentence_generation
        
        # Create and start the sentence worker thread
        self.sentence_worker = SentenceWorker(
            params['words'], 
            params['cefr_level'], 
            params['api_key'],
            self.ordnet_dictionary_data  # Pass dictionary data
        )
        self.sentence_worker.update_signal.connect(self.main_tab.log_message)
        self.sentence_worker.progress_signal.connect(self.main_tab.update_sentence_progress)
        self.sentence_worker.finished_signal.connect(self._sentence_generation_finished)
        self.sentence_worker.error_signal.connect(self._sentence_generation_error)
        self.sentence_worker.start()
    
    def _sentence_generation_finished(self, word_data_list, word_translations):
        """Handle completion of sentence generation and start image fetching."""
        try:
            self.main_tab.log_message(f"Received data for {len(word_data_list)} words from sentence worker")
            self._log_memory_usage("after receiving sentence data")
            
            # Store the structured data
            self.structured_word_data = word_data_list
            
            # Format for display in the results area
            formatted_results = self._format_word_data_for_display(word_data_list)
            self.main_tab.set_results(formatted_results)
            self.main_tab.log_message("\n=== Sentence Generation Complete ===")
            self.main_tab.log_message(f"Generated sentences for {len(word_translations)} words")
            
            # Store the formatted sentence results for backward compatibility
            self.final_sentence_results = formatted_results
            
            self._log_memory_usage("after formatting sentence data")
            
            # Start image fetching phase
            self._start_image_fetching_phase(word_translations)
            
        except Exception as e:
            error_msg = f"Error processing sentence generation results: {str(e)}"
            self.main_tab.log_message(f"ERROR: {error_msg}")
            QMessageBox.critical(self, "Processing Error", error_msg)
            self.main_tab.update_button_state("idle")
    
    def _start_image_fetching_phase(self, word_translations):
        """Start the image fetching phase."""
        self.main_tab.log_message("\n=== Phase 3: Fetching Images ===")
        
        # Create and start the image worker thread
        api_key = self.pending_sentence_generation['api_key']
        self.image_worker = ImageWorker(word_translations, api_key)
        self.image_worker.update_signal.connect(self.main_tab.log_message)
        self.image_worker.progress_signal.connect(self.main_tab.update_image_progress)
        self.image_worker.finished_signal.connect(self._image_fetching_finished)
        self.image_worker.error_signal.connect(self._image_fetching_error)
        self.image_worker.start()
    
    def _image_fetching_finished(self, image_urls):
        """Handle completion of image fetching and finish unified processing."""
        self.main_tab.log_message("\n=== Image Fetching Complete ===")
        successful_images = len([url for url in image_urls.values() if url])
        self.main_tab.log_message(f"Found images for {successful_images} out of {len(image_urls)} words")
        
        # Store image URLs for CSV export
        self.card_processor.set_image_urls(image_urls)
        
        # Complete the unified processing
        self._unified_processing_finished()
    def _format_word_data_for_display(self, word_data_list):
        """Format structured word data for display in the results area."""
        formatted_blocks = []
        
        for word_data in word_data_list:
            if word_data.get('error'):
                # Handle error cases
                word = word_data.get('word', 'Unknown')
                formatted_blocks.append(f"**{word}**\n\nError: {word_data['error']}\n\n---")
            else:
                # Use the existing formatting method from sentence_worker
                from ..core.sentence_worker import SentenceWorker
                worker = SentenceWorker([], "", "")  # Temporary instance for formatting
                formatted_content = worker._format_word_data(word_data)
                formatted_blocks.append(formatted_content)
        
        return "\n\n".join(formatted_blocks)
    
    def _image_fetching_error(self, error_msg):
        """Handle errors in image fetching."""
        self.main_tab.log_message(f"Image fetching error: {error_msg}")
        # Continue without images - set empty image URLs
        self.card_processor.set_image_urls({})
        self._unified_processing_finished()
    
    def _unified_processing_finished(self):
        """Handle completion of the entire unified processing."""
        if self.final_sentence_results:
            # Ensure sentence results are displayed
            self.main_tab.set_results(self.final_sentence_results)
        
        self.main_tab.log_message("\n=== Processing Complete! ===")
        self.main_tab.log_message("Audio files, example sentences, and images have been processed.")
        self.main_tab.log_message("Generating cards for review...")
        
        # Generate cards for review
        try:
            # Use structured data (no fallback - structured data should always be available)
            if self.structured_word_data:
                cards_data = self.card_processor.generate_cards_from_structured_data(self.structured_word_data)
            else:
                # This should not happen in normal operation since we always generate structured data
                self.main_tab.log_message("Error: No structured data available for card generation.")
                QMessageBox.warning(self, "Error", "No structured data available for card generation. Please re-run the sentence generation.")
                return
            if cards_data:
                self.main_tab.log_message(f"Generated {len(cards_data)} cards for review.")
                
                self._log_memory_usage("after card generation")
                
                # Show completion message and redirect to review
                word_count = len(self.pending_sentence_generation['words'])
                image_urls = self.card_processor.word_image_urls
                image_count = len([url for url in image_urls.values() if url]) if image_urls else 0
                
                QMessageBox.information(
                    self, 
                    "Processing Complete!", 
                    f"Successfully processed {word_count} words!\n\n" +
                    "✓ Audio files downloaded\n" +
                    "✓ Example sentences generated\n" +
                    f"✓ Images found for {image_count} words\n" +
                    f"✓ Generated {len(cards_data)} flashcards\n\n" +
                    "Click OK to review and edit your cards."
                )
                
                # Populate the review table and switch to review tab
                self._log_memory_usage("before populating review tab")
                
                try:
                    self.review_tab.populate_cards(cards_data)
                    
                    # Enable the review tab and switch to it
                    self.tabs.setTabEnabled(2, True)
                    self.tabs.setCurrentIndex(2)
                    
                    # Update button state to idle since we're now in review mode
                    self.main_tab.update_button_state("idle")
                    
                    self._log_memory_usage("after populating review tab")
                    
                except Exception as e:
                    error_msg = f"Error populating review tab: {str(e)}"
                    self.main_tab.log_message(f"ERROR: {error_msg}")
                    QMessageBox.critical(self, "Review Tab Error", error_msg)
                    self.main_tab.update_button_state("results_ready")
                    return
                
            else:
                self.main_tab.log_message("No cards were generated. Check the sentence results format.")
                QMessageBox.warning(self, "No Cards Generated", "No cards could be generated from the results. Please check the output format.")
                self.main_tab.update_button_state("results_ready")  # Fall back to old workflow
                
        except Exception as e:
            self.main_tab.log_message(f"Error generating cards for review: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error generating cards for review: {str(e)}")
            self.main_tab.update_button_state("results_ready")  # Fall back to old workflow
    
    def _cancel_processing(self):
        """Cancel the unified processing."""
        # Cancel audio worker if running
        if self.worker and self.worker.isRunning():
            self.worker.abort()
            self.worker.wait()
            self.main_tab.log_message("Audio download cancelled.")
        
        # Cancel sentence worker if running
        if self.sentence_worker and self.sentence_worker.isRunning():
            self.sentence_worker.abort()
            self.sentence_worker.wait()
            self.main_tab.log_message("Sentence generation cancelled.")
        
        # Cancel image worker if running
        if self.image_worker and self.image_worker.isRunning():
            self.image_worker.abort()
            self.image_worker.wait()
            self.main_tab.log_message("Image fetching cancelled.")
        
        self.main_tab.log_message("Processing cancelled.")
        
        # Update UI
        self.main_tab.update_button_state("idle")
    
    def _sentence_generation_error(self, error_msg):
        """Handle errors in sentence generation."""
        self.main_tab.log_message(f"Error in sentence generation: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)
        
        # Update UI
        self.main_tab.update_button_state("idle")
    
    def _save_sentence_results_csv(self):
        """Save the generated sentences to a CSV file."""
        # Check if we have structured data
        if not self.structured_word_data:
            QMessageBox.warning(self, "No Results", "No sentences to save.")
            return
        
        from PyQt5.QtWidgets import QFileDialog
        
        # Set default directory to Downloads folder on macOS
        default_dir = os.path.expanduser("~/Downloads")
        default_filename = os.path.join(default_dir, "danish_example_sentences.csv")
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Sentence Results as CSV", default_filename, 
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                self._log_memory_usage("before CSV export")
                
                self.main_tab.log_message(f"\n=== Exporting to CSV ===")
                self.main_tab.log_message(f"Preparing to save results to: {file_path}")
                self.main_tab.log_message(f"Structured data contains {len(self.structured_word_data)} entries")
                
                settings = self.settings_tab.get_settings()
                # Use the new method that works with structured data, pass log callback
                csv_data = self.card_processor.export_structured_data_to_csv(
                    self.structured_word_data, 
                    file_path,
                    log_callback=self.main_tab.log_message
                )
                
                self._log_memory_usage("after CSV generation")
                
                self.main_tab.log_message(f"\n=== Copying Audio Files ===")
                # Copy audio files to Anki
                copy_result = self.card_processor.copy_audio_files_to_anki(
                    csv_data, 
                    settings.get('output_dir', ''), 
                    settings.get('anki_dir', '')
                )
                
                if copy_result.get('success'):
                    QMessageBox.information(
                        self, "Saved", 
                        f"Results saved to {file_path}\n\n" +
                        "Audio files have been copied to your Anki media folder."
                    )
                else:
                    QMessageBox.information(
                        self, "Saved", 
                        f"Results saved to {file_path}\n\n" +
                        f"Warning: {copy_result.get('message', 'Could not copy audio files')}"
                    )
                
                self.main_tab.log_message(f"Anki CSV export saved to {file_path}")
                # Transition button back to processing mode to allow new processing
                self.main_tab.update_button_state("idle")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error saving CSV file: {str(e)}")
    
    def _handle_export_cards(self, selected_cards):
        """Handle export of selected cards from review tab."""
        settings = self.settings_tab.get_settings()
        
        # Copy audio files to Anki
        copy_result = self.card_processor.copy_audio_files_to_anki(
            selected_cards,
            settings.get('output_dir', ''),
            settings.get('anki_dir', '')
        )
        
        if copy_result.get('success'):
            copied_count = copy_result.get('copied_count', 0)
            failed_copies = copy_result.get('failed_copies', [])
            
            message = f"Successfully exported {len(selected_cards)} cards!\n\n"
            message += f"Audio files copied: {copied_count}"
            if failed_copies:
                message += f"\nFailed to copy: {len(failed_copies)} files"
            
            QMessageBox.information(self, "Export Complete", message)
            
            # Log the results
            self.main_tab.log_message(f"✓ Exported {len(selected_cards)} cards")
            self.main_tab.log_message(f"✓ Copied {copied_count} audio files to Anki")
            if failed_copies:
                self.main_tab.log_message(f"✗ Failed to copy {len(failed_copies)} audio files")
        else:
            QMessageBox.warning(
                self, "Export Warning", 
                f"Cards exported but audio files could not be copied:\n{copy_result.get('message', 'Unknown error')}"
            )
        
        # Reset for new processing
        self._reset_for_new_processing()
    
    def _back_to_processing(self):
        """Go back to the processing tab."""
        self.tabs.setCurrentIndex(0)
    
    def _reset_for_new_processing(self):
        """Reset the app for new processing."""
        # Clean up review tab resources
        if hasattr(self.review_tab, 'cleanup'):
            self.review_tab.cleanup()
        
        # Clear data
        self.card_processor.set_image_urls({})
        self.final_sentence_results = ""
        self.pending_sentence_generation = {}
        self.structured_word_data = []
        self.ordnet_dictionary_data = {}
        
        # Force garbage collection to clean up resources
        import gc
        collected = gc.collect()
        self.main_tab.log_message(f"Cleaned up resources (freed {collected} objects)")
        
        # Disable review tab and go back to processing
        self.tabs.setTabEnabled(2, False)
        self.tabs.setCurrentIndex(0)
        
        # Reset UI state
        self.main_tab.update_button_state("idle")
        self.main_tab.reset_progress()
    
    def _save_settings(self):
        """Save settings to persistent storage."""
        settings = self.settings_tab.get_settings()
        self.settings_manager.save_settings(settings)
        QMessageBox.information(self, "Settings Saved", "Settings have been saved.")
    
    def load_settings(self):
        """Load settings from persistent storage."""
        settings = self.settings_manager.load_settings()
        self.settings_tab.load_settings(settings)
    
    def _log_memory_usage(self, context=""):
        """Log current memory usage and object counts for debugging."""
        try:
            # Force garbage collection
            collected = gc.collect()
            
            # Get object counts by type
            import sys
            object_counts = {}
            for obj in gc.get_objects():
                obj_type = type(obj).__name__
                object_counts[obj_type] = object_counts.get(obj_type, 0) + 1
            
            # Log top object types
            top_objects = sorted(object_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            log_msg = f"Memory usage {context}:"
            if collected > 0:
                log_msg += f" (freed {collected} objects)"
            
            self.main_tab.log_message(log_msg)
            self.main_tab.log_message(f"  Total objects in memory: {len(gc.get_objects())}")
            self.main_tab.log_message("  Top object types:")
            for obj_type, count in top_objects:
                self.main_tab.log_message(f"    {obj_type}: {count}")
                
        except Exception as e:
            self.main_tab.log_message(f"Failed to get memory info: {str(e)}")

    def closeEvent(self, event):
        """Handle application close event to properly clean up resources."""
        try:
            # Cancel any running workers
            self._cancel_processing()
            
            # Clean up review tab resources
            if hasattr(self, 'review_tab') and hasattr(self.review_tab, 'cleanup'):
                self.review_tab.cleanup()
            
            # Force garbage collection
            import gc
            collected = gc.collect()
            print(f"Application closing: freed {collected} objects")
            
        except Exception as e:
            print(f"Error during application cleanup: {e}")
        
        super().closeEvent(event)

def main():
    """Main entry point for the GUI application."""
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = DanishAudioApp()
    window.show()
    sys.exit(app.exec_())
