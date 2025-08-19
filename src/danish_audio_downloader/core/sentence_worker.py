"""
Worker thread for generating example sentences using ChatGPT.
"""

import time
import json
import re
from typing import List, Dict, Optional
from PyQt5.QtCore import QThread, pyqtSignal
import openai
from openai import OpenAI

from ..utils.config import AppConfig


class SentenceWorker(QThread):
    """Worker thread for generating example sentences using ChatGPT."""
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(list, dict)  # word_data_list, word_translations
    error_signal = pyqtSignal(str)  # error message

    def __init__(self, words: List[str], cefr_level: str, api_key: str, ordnet_data: Optional[Dict] = None) -> None:
        super().__init__()
        self.words = words
        self.cefr_level = cefr_level
        self.api_key = api_key
        self.ordnet_data = ordnet_data or {}
        self.abort_flag = False

    def run(self) -> None:
        """Run the sentence generation process."""
        try:
            # Set up OpenAI client
            openai.api_key = self.api_key
            client = openai.OpenAI(api_key=self.api_key)
            
            word_data_list = []  # Store structured data instead of formatted strings
            word_translations = {}  # Track English translations for image fetching
            total_words = len(self.words)
            
            self.update_signal.emit(f"Starting sentence generation for {total_words} words...")
            
            # Always use optimized batch processing
            self.update_signal.emit("Using optimized batch processing...")
            
            # Conservative batch processing to avoid API limits
            if total_words <= AppConfig.BATCH_THRESHOLD:
                # Process all words in one batch for small lists
                word_data_list, word_translations = self._process_words_batch(client, self.words)
            else:
                # For larger lists, use smaller, safer chunks
                chunk_size = min(AppConfig.BATCH_SIZE, 25)  # Cap at 25 words per chunk for stability
                self.update_signal.emit(f"Processing {total_words} words in chunks of {chunk_size}...")
                
                for i in range(0, total_words, chunk_size):
                    if self.abort_flag:
                        self.update_signal.emit("Sentence generation aborted by user")
                        break
                    
                    chunk = self.words[i:i + chunk_size]
                    chunk_start = i + 1
                    chunk_end = min(i + chunk_size, total_words)
                    
                    self.update_signal.emit(f"Processing batch {chunk_start}-{chunk_end} of {total_words}...")
                    self.progress_signal.emit(chunk_end, total_words)
                    
                    chunk_data, chunk_translations = self._process_words_batch(client, chunk)
                    word_data_list.extend(chunk_data)
                    word_translations.update(chunk_translations)
                    
                    # Minimal delay between chunks
                    if i + chunk_size < total_words:
                        time.sleep(0.1)  # Reduced delay
            
            if not self.abort_flag:
                self.update_signal.emit(f"Sending results for {len(word_data_list)} words to main thread...")
                self.finished_signal.emit(word_data_list, word_translations)
            
        except Exception as e:
            self.error_signal.emit(f"Failed to initialize OpenAI: {str(e)}")

    def _process_words_batch(self, client, words_batch):
        """Process multiple words in a single ChatGPT request for optimal speed."""
        word_data_list = []
        word_translations = {}
        
        # Create batch prompt for multiple words
        words_json = ', '.join([f'"{word}"' for word in words_batch])
        
        prompt = f"""For the Danish words [{words_json}], provide example sentences and English translations.

CRITICAL: You MUST return the EXACT words as provided - do not change, substitute, or modify them in any way.

Use this EXACT format:
{{
    "words": [
        {{
            "word": "word1",
            "english_translation": "baseword",
            "example_sentences": [
                {{
                    "danish": "Danish sentence containing the exact word word1",
                    "english": "English translation"
                }},
                {{
                    "danish": "Another Danish sentence containing the exact word word1",
                    "english": "English translation"
                }}
            ]
        }}
    ]
}}

Requirements:
- MANDATORY: Return each word EXACTLY as provided in the word list - no changes whatsoever
- MANDATORY: Use each exact word as provided in the Danish sentences - do not change spelling, inflection, or form
- If a word is inflected (like "rejser"), use that exact inflected form in the sentence
- If a word is a base form (like "rejse"), use that exact base form in the sentence  
- CEFR level: {self.cefr_level}
- 2 example sentences per word
- Focus on creating natural example sentences that properly use the given word forms
- English translation MUST be the dictionary base form (single word only)
- For verbs, use the infinitive WITHOUT "to" (e.g., "talk" not "to talk", "eat" not "to eat")
- For nouns, use singular form WITHOUT articles (e.g., "cat" not "the cat", "house" not "the house")
- NEVER include articles (the, a, an) or prepositions (to, of, in, etc.)
- DO NOT escape quotes in Danish text
- Return ONLY the JSON object"""
        
        try:
            # Calculate appropriate token limit based on batch size
            batch_multiplier = min(3, max(1, len(words_batch) // 10))  # Scale tokens with batch size
            token_limit = min(AppConfig.OPENAI_MAX_TOKENS * batch_multiplier, 4000)  # Cap at 4000 tokens
            
            # Make single API call for all words in batch
            response = client.chat.completions.create(
                model=AppConfig.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a Danish language teacher specializing in creating natural example sentences. Return ONLY valid JSON. NEVER use backslash-quote (\\\" ) in JSON values. Use normal quotes in Danish text. Focus on creating clear, contextual sentences that demonstrate word usage. For English translations, always use the BASE WORD ONLY: infinitive for verbs WITHOUT 'to' (e.g., 'talk' not 'to talk'), singular for nouns WITHOUT articles (e.g., 'cat' not 'the cat')."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=token_limit
            )
            
            self.update_signal.emit(f"API call successful. Processing {len(words_batch)} words...")
            
            # Check if response is valid
            if not response or not response.choices or not response.choices[0].message:
                self.update_signal.emit("Error: Invalid response structure from OpenAI API")
                return self._create_error_fallback_for_batch(words_batch, "Invalid response structure from OpenAI API")
            
            # Parse JSON response
            json_content = response.choices[0].message.content
            
            # Check if content exists and is not None
            if json_content is None:
                self.update_signal.emit("Error: Received None content from OpenAI API")
                return self._create_error_fallback_for_batch(words_batch, "None content from OpenAI API")
            
            json_content = json_content.strip()
            
            # Check for empty response
            if not json_content:
                self.update_signal.emit("Error: Received empty response from OpenAI API")
                return self._create_error_fallback_for_batch(words_batch, "Empty response from OpenAI API")
            
            batch_data = self._parse_batch_response(json_content)
            
            if batch_data and 'words' in batch_data:
                processed_count = 0
                for i, word_data in enumerate(batch_data['words']):
                    if word_data.get('word'):
                        # Preserve the original user input word if we have it
                        if i < len(words_batch):
                            word_data['original_word'] = words_batch[i]
                        else:
                            # Fallback to the word from the response
                            word_data['original_word'] = word_data.get('word', '')
                        
                        original_word = word_data['original_word']
                        returned_word = word_data.get('word', '').lower().strip()
                        
                        # Clean the English translation immediately after parsing
                        if word_data.get('english_translation'):
                            word_data['english_translation'] = self._clean_english_translation(word_data['english_translation'])
                        
                        # VALIDATE: Check if AI returned the correct word
                        if returned_word != original_word.lower().strip():
                            self.update_signal.emit(f"AI returned '{returned_word}' instead of requested '{original_word}' - marking for retry")
                            word_data['needs_retry'] = True
                            word_data['retry_reason'] = 'wrong_word_returned'
                        else:
                            # VALIDATE: Check if sentences actually contain the user's word
                            validated_sentences = self._validate_sentences_contain_word(word_data.get('example_sentences', []), original_word)
                            
                            if len(validated_sentences) < 2:  # Need at least 2 valid sentences
                                self.update_signal.emit(f"Word '{original_word}' needs individual retry - insufficient valid sentences")
                                # For batch processing, we'll mark this word for individual retry later
                                word_data['needs_retry'] = True
                                word_data['retry_reason'] = 'insufficient_sentences'
                            else:
                                # Update with only the validated sentences
                                word_data['example_sentences'] = validated_sentences
                        
                        word_data_list.append(word_data)
                        processed_count += 1
                        
                        # Store English translation for image fetching using original word
                        if word_data.get('english_translation'):
                            word_translations[original_word] = word_data['english_translation'].lower().strip()
                        
                        # Merge with Ordnet data and set defaults
                        self._merge_ordnet_data_and_set_defaults(word_data, original_word)
                        
                        # Update image lookup with English translation
                        if word_data.get('english_translation'):
                            word_translations[original_word] = word_data['english_translation'].lower().strip()
                    
                self.update_signal.emit(f"Successfully processed {processed_count} words in batch (requested {len(words_batch)})")
                
                # Check for words that need individual retry due to validation failures
                retry_words = [word_data for word_data in word_data_list if word_data.get('needs_retry')]
                if retry_words:
                    self.update_signal.emit(f"Retrying {len(retry_words)} words individually...")
                    for word_data in retry_words:
                        original_word = word_data['original_word']
                        retry_reason = word_data.get('retry_reason', 'unknown')
                        
                        # Use different retry strategies based on the reason
                        if retry_reason == 'wrong_word_returned':
                            retry_result = self._retry_with_word_emphasis(client, original_word)
                        else:
                            retry_result = self._retry_sentence_generation(client, original_word)
                        
                        if retry_result and len(self._validate_sentences_contain_word(retry_result.get('example_sentences', []), original_word)) >= 2:
                            # Update the word_data with the new sentences
                            word_data['example_sentences'] = retry_result['example_sentences']
                            if retry_result.get('english_translation'):
                                word_data['english_translation'] = retry_result['english_translation']
                            # Fix the word field to match the original request
                            word_data['word'] = original_word
                            word_data['needs_retry'] = False  # Mark as resolved
                            del word_data['retry_reason']  # Clean up
                        else:
                            # Try to find if an inflected form works
                            self.update_signal.emit(f"Checking if inflected form of '{original_word}' can be used...")
                            inflected_form = self._find_inflected_form_in_sentences(retry_result.get('example_sentences', []) if retry_result else [], original_word)
                            
                            if inflected_form:
                                self.update_signal.emit(f"Found inflected form '{inflected_form}' for '{original_word}' - using this form consistently")
                                # Update the word to use the inflected form consistently
                                word_data['word'] = inflected_form
                                word_data['original_word'] = inflected_form  # Use inflected form for audio download
                                if retry_result:
                                    word_data['example_sentences'] = retry_result['example_sentences']
                                    if retry_result.get('english_translation'):
                                        word_data['english_translation'] = retry_result['english_translation']
                                word_data['needs_retry'] = False
                                word_data['inflected_form_used'] = True  # Flag to indicate we're using an inflected form
                                del word_data['retry_reason']
                                
                                # Update the translation key to use the inflected form
                                if word_data.get('english_translation'):
                                    word_translations[inflected_form] = word_data['english_translation'].lower().strip()
                            else:
                                # Try systematically with different inflected forms
                                self.update_signal.emit(f"Attempting systematic inflected form retry for '{original_word}'...")
                                inflected_retry_result = self._retry_with_inflected_forms(client, original_word)
                                
                                if inflected_retry_result:
                                    self.update_signal.emit(f"Success with inflected form retry for '{original_word}'")
                                    inflected_word = inflected_retry_result['word']
                                    word_data['word'] = inflected_word
                                    word_data['original_word'] = inflected_word  # Use inflected form for audio download
                                    word_data['example_sentences'] = inflected_retry_result['example_sentences']
                                    if inflected_retry_result.get('english_translation'):
                                        # Clean up the English translation
                                        english_translation = inflected_retry_result['english_translation']
                                        word_data['english_translation'] = self._clean_english_translation(english_translation)
                                    word_data['needs_retry'] = False
                                    word_data['inflected_form_used'] = True
                                    word_data['base_word'] = original_word  # Keep track of the original word
                                    del word_data['retry_reason']
                                    
                                    # Update the translation key to use the inflected form
                                    if word_data.get('english_translation'):
                                        word_translations[inflected_word] = word_data['english_translation'].lower().strip()
                                else:
                                    self.update_signal.emit(f"Warning: Could not generate valid sentences for '{original_word}' or any inflected form")
                
                # If we got fewer words than expected, warn but continue
                if processed_count < len(words_batch):
                    missing_count = len(words_batch) - processed_count
                    self.update_signal.emit(f"Warning: {missing_count} words may not have been processed correctly")
                    
            else:
                # Fallback: if batch parsing fails, try processing words individually
                self.update_signal.emit("Batch processing failed, attempting individual word processing...")
                word_data_list, word_translations = [], {}
                
                for word in words_batch:
                    try:
                        single_data, single_translations = self._process_single_word(client, word)
                        word_data_list.extend(single_data)
                        word_translations.update(single_translations)
                    except Exception as single_error:
                        self.update_signal.emit(f"Individual processing failed for '{word}': {str(single_error)}")
                        error_data = self._create_error_word_data(word, f'Individual processing failed: {str(single_error)}')
                        word_data_list.append(error_data)
                
                if word_data_list:
                    self.update_signal.emit(f"Individual fallback completed: {len(word_data_list)} words processed")
                    return word_data_list, word_translations
                else:
                    # Final fallback: create error entries
                    self.update_signal.emit("All processing methods failed, creating error entries...")
                    return self._create_error_fallback_for_batch(words_batch, "All processing methods failed - could not parse response")
                
        except openai.RateLimitError as e:
            self.update_signal.emit(f"Rate limit exceeded: {str(e)}. Processing with retry fallback...")
            # Simple retry with single word processing for rate limit issues
            word_data_list, word_translations = [], {}
            for word in words_batch:
                try:
                    time.sleep(1)  # Rate limit recovery delay
                    single_data, single_translations = self._process_single_word(client, word)
                    word_data_list.extend(single_data)
                    word_translations.update(single_translations)
                except Exception as single_error:
                    self.update_signal.emit(f"Failed to process '{word}': {str(single_error)}")
                    error_data = self._create_error_word_data(word, f'Could not generate sentences: {str(single_error)}')
                    word_data_list.append(error_data)
            return word_data_list, word_translations
        except openai.AuthenticationError as e:
            self.update_signal.emit(f"OpenAI Authentication error: {str(e)}. Check your API key...")
            return self._create_error_fallback_for_batch(words_batch, f'Authentication error: {str(e)}')
        except openai.NotFoundError as e:
            self.update_signal.emit(f"OpenAI Model not found: {str(e)}. Model '{AppConfig.OPENAI_MODEL}' may not exist...")
            return self._create_error_fallback_for_batch(words_batch, f'Model not found: {str(e)}')
        except openai.APIError as e:
            self.update_signal.emit(f"OpenAI API error: {str(e)}. Using error fallback...")
            return self._create_error_fallback_for_batch(words_batch, f'OpenAI API error: {str(e)}')
        except Exception as e:
            self.update_signal.emit(f"Batch processing error: {str(e)}. Using error fallback...")
            return self._create_error_fallback_for_batch(words_batch, f'Batch processing error: {str(e)}')
        
        return word_data_list, word_translations
    
    def _create_error_fallback_for_batch(self, words_batch: List[str], error_message: str):
        """Create error fallback data for an entire batch of words."""
        word_data_list = []
        word_translations = {}
        
        for word in words_batch:
            error_data = self._create_error_word_data(word, error_message)
            word_data_list.append(error_data)
            if error_data.get('english_translation'):
                word_translations[word] = error_data['english_translation'].lower().strip()
        
        return word_data_list, word_translations
    
    def _process_single_word(self, client, word: str):
        """Process a single word with simplified logic."""
        word_data_list = []
        word_translations = {}
        
        # Simplified prompt for single word
        prompt = f"""For the Danish word "{word}", create exactly 2 example sentences and provide English translation.

CRITICAL: Each sentence MUST contain the exact word "{word}" as written.

Return ONLY this JSON:
{{
    "word": "{word}",
    "english_translation": "baseword",
    "example_sentences": [
        {{"danish": "Sentence with {word}", "english": "English translation"}},
        {{"danish": "Another sentence with {word}", "english": "English translation"}}
    ]
}}"""
        
        try:
            response = client.chat.completions.create(
                model=AppConfig.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Return ONLY valid JSON. Use exact word forms as provided. English translation must be a single base word without articles or prepositions."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=AppConfig.OPENAI_MAX_TOKENS
            )
            
            json_content = response.choices[0].message.content.strip()
            word_data = self._parse_response(json_content)
            
            if word_data:
                # Clean the English translation immediately after parsing
                if word_data.get('english_translation'):
                    word_data['english_translation'] = self._clean_english_translation(word_data['english_translation'])
                
                # VALIDATE: Check if AI returned the correct word
                returned_word = word_data.get('word', '').lower().strip()
                if returned_word != word.lower().strip():
                    self.update_signal.emit(f"Single word processing: AI returned '{returned_word}' instead of '{word}' - retrying with emphasis")
                    # Try the word emphasis retry method
                    word_data = self._retry_with_word_emphasis(client, word)
                
                if word_data:
                    # VALIDATE: Check if sentences contain the exact word
                    validated_sentences = self._validate_sentences_contain_word(word_data.get('example_sentences', []), word)
                    if len(validated_sentences) < 2:
                        # Try to find if an inflected form works
                        self.update_signal.emit(f"Single word processing: checking inflected forms for '{word}'...")
                        inflected_form = self._find_inflected_form_in_sentences(word_data.get('example_sentences', []), word)
                        
                        if inflected_form:
                            self.update_signal.emit(f"Single word processing: found inflected form '{inflected_form}' for '{word}' - using consistently")
                            word_data['word'] = inflected_form
                            word_data['original_word'] = inflected_form  # Use inflected form for audio download
                            word_data['inflected_form_used'] = True
                            self._merge_ordnet_data_and_set_defaults(word_data, inflected_form)
                            word_data_list.append(word_data)
                            
                            if word_data.get('english_translation'):
                                word_translations[inflected_form] = word_data['english_translation'].lower().strip()
                        else:
                            self.update_signal.emit(f"Single word processing: insufficient valid sentences for '{word}'")
                            error_data = self._create_error_word_data(word, 'Could not generate valid sentences containing the exact word or inflected forms')
                            word_data_list.append(error_data)
                    else:
                        word_data['example_sentences'] = validated_sentences
                        word_data['original_word'] = word
                        self._merge_ordnet_data_and_set_defaults(word_data, word)
                        word_data_list.append(word_data)
                        
                        if word_data.get('english_translation'):
                            word_translations[word] = word_data['english_translation'].lower().strip()
                else:
                    error_data = self._create_error_word_data(word, 'Could not get correct word after retry')
                    word_data_list.append(error_data)
            else:
                error_data = self._create_error_word_data(word, 'Could not parse response')
                word_data_list.append(error_data)
                
        except Exception as e:
            error_data = self._create_error_word_data(word, f'Error processing word: {str(e)}')
            word_data_list.append(error_data)
        
        return word_data_list, word_translations
    
    def _clean_english_translation(self, translation: str) -> str:
        """Clean English translation to ensure single base word form."""
        if not translation:
            return ""
        
        # Remove "(base word: ...)" pattern if present
        cleaned = re.sub(r'\s*\(base word:.*?\).*', '', translation, flags=re.IGNORECASE)
        # Remove "dictionary form" if present  
        cleaned = re.sub(r'\s*dictionary form\s*', '', cleaned, flags=re.IGNORECASE)
        # Remove articles and prepositions at the beginning
        cleaned = re.sub(r'^(the|a|an|to)\s+', '', cleaned, flags=re.IGNORECASE)
        # Remove common prepositions that might appear
        cleaned = re.sub(r'^(in|on|at|by|for|with|of)\s+', '', cleaned, flags=re.IGNORECASE)
        # Remove any trailing punctuation
        cleaned = re.sub(r'[.,!?;:]+$', '', cleaned)
        # Clean up multiple spaces and trim
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _merge_ordnet_data_and_set_defaults(self, word_data: Dict, original_word: str) -> None:
        """Merge Ordnet data with word_data and set default values for missing fields."""
        # Merge with Ordnet data if available
        if original_word in self.ordnet_data:
            ordnet_info = self.ordnet_data[original_word]
            # Use Ordnet data for definitions and grammar, but keep ChatGPT sentences
            if ordnet_info.get('danish_definition'):
                word_data['danish_definition'] = ordnet_info['danish_definition']
            if ordnet_info.get('pronunciation'):
                word_data['pronunciation'] = ordnet_info['pronunciation']
            if ordnet_info.get('word_type'):
                word_data['word_type'] = ordnet_info['word_type']
            if ordnet_info.get('gender'):
                word_data['gender'] = ordnet_info['gender']
            if ordnet_info.get('plural'):
                word_data['plural'] = ordnet_info['plural']
            if ordnet_info.get('inflections'):
                word_data['inflections'] = ordnet_info['inflections']
            # Use ChatGPT for English translation if Ordnet doesn't have it
            if not word_data.get('english_translation') and ordnet_info.get('english_translation'):
                word_data['english_translation'] = ordnet_info['english_translation']
        
        # Set default values for missing fields
        word_data.setdefault('pronunciation', '')
        word_data.setdefault('word_type', '')
        word_data.setdefault('gender', '')
        word_data.setdefault('plural', '')
        word_data.setdefault('inflections', '')
        word_data.setdefault('danish_definition', '')
        word_data.setdefault('english_translation', '')
    
    def _create_error_word_data(self, word: str, error_message: str) -> Dict:
        """Create error data structure for a word with Ordnet data if available."""
        error_data = {
            'word': word,
            'original_word': word,
            'error': error_message,
            'pronunciation': '',
            'word_type': '',
            'gender': '',
            'plural': '',
            'inflections': '',
            'danish_definition': '',
            'english_translation': '',
            'example_sentences': []
        }
        
        # Add Ordnet data if available
        if word in self.ordnet_data:
            ordnet_info = self.ordnet_data[word]
            if ordnet_info.get('danish_definition'):
                error_data['danish_definition'] = ordnet_info['danish_definition']
            if ordnet_info.get('pronunciation'):
                error_data['pronunciation'] = ordnet_info['pronunciation']
            if ordnet_info.get('word_type'):
                error_data['word_type'] = ordnet_info['word_type']
            if ordnet_info.get('gender'):
                error_data['gender'] = ordnet_info['gender']
            if ordnet_info.get('plural'):
                error_data['plural'] = ordnet_info['plural']
            if ordnet_info.get('inflections'):
                error_data['inflections'] = ordnet_info['inflections']
            if ordnet_info.get('english_translation'):
                error_data['english_translation'] = ordnet_info['english_translation']
            # Update error message if we have good Ordnet data
            if ordnet_info.get('ordnet_found'):
                error_data['error'] = f'{error_message}, but dictionary data available'
        
        return error_data
    
    def _validate_sentences_contain_word(self, sentences, target_word):
        """Validate that sentences actually contain the target word (exact match or inflected form)."""
        valid_sentences = []
        target_word_lower = target_word.lower()
        
        for sentence_data in sentences:
            if isinstance(sentence_data, dict) and sentence_data.get('danish'):
                danish_sentence = sentence_data['danish'].lower()
                # Check for exact word match with word boundaries
                pattern = r'\b' + re.escape(target_word_lower) + r'\b'
                if re.search(pattern, danish_sentence):
                    valid_sentences.append(sentence_data)
        
        # Only log if there are validation issues
        if len(valid_sentences) < len(sentences):
            invalid_count = len(sentences) - len(valid_sentences)
            self.update_signal.emit(f"Validation: {invalid_count}/{len(sentences)} sentences for '{target_word}' don't contain the word")
        
        return valid_sentences
    
    def _find_inflected_form_in_sentences(self, sentences, base_word):
        """Find what inflected form of the word is actually used in the sentences."""
        base_word_lower = base_word.lower()
        
        # First, check if the base word itself appears in the sentences
        for sentence_data in sentences:
            if isinstance(sentence_data, dict) and sentence_data.get('danish'):
                danish_sentence = sentence_data['danish'].lower()
                # Check for exact base word match with word boundaries
                base_pattern = r'\b' + re.escape(base_word_lower) + r'\b'
                if re.search(base_pattern, danish_sentence):
                    # Base word found, no need to look for inflected forms
                    return None
        
        # Only look for inflected forms if base word is NOT found
        # Common Danish inflections to try
        danish_inflections = [
            base_word_lower + 'en',    # definite form (-en)
            base_word_lower + 'et',    # definite form (-et) 
            base_word_lower + 'erne',  # definite plural (-erne)
            base_word_lower + 'ne',    # definite plural (-ne)
            base_word_lower + 'er',    # plural/present tense (-er)
            base_word_lower + 'ed',    # past tense (-ed)
            base_word_lower + 'ede',   # past tense definite (-ede)
            base_word_lower + 't',     # past participle (-t)
            base_word_lower + 'te',    # past participle definite (-te)
            base_word_lower + 's',     # genitive (-s)
        ]
        
        # Special handling for verbs ending in 'e' - don't add another 'e'
        if base_word_lower.endswith('e'):
            # For verbs ending in 'e', remove the redundant 'e' inflection
            danish_inflections = [infl for infl in danish_inflections if infl != base_word_lower + 'e']
        
        for sentence_data in sentences:
            if isinstance(sentence_data, dict) and sentence_data.get('danish'):
                danish_sentence = sentence_data['danish'].lower()
                
                # Check each possible inflection
                for inflected_form in danish_inflections:
                    pattern = r'\b' + re.escape(inflected_form) + r'\b'
                    if re.search(pattern, danish_sentence):
                        # Found an inflected form - extract the actual form from the sentence
                        words = danish_sentence.split()
                        for word in words:
                            # Clean punctuation and check if it matches our inflected form
                            clean_word = re.sub(r'[.,!?;:"]', '', word.lower())
                            if clean_word == inflected_form:
                                # Return the original case version from the sentence
                                original_word = re.sub(r'[.,!?;:"]', '', word)
                                return original_word
        
        return None
    
    def _retry_with_inflected_forms(self, client, base_word):
        """Retry with common Danish inflected forms when base form doesn't work."""
        base_word_lower = base_word.lower()
        
        # Try common Danish inflections, but be smart about verbs ending in 'e'
        inflections_to_try = [
            base_word_lower + 'en',    # definite form (-en)
            base_word_lower + 'et',    # definite form (-et)
            base_word_lower + 'erne',  # definite plural (-erne)
            base_word_lower + 'ne',    # definite plural (-ne)
            base_word_lower + 'er',    # plural/present tense (-er)
        ]
        
        # Special handling for verbs ending in 'e' - don't add another 'e'
        if not base_word_lower.endswith('e'):
            inflections_to_try.append(base_word_lower + 'e')  # plural/imperative (-e)
        
        for inflected_form in inflections_to_try:
            self.update_signal.emit(f"Trying inflected form: '{inflected_form}'")
            
            retry_prompt = f"""Create exactly 2 Danish sentences using the word "{inflected_form}".

The word to use is: "{inflected_form}"

REQUIREMENTS:
- Each sentence MUST contain "{inflected_form}" EXACTLY as written
- Do NOT change this word to any other form
- Return the word field as "{inflected_form}"
- Provide English translation as single base word (infinitive for verbs, singular for nouns)

Return ONLY this JSON format:
{{
    "word": "{inflected_form}",
    "english_translation": "baseword",
    "example_sentences": [
        {{
            "danish": "First sentence containing {inflected_form}",
            "english": "English translation"
        }},
        {{
            "danish": "Second sentence containing {inflected_form}",
            "english": "English translation"  
        }}
    ]
}}"""

            try:
                response = client.chat.completions.create(
                    model=AppConfig.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a Danish language teacher. Use the EXACT word provided. Return ONLY valid JSON."},
                        {"role": "user", "content": retry_prompt}
                    ],
                    max_completion_tokens=AppConfig.OPENAI_MAX_TOKENS
                )
                
                json_content = response.choices[0].message.content.strip()
                result = self._parse_response(json_content)
                
                if result:
                    # Validate that sentences contain the inflected form
                    validated_sentences = self._validate_sentences_contain_word(result.get('example_sentences', []), inflected_form)
                    if len(validated_sentences) >= 2:
                        result['example_sentences'] = validated_sentences
                        result['inflected_form_used'] = True
                        result['base_word'] = base_word
                        
                        # Clean up the English translation - remove any extra text added by the prompt
                        if result.get('english_translation'):
                            result['english_translation'] = self._clean_english_translation(result['english_translation'])
                        
                        self.update_signal.emit(f"Successfully created sentences with inflected form '{inflected_form}'")
                        return result
                
            except Exception as e:
                self.update_signal.emit(f"Failed to try inflected form '{inflected_form}': {str(e)}")
                continue
        
        return None

    def _retry_with_word_emphasis(self, client, word):
        """Retry with extra emphasis on using the exact word when AI returned wrong word."""
        retry_prompt = f"""CRITICAL: You MUST use the EXACT word "{word}" - nothing else!

The word is: "{word}"

You previously returned a different word, but I need sentences with EXACTLY "{word}".

Create exactly 2 Danish sentences that contain the literal word "{word}" as written.

REQUIREMENTS:
- Each sentence MUST contain "{word}" EXACTLY as written
- Do NOT change the word to any other form
- Do NOT use synonyms or similar words
- The word "{word}" must appear exactly as provided
- Return the word field as "{word}" (exact match)

Return ONLY this JSON format:
{{
    "word": "{word}",
    "english_translation": "baseword",
    "example_sentences": [
        {{
            "danish": "First sentence containing {word}",
            "english": "English translation"
        }},
        {{
            "danish": "Second sentence containing {word}",
            "english": "English translation"  
        }}
    ]
}}

MANDATORY: Use "{word}" exactly - no variations, no inflections unless that IS the exact word provided."""

        try:
            response = client.chat.completions.create(
                model=AppConfig.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a Danish language teacher. You MUST use the EXACT word provided - no substitutions, no variations. Return ONLY valid JSON. The word field in your response must match exactly what was requested. English translation must be a single base word without articles or prepositions."},
                    {"role": "user", "content": retry_prompt}
                ],
                max_completion_tokens=AppConfig.OPENAI_MAX_TOKENS
            )
            
            json_content = response.choices[0].message.content.strip()
            result = self._parse_response(json_content)
            
            # Clean the English translation
            if result and result.get('english_translation'):
                result['english_translation'] = self._clean_english_translation(result['english_translation'])
            
            # Double-check that the returned word matches what we requested
            if result and result.get('word', '').lower().strip() != word.lower().strip():
                self.update_signal.emit(f"Retry still returned wrong word: got '{result.get('word', '')}' instead of '{word}'")
                return None
                
            return result
            
        except Exception as e:
            self.update_signal.emit(f"Word emphasis retry failed for '{word}': {str(e)}")
            return None

    def _retry_sentence_generation(self, client, word):
        """Retry sentence generation with a more specific prompt for a single word."""
        retry_prompt = f"""The word is "{word}". Create exactly 2 Danish sentences that contain the EXACT word "{word}".

CRITICAL REQUIREMENT: Each sentence MUST contain the literal word "{word}" exactly as written. 
Do not use any other form - use "{word}" and only "{word}".

Return ONLY this JSON format:
{{
    "word": "{word}",
    "english_translation": "baseword",
    "example_sentences": [
        {{
            "danish": "First sentence with {word}",
            "english": "English translation"
        }},
        {{
            "danish": "Second sentence with {word}",
            "english": "English translation"  
        }}
    ]
}}

MANDATORY: The word "{word}" must appear exactly as written in each Danish sentence."""

        try:
            response = client.chat.completions.create(
                model=AppConfig.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a Danish language teacher. You MUST use the exact word provided. Return ONLY valid JSON. English translation must be a single base word without articles or prepositions."},
                    {"role": "user", "content": retry_prompt}
                ],
                max_completion_tokens=AppConfig.OPENAI_MAX_TOKENS
            )
            
            json_content = response.choices[0].message.content.strip()
            result = self._parse_response(json_content)
            
            # Clean the English translation
            if result and result.get('english_translation'):
                result['english_translation'] = self._clean_english_translation(result['english_translation'])
            
            return result
            
        except Exception as e:
            self.update_signal.emit(f"Retry failed for '{word}': {str(e)}")
            return None

    def _parse_batch_response(self, json_content: str):
        """Parse the JSON response from ChatGPT for batch processing with simplified error handling."""
        try:
            # Check for empty content first
            if not json_content or json_content.isspace():
                self.update_signal.emit("Error: Empty or whitespace-only response content")
                return None
            
            # Remove any markdown formatting if present
            content = json_content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Check again after cleaning
            if not content:
                self.update_signal.emit("Error: Content became empty after cleaning markdown")
                return None
            
            # Simple fix for common escaped quote issues
            content = content.replace('\\"', '"')
            
            parsed_data = json.loads(content)
            
            # Validate the structure
            if not isinstance(parsed_data, dict):
                self.update_signal.emit(f"Error: Invalid JSON structure - expected dict, got {type(parsed_data)}")
                return None
            
            if 'words' not in parsed_data:
                self.update_signal.emit(f"Error: Missing 'words' key in response. Keys found: {list(parsed_data.keys())}")
                return None
            
            if not isinstance(parsed_data['words'], list):
                self.update_signal.emit(f"Error: Invalid 'words' structure - expected list, got {type(parsed_data['words'])}")
                return None
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            self.update_signal.emit(f"JSON parsing error at position {e.pos}: {str(e)}")
            if hasattr(e, 'pos') and e.pos < len(json_content):
                self.update_signal.emit(f"Content around error: ...{json_content[max(0, e.pos-50):e.pos+50]}...")
            return None
        except Exception as e:
            self.update_signal.emit(f"Error parsing batch response: {str(e)}")
            return None
    
    def _parse_response(self, json_content: str) -> Optional[Dict]:
        """Parse the JSON response from ChatGPT."""
        try:
            # Remove any markdown formatting if present
            content = json_content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            return json.loads(content)
        except json.JSONDecodeError as e:
            self.update_signal.emit(f"JSON parsing error: {str(e)}")
            return None
        except Exception as e:
            self.update_signal.emit(f"Error parsing response: {str(e)}")
            return None

    def _format_word_data(self, word_data: Dict) -> str:
        """Format the parsed word data for display."""
        word = word_data.get('word', 'Unknown')
        word_type = word_data.get('word_type', '').lower()
        
        # Build grammar info section
        grammar_parts = []
        if word_data.get('pronunciation'):
            grammar_parts.append(f"IPA: {word_data['pronunciation']}")
        if word_data.get('word_type'):
            grammar_parts.append(f"Type: {word_data['word_type']}")
        
        # Add type-specific information
        if word_type in ['substantiv', 'noun']:
            # For nouns: include gender and plural
            if word_data.get('gender') and word_data['gender'].lower() != 'null':
                grammar_parts.append(f"Gender: {word_data['gender']}")
            if word_data.get('plural') and word_data['plural'].lower() != 'null':
                grammar_parts.append(f"Plural: {word_data['plural']}")
        elif word_type in ['verbum', 'verb']:
            # For verbs: include inflections as "bøjning"
            if word_data.get('inflections') and word_data['inflections'].lower() != 'null':
                grammar_parts.append(f"Bøjning: {word_data['inflections']}")
        elif word_type in ['adjektiv', 'adjective']:
            # For adjectives: include comparative/superlative forms
            if word_data.get('inflections') and word_data['inflections'].lower() != 'null':
                grammar_parts.append(f"Bøjning: {word_data['inflections']}")
        else:
            # For other word types: include inflections if available
            if word_data.get('inflections') and word_data['inflections'].lower() != 'null':
                grammar_parts.append(f"Inflections: {word_data['inflections']}")
        
        if word_data.get('danish_definition'):
            grammar_parts.append(f"Definition: {word_data['danish_definition']}")
        if word_data.get('english_translation'):
            grammar_parts.append(f"English word: {word_data['english_translation']}")
        
        grammar_info = '\n'.join(grammar_parts)
        
        # Build example sentences section
        sentences = []
        example_sentences = word_data.get('example_sentences', [])
        for i, sentence in enumerate(example_sentences, 1):
            if isinstance(sentence, dict) and 'danish' in sentence and 'english' in sentence:
                sentences.append(f"{i}. {sentence['danish']} - {sentence['english']}")
        
        example_section = '\n'.join(sentences)
        
        # Combine everything
        formatted = f"**{word}**\n\n**Grammar Info:**\n{grammar_info}\n\n**Example Sentences:**\n{example_section}\n\n---"
        
        return formatted

    def abort(self) -> None:
        """Abort the sentence generation process."""
        self.abort_flag = True
        self.update_signal.emit("Aborting sentence generation...")
