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

CRITICAL: Each sentence MUST contain the EXACT word as written - do not change its form or inflection.

Use this EXACT format:
{{
    "words": [
        {{
            "word": "word1",
            "english_translation": "dictionary form (infinitive for verbs, singular for nouns)",
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
- MANDATORY: Use each exact word as provided in the Danish sentences - do not change spelling, inflection, or form
- If a word is inflected (like "rejser"), use that exact inflected form in the sentence
- If a word is a base form (like "rejse"), use that exact base form in the sentence  
- CEFR level: {self.cefr_level}
- 2 example sentences per word
- Focus on creating natural example sentences that properly use the given word forms
- English translation MUST be the dictionary form (infinitive for verbs, singular for nouns)
- For verbs, use the infinitive form WITHOUT "to" (e.g., "talk" not "talked/talking/talks", "eat" not "ate/eating/eats")
- For nouns, use singular form (e.g., "cat" not "cats", "house" not "houses")
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
                    {"role": "system", "content": "You are a Danish language teacher specializing in creating natural example sentences. Return ONLY valid JSON. NEVER use backslash-quote (\\\" ) in JSON values. Use normal quotes in Danish text. Focus on creating clear, contextual sentences that demonstrate word usage. For English translations, always use the dictionary form: infinitive for verbs (e.g., 'talk' not 'talked'), singular for nouns (e.g., 'cat' not 'cats')."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=token_limit
            )
            
            # Parse JSON response
            json_content = response.choices[0].message.content.strip()
            
            # Log the raw response for debugging (first 500 chars)
            self.update_signal.emit(f"Raw API response preview: {json_content[:500]}...")
            
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
                        
                        # VALIDATE: Check if sentences actually contain the user's word
                        validated_sentences = self._validate_sentences_contain_word(word_data.get('example_sentences', []), original_word)
                        
                        if len(validated_sentences) < 2:  # Need at least 2 valid sentences
                            self.update_signal.emit(f"Batch result for '{original_word}' doesn't contain the word, will retry individually...")
                            # For batch processing, we'll mark this word for individual retry later
                            word_data['needs_retry'] = True
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
                    self.update_signal.emit(f"Retrying {len(retry_words)} words individually due to validation failures...")
                    for word_data in retry_words:
                        original_word = word_data['original_word']
                        self.update_signal.emit(f"Retrying individual sentence generation for '{original_word}'...")
                        retry_result = self._retry_sentence_generation(client, original_word)
                        if retry_result and len(self._validate_sentences_contain_word(retry_result.get('example_sentences', []), original_word)) >= 2:
                            # Update the word_data with the new sentences
                            word_data['example_sentences'] = retry_result['example_sentences']
                            if retry_result.get('english_translation'):
                                word_data['english_translation'] = retry_result['english_translation']
                            word_data['needs_retry'] = False  # Mark as resolved
                            self.update_signal.emit(f"Successfully generated valid sentences for '{original_word}' on individual retry")
                        else:
                            self.update_signal.emit(f"Warning: Could not generate valid sentences for '{original_word}' even on individual retry")
                
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
                        self.update_signal.emit(f"Individual processing successful for '{word}'")
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
    "english_translation": "dictionary form",
    "example_sentences": [
        {{"danish": "Sentence with {word}", "english": "English translation"}},
        {{"danish": "Another sentence with {word}", "english": "English translation"}}
    ]
}}"""
        
        try:
            response = client.chat.completions.create(
                model=AppConfig.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Return ONLY valid JSON. Use exact word forms as provided."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=AppConfig.OPENAI_MAX_TOKENS
            )
            
            json_content = response.choices[0].message.content.strip()
            word_data = self._parse_response(json_content)
            
            if word_data:
                word_data['original_word'] = word
                self._merge_ordnet_data_and_set_defaults(word_data, word)
                word_data_list.append(word_data)
                
                if word_data.get('english_translation'):
                    word_translations[word] = word_data['english_translation'].lower().strip()
            else:
                error_data = self._create_error_word_data(word, 'Could not parse response')
                word_data_list.append(error_data)
                
        except Exception as e:
            error_data = self._create_error_word_data(word, f'Error processing word: {str(e)}')
            word_data_list.append(error_data)
        
        return word_data_list, word_translations
    
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
        """Validate that sentences actually contain the target word (exact match)."""
        valid_sentences = []
        target_word_lower = target_word.lower()
        
        for sentence_data in sentences:
            if isinstance(sentence_data, dict) and sentence_data.get('danish'):
                danish_sentence = sentence_data['danish'].lower()
                # Check for exact word match with word boundaries
                pattern = r'\b' + re.escape(target_word_lower) + r'\b'
                if re.search(pattern, danish_sentence):
                    valid_sentences.append(sentence_data)
        
        return valid_sentences
    
    def _retry_sentence_generation(self, client, word):
        """Retry sentence generation with a more specific prompt for a single word."""
        retry_prompt = f"""The word is "{word}". Create exactly 2 Danish sentences that contain the EXACT word "{word}".

CRITICAL REQUIREMENT: Each sentence MUST contain the literal word "{word}" exactly as written. 
Do not use any other form - use "{word}" and only "{word}".

Return ONLY this JSON format:
{{
    "word": "{word}",
    "english_translation": "dictionary form",
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
                    {"role": "system", "content": "You are a Danish language teacher. You MUST use the exact word provided. Return ONLY valid JSON."},
                    {"role": "user", "content": retry_prompt}
                ],
                max_completion_tokens=AppConfig.OPENAI_MAX_TOKENS
            )
            
            json_content = response.choices[0].message.content.strip()
            return self._parse_response(json_content)
            
        except Exception as e:
            self.update_signal.emit(f"Retry failed for '{word}': {str(e)}")
            return None

    def _parse_batch_response(self, json_content: str):
        """Parse the JSON response from ChatGPT for batch processing with simplified error handling."""
        try:
            # Remove any markdown formatting if present
            content = json_content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Simple fix for common escaped quote issues
            content = content.replace('\\"', '"')
            
            # Log the cleaned content for debugging
            self.update_signal.emit(f"Attempting to parse cleaned JSON (first 200 chars): {content[:200]}...")
            
            parsed_data = json.loads(content)
            
            # Validate the structure
            if not isinstance(parsed_data, dict):
                self.update_signal.emit(f"Invalid JSON structure: expected dict, got {type(parsed_data)}")
                return None
            
            if 'words' not in parsed_data:
                self.update_signal.emit(f"Missing 'words' key in response. Keys found: {list(parsed_data.keys())}")
                return None
            
            if not isinstance(parsed_data['words'], list):
                self.update_signal.emit(f"Invalid 'words' structure: expected list, got {type(parsed_data['words'])}")
                return None
            
            self.update_signal.emit(f"Successfully parsed JSON with {len(parsed_data['words'])} word entries")
            return parsed_data
            
        except json.JSONDecodeError as e:
            self.update_signal.emit(f"JSON parsing error at position {e.pos}: {str(e)}")
            self.update_signal.emit(f"Content around error: ...{json_content[max(0, e.pos-50):e.pos+50]}...")
            return None
        except Exception as e:
            self.update_signal.emit(f"Error parsing batch response: {str(e)}")
            self.update_signal.emit(f"Raw content length: {len(json_content)} characters")
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
