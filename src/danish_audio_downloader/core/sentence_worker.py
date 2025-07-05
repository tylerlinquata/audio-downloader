"""
Worker thread for generating example sentences using ChatGPT.
"""

import time
import json
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
        
        prompt = f"""For the Danish words [{words_json}], provide detailed language information and example sentences.

CRITICAL: Return ONLY valid JSON. No escaping quotes - use normal quotes in Danish text.

Use this EXACT format:
{{
    "words": [
        {{
            "word": "word1",
            "pronunciation": "/pronunciation/",
            "word_type": "substantiv",
            "gender": "en",
            "plural": "plural form",
            "inflections": "other forms",
            "danish_definition": "Danish definition",
            "english_translation": "single English word",
            "example_sentences": [
                {{
                    "danish": "Danish sentence with normal quotes",
                    "english": "English translation"
                }},
                {{
                    "danish": "Another Danish sentence",
                    "english": "English translation"
                }},
                {{
                    "danish": "Third Danish sentence",
                    "english": "English translation"
                }}
            ]
        }}
    ]
}}

Requirements:
- Use exact word in Danish sentences
- CEFR level: {self.cefr_level}
- 3 example sentences per word
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
                    {"role": "system", "content": "You are a Danish language teacher. Return ONLY valid JSON. NEVER use backslash-quote (\\\" ) in JSON values. Use normal quotes in Danish text. Follow JSON syntax exactly."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=token_limit,
                temperature=AppConfig.OPENAI_TEMPERATURE
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
                        
                        word_data_list.append(word_data)
                        processed_count += 1
                        
                        # Store English translation for image fetching using original word
                        original_word = word_data['original_word']
                        if word_data.get('english_translation'):
                            word_translations[original_word] = word_data['english_translation'].lower().strip()
                    
                self.update_signal.emit(f"Successfully processed {processed_count} words in batch (requested {len(words_batch)})")
                
                # If we got fewer words than expected, warn but continue
                if processed_count < len(words_batch):
                    missing_count = len(words_batch) - processed_count
                    self.update_signal.emit(f"Warning: {missing_count} words may not have been processed correctly")
                    
            else:
                # Fallback to individual processing if batch fails
                self.update_signal.emit("Batch processing failed, falling back to individual requests...")
                return self._process_words_individually(client, words_batch)
                
        except openai.RateLimitError as e:
            self.update_signal.emit(f"Rate limit exceeded: {str(e)}. Falling back to individual processing...")
            return self._process_words_individually(client, words_batch)
        except openai.APIError as e:
            self.update_signal.emit(f"OpenAI API error: {str(e)}. Falling back to individual processing...")
            return self._process_words_individually(client, words_batch)
        except Exception as e:
            self.update_signal.emit(f"Batch processing error: {str(e)}, falling back to individual requests...")
            return self._process_words_individually(client, words_batch)
        
        return word_data_list, word_translations

    def _parse_batch_response(self, json_content: str):
        """Parse the JSON response from ChatGPT for batch processing with robust error handling."""
        try:
            # Remove any markdown formatting if present
            content = json_content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Try to fix common JSON issues
            content = self._fix_common_json_issues(content)
            
            return json.loads(content)
        except json.JSONDecodeError as e:
            self.update_signal.emit(f"Batch JSON parsing error: {str(e)}")
            # Try to extract partial valid JSON
            return self._attempt_partial_json_recovery(content)
        except Exception as e:
            self.update_signal.emit(f"Error parsing batch response: {str(e)}")
            return None
    
    def _fix_common_json_issues(self, content: str) -> str:
        """Fix common JSON formatting issues that occur with large responses."""
        import re
        
        # Fix the main issue: incorrectly escaped quotes in values
        # Replace \" with " inside string values (but not at the start/end of strings)
        content = re.sub(r'(?<=[a-zA-ZæøåÆØÅ\s])\\"(?=[a-zA-ZæøåÆØÅ\s])', '"', content)
        
        # Fix trailing commas before closing brackets/braces
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        
        # More specific fix for the Danish quote issue
        # Find patterns like "danish": \"text with quotes\"
        # and fix them to "danish": "text with quotes"
        def fix_danish_quotes(match):
            key = match.group(1)
            value_content = match.group(2)
            # Unescape the quotes in the value content
            fixed_value = value_content.replace('\\"', '"')
            return f'"{key}": "{fixed_value}"'
        
        # Pattern to match key-value pairs with escaped quotes in values
        pattern = r'"(danish|english)"\s*:\s*\\"([^"]*(?:\\"[^"]*)*)\\"'
        content = re.sub(pattern, fix_danish_quotes, content)
        
        return content
    
    def _attempt_partial_json_recovery(self, content: str):
        """Attempt to recover partial valid JSON from malformed response."""
        try:
            # First, try the simpler fix for the escaped quotes issue
            fixed_content = self._fix_escaped_quotes_issue(content)
            if fixed_content:
                try:
                    return json.loads(fixed_content)
                except:
                    pass
            
            # If that fails, try the more complex recovery
            import re
            
            # Look for the "words" array
            words_match = re.search(r'"words"\s*:\s*\[(.*?)\]', content, re.DOTALL)
            if not words_match:
                self.update_signal.emit("Could not find 'words' array in response")
                return None
            
            words_content = words_match.group(1)
            
            # Try to extract individual word objects
            word_objects = []
            brace_level = 0
            current_object = ""
            
            for char in words_content:
                current_object += char
                if char == '{':
                    brace_level += 1
                elif char == '}':
                    brace_level -= 1
                    if brace_level == 0:
                        # We have a complete object
                        try:
                            # Try to parse this individual object
                            obj_json = current_object.strip().strip(',').strip()
                            obj_json = '{' + obj_json + '}'
                            obj_json = self._fix_common_json_issues(obj_json)
                            word_obj = json.loads(obj_json)
                            if word_obj.get('word'):  # Valid word object
                                word_objects.append(word_obj)
                        except Exception as e:
                            self.update_signal.emit(f"Failed to parse object: {str(e)}")
                        current_object = ""
            
            if word_objects:
                self.update_signal.emit(f"Recovered {len(word_objects)} valid word objects from malformed JSON")
                return {"words": word_objects}
            else:
                self.update_signal.emit("Could not recover any valid word objects")
                return None
                
        except Exception as e:
            self.update_signal.emit(f"JSON recovery failed: {str(e)}")
            return None
    
    def _fix_escaped_quotes_issue(self, content: str) -> str:
        """Specifically fix the escaped quotes issue we're seeing."""
        try:
            import re
            
            # The issue is that the AI is using \" instead of " in JSON values
            # We need to fix this by replacing \" with " but only in the right places
            
            # Pattern to find string values that have incorrectly escaped quotes
            # This matches "key": \"value with quotes\" and fixes it to "key": "value with quotes"
            def fix_value_quotes(match):
                key = match.group(1)
                value = match.group(2)
                # Remove the escaping from the quotes in the value
                fixed_value = value.replace('\\"', '"')
                return f'"{key}": "{fixed_value}"'
            
            # Fix the specific pattern we see in the error
            pattern = r'"(\w+)"\s*:\s*\\"([^"]*(?:\\"[^"]*)*)\\"'
            fixed_content = re.sub(pattern, fix_value_quotes, content)
            
            return fixed_content
            
        except Exception as e:
            self.update_signal.emit(f"Failed to fix escaped quotes: {str(e)}")
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
                    # Preserve the original user input word
                    word_data['original_word'] = word
                    
                    # Store the structured data directly
                    word_data_list.append(word_data)
                    
                    # Store English translation for image fetching
                    if word_data.get('english_translation'):
                        word_translations[word] = word_data['english_translation'].lower().strip()
                else:
                    # Fallback with error data structure
                    error_data = {
                        'word': word,
                        'original_word': word,  # Preserve original word even in error cases
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
                    'original_word': word,  # Preserve original word even in error cases
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
