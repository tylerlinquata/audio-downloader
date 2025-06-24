"""Business logic for card generation and CSV export."""

import re
import os
import shutil
import csv


class CardProcessor:
    """Handles card generation and CSV processing logic."""
    
    def __init__(self):
        self.word_image_urls = {}
    
    def set_image_urls(self, image_urls):
        """Set the image URLs dictionary."""
        self.word_image_urls = image_urls
    
    def generate_cards_for_review(self, sentence_results_text):
        """Generate cards from sentence results for review interface."""
        content = sentence_results_text
        
        # Parse the content to extract words and sentences
        cards_data = []
        
        # Split by word blocks - handle both "---\n\n" between blocks and trailing "---"
        word_blocks = re.split(r'---(?:\s*\n\n|\s*$)', content)
        
        for block in word_blocks:
            block = block.strip()
            if not block:
                continue
                
            # Extract the word from the beginning of the block
            word_match = re.match(r'\*\*([^*]+)\*\*', block)
            if not word_match:
                continue
                
            word = word_match.group(1).strip()
            
            # Skip if this is formatting text
            if word.lower() in ['example sentences', 'eksempel sætninger']:
                continue
            
            # Extract grammar information from the block
            grammar_info = self._extract_grammar_info(block)
            
            # Extract sentences from the block
            sentence_pattern = r'(\d+)\.\s*([^-\n]+?)\s*-\s*([^\n]+?)(?=\n\d+\.|\n\n|\Z)'
            matches = re.findall(sentence_pattern, block, re.DOTALL)
            
            if not matches:
                continue
            
            sentences = []
            for match in matches:
                sentence_num, danish, english = match
                danish = danish.strip()
                english = english.strip()
                if danish and english:
                    sentences.append(danish)
            
            if len(sentences) >= 3:
                # Generate the three card types for this word with grammar info
                word_cards = self._generate_anki_cards(word, sentences[:3], grammar_info)
                
                # Add metadata for each card
                english_translation = grammar_info.get('english_word', 'Unknown')
                image_url = self.word_image_urls.get(word, None)
                
                for card in word_cards:
                    # Add preview information (Danish word, English translation, image status)
                    card_with_metadata = {
                        'card_data': card,
                        'danish_word': word,
                        'english_word': english_translation,
                        'image_url': image_url
                    }
                    cards_data.append(card_with_metadata)
        
        return cards_data
    
    def export_sentences_to_csv(self, sentence_results_text, file_path):
        """Export sentences to CSV format for Anki import with specific card types."""
        content = sentence_results_text
        
        # Parse the content to extract words and sentences
        csv_data = []
        
        # Split by word blocks - handle both "---\n\n" between blocks and trailing "---"
        word_blocks = re.split(r'---(?:\s*\n\n|\s*$)', content)
        
        for block in word_blocks:
            block = block.strip()
            if not block:
                continue
                
            # Extract the word from the beginning of the block
            word_match = re.match(r'\*\*([^*]+)\*\*', block)
            if not word_match:
                continue
                
            word = word_match.group(1).strip()
            
            # Skip if this is formatting text
            if word.lower() in ['example sentences', 'eksempel sætninger']:
                continue
            
            # Extract grammar information from the block
            grammar_info = self._extract_grammar_info(block)
            
            # Extract sentences from the block
            sentence_pattern = r'(\d+)\.\s*([^-\n]+?)\s*-\s*([^\n]+?)(?=\n\d+\.|\n\n|\Z)'
            matches = re.findall(sentence_pattern, block, re.DOTALL)
            
            if not matches:
                continue
            
            sentences = []
            for match in matches:
                sentence_num, danish, english = match
                danish = danish.strip()
                english = english.strip()
                if danish and english:
                    sentences.append(danish)
            
            if len(sentences) >= 3:
                # Generate the three card types for this word with grammar info
                csv_data.extend(self._generate_anki_cards(word, sentences[:3], grammar_info))
        
        # Write to CSV file
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # Don't write header for Anki import - Anki doesn't expect headers
            writer.writerows(csv_data)
        
        return csv_data
    
    def copy_audio_files_to_anki(self, selected_cards, output_dir, anki_folder):
        """Copy audio files for selected cards to Anki media folder."""
        if not anki_folder or not os.path.exists(anki_folder):
            return {"success": False, "message": "Anki media folder not found"}
        
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
                except Exception as e:
                    failed_copies.append(word)
            else:
                failed_copies.append(word)
        
        return {
            "success": True,
            "copied_count": copied_count,
            "failed_copies": failed_copies,
            "total_words": len(words_to_copy)
        }
    
    def _extract_grammar_info(self, block):
        """Extract grammar information from a word block."""
        grammar_info = {
            'ipa': '',
            'type': '',
            'gender': '',
            'plural': '',
            'inflections': '',
            'definition': '',
            'english_word': ''
        }
        
        # Look for grammar info section
        grammar_match = re.search(r'\*\*Grammar Info:\*\*(.*?)(?=\*\*Example Sentences:\*\*|\Z)', block, re.DOTALL)
        if grammar_match:
            grammar_section = grammar_match.group(1).strip()
            
            # Extract IPA
            ipa_match = re.search(r'IPA:\s*([^\n]+)', grammar_section)
            if ipa_match:
                grammar_info['ipa'] = ipa_match.group(1).strip()
            
            # Extract type
            type_match = re.search(r'Type:\s*([^\n]+)', grammar_section)
            if type_match:
                grammar_info['type'] = type_match.group(1).strip()
            
            # Extract gender
            gender_match = re.search(r'Gender:\s*([^\n]+)', grammar_section)
            if gender_match:
                grammar_info['gender'] = gender_match.group(1).strip()
            
            # Extract plural
            plural_match = re.search(r'Plural:\s*([^\n]+)', grammar_section)
            if plural_match:
                grammar_info['plural'] = plural_match.group(1).strip()
            
            # Extract inflections
            inflections_match = re.search(r'Inflections:\s*([^\n]+)', grammar_section)
            if inflections_match:
                grammar_info['inflections'] = inflections_match.group(1).strip()
            
            # Extract definition
            definition_match = re.search(r'Definition:\s*([^\n]+)', grammar_section)
            if definition_match:
                grammar_info['definition'] = definition_match.group(1).strip()
            
            # Extract English word
            english_word_match = re.search(r'English word:\s*([^\n]+)', grammar_section)
            if english_word_match:
                grammar_info['english_word'] = english_word_match.group(1).strip()
        
        return grammar_info
    
    def _generate_anki_cards(self, word, sentences, grammar_info=None):
        """Generate three card types for a word with the given sentences."""
        cards = []
        
        if len(sentences) < 3:
            return cards
        
        # Initialize grammar info if not provided
        if grammar_info is None:
            grammar_info = {
                'ipa': f'IPA_for_{word}',
                'type': 'ukendt',
                'gender': '',
                'plural': '',
                'inflections': f'Grammatik info for {word}',
                'definition': f'Definition af {word}'
            }
        
        # Card Type 1: Fill-in-the-blank + IPA
        sentence1_with_blank = self._remove_word_from_sentence(sentences[0], word, use_blank=True)
        grammar_details = self._format_grammar_details(grammar_info)
        definition_clean = self._strip_english_from_definition(grammar_info.get('definition', ''))
        cards.append([
            sentence1_with_blank,                    # Front (Eksempel med ord fjernet eller blankt)
            self._get_image_url(word),               # Front (Billede)
            definition_clean,                        # Front (Definition, grundform, osv.)
            word,                                    # Back (et enkelt ord/udtryk, uden kontekst)
            sentences[0],                            # - Hele sætningen (intakt)
            f'{grammar_details} [sound:{word}.mp3]', # - Ekstra info (IPA, køn, bøjning)
            'y'                                      # • Lav 2 kort?
        ])
        
        # Card Type 2: Fill-in-the-blank + definition (definition present, no English)
        sentence1_no_word = self._remove_word_from_sentence(sentences[0], word, use_blank=False)
        cards.append([
            sentence1_no_word,                       # Front (Eksempel med ord fjernet eller blankt)
            self._get_image_url(word),               # Front (Billede)
            f'{word} - {definition_clean}',          # Front (Definition, grundform, osv.)
            '',                                      # Back (et enkelt ord/udtryk, uden kontekst) - empty for card 2
            sentences[0],                            # - Hele sætningen (intakt)
            f'{grammar_details} [sound:{word}.mp3]', # - Ekstra info (IPA, køn, bøjning)
            ''                                       # • Lav 2 kort? - empty for card 2
        ])
        
        # Card Type 3: New sentence with blank
        sentence2_with_blank = self._remove_word_from_sentence(sentences[1], word, use_blank=True)
        cards.append([
            sentence2_with_blank,                    # Front (Eksempel med ord fjernet eller blankt)
            self._get_image_url(word),               # Front (Billede)
            definition_clean,                        # Front (Definition, grundform, osv.)
            word,                                    # Back (et enkelt ord/udtryk, uden kontekst)
            sentences[1],                            # - Hele sætningen (intakt)
            f'{grammar_details} [sound:{word}.mp3]', # - Ekstra info (IPA, køn, bøjning)
            ''                                       # • Lav 2 kort? - empty for card 3
        ])
        
        return cards
    
    def _remove_word_from_sentence(self, sentence, word_to_remove, use_blank=True):
        """Remove word from sentence and optionally replace with blank."""
        # Create patterns for the word and common inflected forms
        base_word = word_to_remove.lower()
        patterns = [
            r'\b' + re.escape(word_to_remove) + r'\b',  # exact match
            r'\b' + re.escape(word_to_remove.capitalize()) + r'\b',  # capitalized
            r'\b' + re.escape(word_to_remove.upper()) + r'\b',  # uppercase
        ]
        
        # Add common Danish inflections
        if base_word.endswith('e'):
            # For words ending in 'e', try without 'e' + common endings
            stem = base_word[:-1]
            patterns.extend([
                r'\b' + re.escape(stem + 'en') + r'\b',  # definite form
                r'\b' + re.escape(stem + 'er') + r'\b',  # plural
                r'\b' + re.escape(stem + 'erne') + r'\b',  # definite plural
            ])
        else:
            # For words not ending in 'e', add common endings
            patterns.extend([
                r'\b' + re.escape(base_word + 'en') + r'\b',  # definite form (en-words)
                r'\b' + re.escape(base_word + 'et') + r'\b',  # neuter definite (et-words)
                r'\b' + re.escape(base_word + 'e') + r'\b',   # adjective/verb form
                r'\b' + re.escape(base_word + 'er') + r'\b',  # plural/present
                r'\b' + re.escape(base_word + 'erne') + r'\b', # definite plural
            ])
        
        # Special case for common double consonant patterns (e.g., kat -> katten)
        if len(base_word) >= 2 and base_word[-1] == base_word[-2]:
            # Double consonant at end (like "kat" -> "katt")
            single_consonant = base_word[:-1]
            patterns.extend([
                r'\b' + re.escape(single_consonant + 'en') + r'\b',  # katten
                r'\b' + re.escape(single_consonant + 'er') + r'\b',  # katter
                r'\b' + re.escape(single_consonant + 'erne') + r'\b', # katterne
            ])
        elif len(base_word) >= 2:
            # Try adding double consonant for inflection (kat -> katt -> katten)
            last_consonant = base_word[-1]
            if last_consonant not in 'aeiouæøå':  # if last letter is consonant
                double_consonant_stem = base_word + last_consonant
                patterns.extend([
                    r'\b' + re.escape(double_consonant_stem + 'en') + r'\b',  # katten
                    r'\b' + re.escape(double_consonant_stem + 'er') + r'\b',  # katter
                    r'\b' + re.escape(double_consonant_stem + 'erne') + r'\b', # katterne
                ])
        
        # Try each pattern
        result_sentence = sentence
        for pattern in patterns:
            if re.search(pattern, result_sentence, flags=re.IGNORECASE):
                if use_blank:
                    result_sentence = re.sub(pattern, '___', result_sentence, flags=re.IGNORECASE)
                else:
                    result_sentence = re.sub(pattern, '', result_sentence, flags=re.IGNORECASE)
                break
        
        if not use_blank:
            # Clean up extra spaces and punctuation
            result_sentence = re.sub(r'\s+', ' ', result_sentence).strip()
            result_sentence = re.sub(r'\s+([,.!?])', r'\1', result_sentence)
            
        return result_sentence
    
    def _get_image_url(self, word):
        """Get the image URL for a word, or return placeholder if not available."""
        if word in self.word_image_urls and self.word_image_urls[word]:
            return f'<image src="{self.word_image_urls[word]}">'
        return '<image src="myimage.jpg">'  # Fallback placeholder
    
    def _strip_english_from_definition(self, definition):
        """Remove any English translation after a dash or parenthesis."""
        if not definition:
            return ''
        # Remove dash + English
        definition = re.sub(r'\s*[-–—]\s*[A-Za-z ,;\'\"()]+$', '', definition)
        # Remove parenthetical English at end
        definition = re.sub(r'\s*\([A-Za-z ,;\'\"-]+\)\s*$', '', definition)
        return definition.strip()
    
    def _format_grammar_details(self, grammar_info):
        """Format detailed grammar information with IPA and word forms only (no English)."""
        parts = []
        
        # Add IPA if available
        if grammar_info.get('ipa'):
            ipa = grammar_info['ipa']
            if not ipa.startswith('/'):
                ipa = f'/{ipa}/'
            parts.append(ipa)
        
        # Build the main grammar section - focus on Danish word forms only
        grammar_parts = []
        
        # Add type (verbum, substantiv, etc.) - keep Danish terms only
        if grammar_info.get('type'):
            word_type = grammar_info['type']
            # Remove any English translations in parentheses
            word_type = re.sub(r'\s*\([^)]*\)', '', word_type)
            grammar_parts.append(word_type)
        
        # Add gender for nouns (if applicable)
        if grammar_info.get('gender'):
            gender = grammar_info['gender']
            # Remove any English translations
            gender = re.sub(r'\s*\([^)]*\)', '', gender)
            grammar_parts.append(f"køn: {gender}")
        
        # Add inflections - focus on actual word forms, not explanations
        if grammar_info.get('inflections'):
            inflections = grammar_info['inflections']
            # Remove English explanations and keep only Danish word forms
            # Remove anything in parentheses (usually English)
            inflections = re.sub(r'\s*\([^)]*\)', '', inflections)
            # Remove English explanations after dashes
            inflections = re.sub(r'\s*[-–—]\s*[A-Za-z\s,]+$', '', inflections)
            if inflections.strip():
                grammar_parts.append(inflections.strip())
        
        # Add plural form if available and not already in inflections
        if grammar_info.get('plural'):
            plural = grammar_info['plural']
            # Remove English explanations
            plural = re.sub(r'\s*\([^)]*\)', '', plural)
            plural = re.sub(r'\s*[-–—]\s*[A-Za-z\s,]+$', '', plural)
            if plural.strip() and 'flertal' not in str(grammar_parts):
                grammar_parts.append(f"flertal: {plural.strip()}")
        
        # Combine parts with proper formatting
        if parts and grammar_parts:
            return f"{parts[0]} – {', '.join(grammar_parts)}"
        elif parts:
            return parts[0]
        elif grammar_parts:
            return ', '.join(grammar_parts)
        else:
            return "Grammatik info nødvendig"
