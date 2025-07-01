"""
Worker thread for generating example sentences using ChatGPT.
"""

import time
import json
from typing import List, Dict, Optional
from PyQt5.QtCore import QThread, pyqtSignal
import openai

from ..utils.config import AppConfig


class SentenceWorker(QThread):
    """Worker thread for generating example sentences using ChatGPT."""
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(list, dict)  # word_data_list, word_translations
    error_signal = pyqtSignal(str)  # error message

    def __init__(self, words: List[str], cefr_level: str, api_key: str) -> None:
        super().__init__()
        self.words = words
        self.cefr_level = cefr_level
        self.api_key = api_key
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
            
            # Choose processing method based on word count
            if total_words <= AppConfig.BATCH_THRESHOLD:  # Use batch processing for smaller lists
                self.update_signal.emit("Using batch processing for optimal speed...")
                word_data_list, word_translations = self._process_words_batch(client, self.words)
            else:
                # For very large lists, process in chunks to avoid token limits
                self.update_signal.emit("Processing in optimized chunks...")
                chunk_size = AppConfig.BATCH_SIZE  # Process words in configurable chunks
                for i in range(0, total_words, chunk_size):
                    if self.abort_flag:
                        self.update_signal.emit("Sentence generation aborted by user")
                        break
                    
                    chunk = self.words[i:i + chunk_size]
                    chunk_start = i + 1
                    chunk_end = min(i + chunk_size, total_words)
                    
                    self.update_signal.emit(f"Processing words {chunk_start}-{chunk_end} of {total_words}...")
                    self.progress_signal.emit(chunk_end, total_words)
                    
                    chunk_data, chunk_translations = self._process_words_batch(client, chunk)
                    word_data_list.extend(chunk_data)
                    word_translations.update(chunk_translations)
                    
                    # Small delay between chunks only
                    if i + chunk_size < total_words:
                        time.sleep(0.5)  # Much shorter delay between chunks
            
            if not self.abort_flag:
                # Final memory cleanup before emitting results
                import gc
                collected = gc.collect()
                self.update_signal.emit(f"Final memory cleanup: freed {collected} objects")
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
        
        prompt = f"""For the Danish words [{words_json}], please provide detailed language information and example sentences for each word.

Return your response as valid JSON in this exact format:
{{
    "words": [
        {{
            "word": "word1",
            "pronunciation": "/pronunciation/",
            "word_type": "substantiv|verbum|adjektiv|etc",
            "gender": "en|et|null",
            "plural": "plural form or null",
            "inflections": "other forms, declensions, conjugations",
            "danish_definition": "brief Danish definition",
            "english_translation": "main English translation (single word, base form)",
            "example_sentences": [
                {{
                    "danish": "Danish sentence using word1",
                    "english": "English translation"
                }},
                {{
                    "danish": "Danish sentence using word1",
                    "english": "English translation"
                }},
                {{
                    "danish": "Danish sentence using word1",
                    "english": "English translation"
                }}
            ]
        }},
        {{
            "word": "word2",
            "pronunciation": "/pronunciation/",
            "word_type": "substantiv|verbum|adjektiv|etc",
            "gender": "en|et|null",
            "plural": "plural form or null",
            "inflections": "other forms, declensions, conjugations",
            "danish_definition": "brief Danish definition",
            "english_translation": "main English translation (single word, base form)",
            "example_sentences": [
                {{
                    "danish": "Danish sentence using word2",
                    "english": "English translation"
                }},
                {{
                    "danish": "Danish sentence using word2",
                    "english": "English translation"
                }},
                {{
                    "danish": "Danish sentence using word2",
                    "english": "English translation"
                }}
            ]
        }}
    ]
}}

Requirements:
- Use the exact word in each Danish sentence (not inflected forms)
- Make sentences appropriate for {self.cefr_level} level
- Provide 3 different example sentences per word showing different contexts/uses
- Return ONLY valid JSON, no additional text or formatting
- Process all {len(words_batch)} words in the response"""
        
        try:
            # Make single API call for all words in batch
            response = client.chat.completions.create(
                model=AppConfig.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful Danish language teacher. Always respond with valid JSON only, no additional text or formatting. Process multiple words efficiently in a single response."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=AppConfig.OPENAI_MAX_TOKENS * 2,  # Increase token limit for batch processing
                temperature=AppConfig.OPENAI_TEMPERATURE
            )
            
            # Parse JSON response
            json_content = response.choices[0].message.content.strip()
            batch_data = self._parse_batch_response(json_content)
            
            if batch_data and 'words' in batch_data:
                for word_data in batch_data['words']:
                    if word_data.get('word'):
                        word_data_list.append(word_data)
                        
                        # Store English translation for image fetching
                        if word_data.get('english_translation'):
                            word_translations[word_data['word']] = word_data['english_translation'].lower().strip()
                    
                self.update_signal.emit(f"Successfully processed {len(word_data_list)} words in batch")
            else:
                # Fallback to individual processing if batch fails
                self.update_signal.emit("Batch processing failed, falling back to individual requests...")
                return self._process_words_individually(client, words_batch)
                
        except Exception as e:
            self.update_signal.emit(f"Batch processing error: {str(e)}, falling back to individual requests...")
            return self._process_words_individually(client, words_batch)
        
        return word_data_list, word_translations

    def _parse_batch_response(self, json_content: str):
        """Parse the JSON response from ChatGPT for batch processing."""
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
            self.update_signal.emit(f"Batch JSON parsing error: {str(e)}")
            return None
        except Exception as e:
            self.update_signal.emit(f"Error parsing batch response: {str(e)}")
            return None

    def _process_words_individually(self, client, words_batch):
        """Fallback method: process words individually (original implementation)."""
        word_data_list = []
        word_translations = {}
        
        for i, word in enumerate(words_batch):
            if self.abort_flag:
                break
                
            self.update_signal.emit(f"Individual processing: {word} ({i+1}/{len(words_batch)})")
            
            # Create the prompt for structured JSON response (original individual logic)
            prompt = f"""For the Danish word "{word}", please provide detailed language information and example sentences.

Return your response as valid JSON in this exact format:
{{
    "word": "{word}",
    "pronunciation": "/pronunciation/",
    "word_type": "substantiv|verbum|adjektiv|etc",
    "gender": "en|et|null",
    "plural": "plural form or null",
    "inflections": "other forms, declensions, conjugations",
    "danish_definition": "brief Danish definition",
    "english_translation": "main English translation, it should be a single word. If the word has multiple meanings, provide the most common one. If the word is plural, provide the singular form. Be sure to always use the base form of the word.",
    "example_sentences": [
        {{
            "danish": "Danish sentence using {word}",
            "english": "English translation"
        }},
        {{
            "danish": "Danish sentence using {word}",
            "english": "English translation"
        }},
        {{
            "danish": "Danish sentence using {word}",
            "english": "English translation"
        }}
    ]
}}

Requirements:
- Use the exact word "{word}" in each Danish sentence (not inflected forms)
- Make sentences appropriate for {self.cefr_level} level
- Provide 3 different example sentences showing different contexts/uses
- Return ONLY valid JSON, no additional text or formatting"""
            
            try:
                # Make API call
                response = client.chat.completions.create(
                    model=AppConfig.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a helpful Danish language teacher. Always respond with valid JSON only, no additional text or formatting."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=AppConfig.OPENAI_MAX_TOKENS,
                    temperature=AppConfig.OPENAI_TEMPERATURE
                )
                
                # Parse JSON response
                json_content = response.choices[0].message.content.strip()
                word_data = self._parse_response(json_content)
                
                if word_data:
                    # Store the structured data directly
                    word_data_list.append(word_data)
                    
                    # Store English translation for image fetching
                    if word_data.get('english_translation'):
                        word_translations[word] = word_data['english_translation'].lower().strip()
                else:
                    # Fallback with error data structure
                    error_data = {
                        'word': word,
                        'error': 'Could not parse response for this word',
                        'pronunciation': '',
                        'word_type': '',
                        'gender': '',
                        'plural': '',
                        'inflections': '',
                        'danish_definition': '',
                        'english_translation': '',
                        'example_sentences': []
                    }
                    word_data_list.append(error_data)
                
                # Add a small delay to respect rate limits
                time.sleep(AppConfig.REQUEST_DELAY)
                
            except Exception as e:
                error_msg = f"Error generating sentences for '{word}': {str(e)}"
                self.update_signal.emit(error_msg)
                # Add error data structure
                error_data = {
                    'word': word,
                    'error': f'Could not generate sentences for this word: {str(e)}',
                    'pronunciation': '',
                    'word_type': '',
                    'gender': '',
                    'plural': '',
                    'inflections': '',
                    'danish_definition': '',
                    'english_translation': '',
                    'example_sentences': []
                }
                word_data_list.append(error_data)
        
        return word_data_list, word_translations

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
