"""Business logic for card generation and CSV export."""

import re
import os
import shutil
import csv


class CardProcessor:
    """Handles card generation and CSV processing logic."""
    
    def __init__(self):
        self.word_image_urls = {}
        self.generate_second_sentence = True  # Default to enabled for backwards compatibility
    
    def set_generate_second_sentence(self, generate_second_sentence):
        """Set whether to generate second sentence cards."""
        self.generate_second_sentence = generate_second_sentence
    
    def set_image_urls(self, image_urls):
        """Set the image URLs dictionary."""
        self.word_image_urls = image_urls
    
    def copy_audio_files_to_anki(self, selected_cards, output_dir, anki_folder):
        """Copy audio files for selected cards to Anki media folder."""
        if not anki_folder or not os.path.exists(anki_folder):
            return {"success": False, "message": "Anki media folder not found or not accessible"}
        
        # Expand user paths to handle ~ notation
        output_dir = os.path.expanduser(output_dir) if output_dir else ""
        anki_folder = os.path.expanduser(anki_folder) if anki_folder else ""
        
        if not output_dir or not os.path.exists(output_dir):
            return {"success": False, "message": "Output directory not found"}
        
        # Extract unique words from selected cards that have audio references
        words_to_copy = set()
        for card in selected_cards:
            # Check the grammar info column (index 5) for audio references
            if len(card) > 5 and '[sound:' in card[5]:
                # Extract word from audio reference like "[sound:word.mp3]"
                audio_match = re.search(r'\[sound:([^.]+)\.mp3\]', card[5])
                if audio_match:
                    words_to_copy.add(audio_match.group(1))
        
        copied_count = 0
        failed_copies = []
        
        for word in words_to_copy:
            source_file = os.path.join(output_dir, f"{word}.mp3")
            dest_file = os.path.join(anki_folder, f"{word}.mp3")
            
            if os.path.exists(source_file):
                try:
                    shutil.copy2(source_file, dest_file)
                    copied_count += 1
                except PermissionError:
                    failed_copies.append(f"{word} (permission denied)")
                except Exception as e:
                    failed_copies.append(f"{word} ({str(e)})")
            else:
                failed_copies.append(f"{word} (source file not found)")
        
        return {
            "success": True,
            "copied_count": copied_count,
            "failed_copies": failed_copies,
            "total_words": len(words_to_copy)
        }
    
    def export_structured_data_to_csv(self, word_data_list, file_path, log_callback=None):
        """Export structured word data to CSV format for Anki import with specific card types."""
        if log_callback:
            log_callback(f"Starting CSV export to: {file_path}")
            log_callback(f"Processing {len(word_data_list)} word entries...")
        
        csv_data = []
        processed_words = 0
        skipped_words = 0
        
        for i, word_data in enumerate(word_data_list):
            word = word_data.get('word', 'Unknown')
            original_word = word_data.get('original_word', word)  # Get original user input word
            
            # Skip error entries
            if word_data.get('error'):
                skipped_words += 1
                if log_callback:
                    log_callback(f"  Skipping '{original_word}' - has error: {word_data.get('error')}")
                continue
                
            if not word or word == 'Unknown':
                skipped_words += 1
                if log_callback:
                    log_callback(f"  Skipping entry {i+1} - no word specified")
                continue
            
            # Extract sentences from structured data
            example_sentences = word_data.get('example_sentences', [])
            sentences = []
            for sentence_data in example_sentences:
                if isinstance(sentence_data, dict) and sentence_data.get('danish'):
                    sentences.append(sentence_data['danish'])
            
            required_sentences = 2 if self.generate_second_sentence else 1
            if len(sentences) >= required_sentences:  # Need required number of sentences
                # Generate the card types for this word with available sentences
                cards = self._generate_anki_cards_from_structured_data(word, sentences, word_data)
                
                csv_data.extend(cards)
                processed_words += 1
                if log_callback:
                    log_callback(f"  Generated {len(cards)} cards for '{original_word}' (using {len(sentences)} sentences)")
            else:
                skipped_words += 1
                if log_callback:
                    log_callback(f"  Skipping '{original_word}' - insufficient sentences ({len(sentences)} found, need at least {required_sentences})")
        
        if log_callback:
            log_callback(f"CSV generation summary:")
            log_callback(f"  - Processed words: {processed_words}")
            log_callback(f"  - Skipped words: {skipped_words}")
            log_callback(f"  - Total cards generated: {len(csv_data)}")
            log_callback(f"Writing CSV data to file...")
        
        try:
            # Write to CSV file
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                # Don't write header for Anki import - Anki doesn't expect headers
                writer.writerows(csv_data)
            
            if log_callback:
                log_callback(f"Successfully wrote {len(csv_data)} rows to CSV file")
        
        except Exception as e:
            error_msg = f"Failed to write CSV file: {str(e)}"
            if log_callback:
                log_callback(f"ERROR: {error_msg}")
            raise Exception(error_msg)
        
        return csv_data

    def _generate_anki_cards_from_structured_data(self, word, sentences, word_data):
        """Generate card types for a word using structured data."""
        cards = []
        
        required_sentences = 2 if self.generate_second_sentence else 1
        if len(sentences) < required_sentences:  # Need required number of sentences
            return cards
        
        # Get the original user input word for word removal and back column
        original_word = word_data.get('original_word', word)
        
        # Extract grammar information from structured data
        grammar_info = {
            'ipa': word_data.get('pronunciation', ''),
            'type': word_data.get('word_type', ''),
            'gender': word_data.get('gender', ''),
            'plural': word_data.get('plural', ''),
            'inflections': word_data.get('inflections', ''),
            'definition': word_data.get('danish_definition', ''),
            'english_word': word_data.get('english_translation', '')
        }
        
        # Card Type 1: Fill-in-the-blank + IPA
        sentence1_with_blank = self._remove_word_from_sentence(sentences[0], original_word, use_blank=True)
        grammar_details = self._format_grammar_details_from_structured_data(word_data)
        definition_clean = self._strip_english_from_definition(grammar_info.get('definition', ''))
        cards.append([
            sentence1_with_blank,                         # Front (Eksempel med ord fjernet eller blankt)
            self._get_image_url(word),                    # Front (Billede)
            definition_clean,                             # Front (Definition, grundform, osv.)
            original_word,                                # Back (et enkelt ord/udtryk, uden kontekst) - Use original word
            sentences[0],                                 # - Hele sætningen (intakt)
            f'{grammar_details} [sound:{original_word}.mp3]', # - Ekstra info (IPA, køn, bøjning) - Use original word for audio
            'y'                                           # • Lav 2 kort?
        ])
        
        # Card Type 2: Fill-in-the-blank + definition (definition present, no English)
        sentence1_no_word = self._remove_word_from_sentence(sentences[0], original_word, use_blank=False)
        cards.append([
            sentence1_no_word,                            # Front (Eksempel med ord fjernet eller blankt)
            self._get_image_url(word),                    # Front (Billede)
            f'{original_word} - {definition_clean}',      # Front (Definition, grundform, osv.) - Use original word
            '',                                           # Back (et enkelt ord/udtryk, uden kontekst) - empty for card 2
            sentences[0],                                 # - Hele sætningen (intakt)
            f'{grammar_details} [sound:{original_word}.mp3]', # - Ekstra info (IPA, køn, bøjning) - Use original word for audio
            ''                                            # • Lav 2 kort? - empty for card 2
        ])
        
        # Card Type 3: New sentence with blank (use second sentence if available and setting enabled)
        if self.generate_second_sentence and len(sentences) >= 2:
            sentence2_with_blank = self._remove_word_from_sentence(sentences[1], original_word, use_blank=True)
            cards.append([
                sentence2_with_blank,                    # Front (Eksempel med ord fjernet eller blankt)
                self._get_image_url(word),               # Front (Billede)
                definition_clean,                        # Front (Definition, grundform, osv.)
                original_word,                           # Back (et enkelt ord/udtryk, uden kontekst) - Use original word
                sentences[1],                            # - Hele sætningen (intakt)
                f'{grammar_details} [sound:{original_word}.mp3]', # - Ekstra info (IPA, køn, bøjning) - Use original word for audio
                ''                                       # • Lav 2 kort? - empty for card 3
            ])
        # Note: When second sentence is enabled, we generate 3 cards using 2 sentences (sentence 1 twice, sentence 2 once)
        # When disabled, we generate 2 cards using 1 sentence (sentence 1 twice)
        
        return cards

    def generate_cards_from_structured_data(self, word_data_list):
        """Generate cards from structured word data for review interface."""
        cards_data = []
        
        for word_data in word_data_list:
            # Skip error entries
            if word_data.get('error'):
                continue
                
            word = word_data.get('word', '')
            original_word = word_data.get('original_word', word)  # Get original user input word
            if not word:
                continue
            
            # Extract sentences from structured data
            example_sentences = word_data.get('example_sentences', [])
            sentences = []
            for sentence_data in example_sentences:
                if isinstance(sentence_data, dict) and sentence_data.get('danish'):
                    sentences.append(sentence_data['danish'])
            
            required_sentences = 2 if self.generate_second_sentence else 1
            if len(sentences) >= required_sentences:  # Need required number of sentences
                # Generate cards for this word with available sentences
                word_cards = self._generate_anki_cards_from_structured_data(word, sentences, word_data)
                
                # Add metadata for each card
                english_translation = word_data.get('english_translation', 'Unknown')
                image_url = self.word_image_urls.get(original_word, None)  # Use original word for image lookup
                
                for card in word_cards:
                    # Add preview information (Danish word, English translation, image status)
                    card_with_metadata = {
                        'card_data': card,
                        'danish_word': original_word,  # Use original word for display
                        'english_word': english_translation,
                        'image_url': image_url
                    }
                    cards_data.append(card_with_metadata)
        
        return cards_data
    
    def _format_grammar_details_from_structured_data(self, word_data):
        """Format detailed grammar information from structured data with proper Danish labels."""
        parts = []
        
        # Add IPA if available
        pronunciation = word_data.get('pronunciation', '')
        if pronunciation:
            if not pronunciation.startswith('/'):
                pronunciation = f'/{pronunciation}/'
            parts.append(pronunciation)
        
        # Build the main grammar section - focus on Danish word forms only
        grammar_parts = []
        
        # Add type (verbum, substantiv, etc.) - keep Danish terms only
        word_type = word_data.get('word_type', '').lower()
        if word_type:
            # Remove any English translations in parentheses
            word_type = re.sub(r'\s*\([^)]*\)', '', word_type)
            grammar_parts.append(word_type)
        
        # Add type-specific information based on word type
        if word_type in ['substantiv', 'noun']:
            # For nouns: include gender and plural
            gender = word_data.get('gender', '')
            if gender and gender.lower() not in ['null', '']:
                gender = re.sub(r'\s*\([^)]*\)', '', gender)
                grammar_parts.append(f"køn: {gender}")
            
            plural = word_data.get('plural', '')
            if plural and plural.lower() not in ['null', '']:
                plural = re.sub(r'\s*\([^)]*\)', '', plural)
                
        elif word_type in ['verbum', 'verb']:
            # For verbs: include inflections as "bøjning"
            inflections = word_data.get('inflections', '')
            if inflections and inflections.lower() not in ['null', '']:
                # Remove English explanations and keep only Danish word forms
                inflections = re.sub(r'\s*\([^)]*\)', '', inflections)
                inflections = re.sub(r'\s*[-–—]\s*[A-Za-z\s,]+$', '', inflections)
                if inflections.strip():
                    grammar_parts.append(f"bøjning: {inflections.strip()}")
                    
        elif word_type in ['adjektiv', 'adjective']:
            # For adjectives: include comparative/superlative forms as "bøjning"
            inflections = word_data.get('inflections', '')
            if inflections and inflections.lower() not in ['null', '']:
                inflections = re.sub(r'\s*\([^)]*\)', '', inflections)
                inflections = re.sub(r'\s*[-–—]\s*[A-Za-z\s,]+$', '', inflections)
                if inflections.strip():
                    grammar_parts.append(f"bøjning: {inflections.strip()}")
        else:
            # For other word types: include inflections if available
            inflections = word_data.get('inflections', '')
            if inflections and inflections.lower() not in ['null', '']:
                inflections = re.sub(r'\s*\([^)]*\)', '', inflections)
                inflections = re.sub(r'\s*[-–—]\s*[A-Za-z\s,]+$', '', inflections)
                if inflections.strip():
                    grammar_parts.append(f"bøjning: {inflections.strip()}")
        
        # Combine parts with proper formatting
        if parts and grammar_parts:
            return f"{parts[0]} – {', '.join(grammar_parts)}"
        elif parts:
            return parts[0]
        elif grammar_parts:
            return ', '.join(grammar_parts)
        else:
            return "Grammatik info nødvendig"

    def _remove_word_from_sentence(self, sentence, word_to_remove, use_blank=True):
        """Remove word from sentence and optionally replace with blank. 
        Enhanced version with better pattern matching to handle Danish inflections."""
        import re
        import unicodedata
        
        # Normalize both strings to handle Unicode issues
        sentence_normalized = unicodedata.normalize('NFC', sentence)
        word_normalized = unicodedata.normalize('NFC', word_to_remove.lower())
        
        # For Danish, we need to handle common inflections and conjugations
        # Try to find the word with common Danish endings
        common_inflections = [
            '',           # base form
            'en',         # definite article (substantives)
            'et',         # definite article (neuter)
            'erne',       # definite plural
            'ne',         # definite plural (some words)
            'e',          # adjective/verb ending
            'er',         # verb present/plural nouns
            'ed',         # past participle
            't',          # neuter/past tense
            'ede',        # past tense
            'te',         # past tense
            'tes',        # passive
            'ede',        # past tense
            's',          # genitive/passive
        ]
        
        result_sentence = sentence_normalized
        replacement = '___' if use_blank else ''
        word_found = False
        
        # Try exact word boundary matches first (including inflected forms)
        for ending in common_inflections:
            inflected_word = word_normalized + ending
            
            # Try multiple case variations
            patterns = [
                r'\b' + re.escape(inflected_word) + r'\b',                    # lowercase
                r'\b' + re.escape(inflected_word.capitalize()) + r'\b',       # capitalized
                r'\b' + re.escape(inflected_word.upper()) + r'\b',            # uppercase
            ]
            
            for pattern in patterns:
                if re.search(pattern, result_sentence, re.IGNORECASE):
                    result_sentence = re.sub(pattern, replacement, result_sentence, count=1, flags=re.IGNORECASE)
                    word_found = True
                    break
            
            if word_found:
                break
        
        # If still not found, try partial matching for complex cases
        if not word_found:
            # Look for the base word as part of a larger word
            partial_patterns = [
                r'\b' + re.escape(word_normalized) + r'\w*\b',     # word + any endings
                r'(?i)\b' + re.escape(word_normalized) + r'\w*\b', # case insensitive + any endings
            ]
            
            for pattern in partial_patterns:
                match = re.search(pattern, result_sentence)
                if match:
                    matched_word = match.group(0)
                    result_sentence = result_sentence.replace(matched_word, replacement, 1)
                    word_found = True
                    break
        
        # Final fallback if still not found
        if not word_found and use_blank:
            # Instead of the prominent error message, try a gentler approach
            # Check if word appears anywhere in sentence (even partially)
            if word_normalized in sentence_normalized.lower():
                # Word is there but our patterns didn't catch it
                # Add a discrete placeholder
                result_sentence = f"___ {sentence_normalized.strip()}"
            else:
                # Word genuinely not found - use a subtle indicator
                result_sentence = f"___ [{word_normalized}?] {sentence_normalized.strip()}"
        
        if not use_blank:
            # Clean up extra spaces and punctuation
            result_sentence = re.sub(r'\s+', ' ', result_sentence).strip()
            result_sentence = re.sub(r'\s+([,.!?])', r'\1', result_sentence)
            
        return result_sentence
    
    def _get_image_url(self, word):
        """Get the image URL for a word, or return empty string if not available."""
        if word in self.word_image_urls and self.word_image_urls[word]:
            return f'<image src="{self.word_image_urls[word]}">'
        return ''  # Leave blank when no image is available
    
    def _strip_english_from_definition(self, definition):
        """Remove any English translation after a dash or parenthesis."""
        if not definition:
            return ''
        # Remove dash + English
        definition = re.sub(r'\s*[-–—]\s*[A-Za-z ,;\'\"()]+$', '', definition)
        # Remove parenthetical English at end
        definition = re.sub(r'\s*\([A-Za-z ,;\'\"-]+\)\s*$', '', definition)
        return definition.strip()
