"""
Worker thread for generating example sentences using ChatGPT.
"""

import time
from typing import List
from PyQt5.QtCore import QThread, pyqtSignal
import openai

from ..utils.config import AppConfig


class SentenceWorker(QThread):
    """Worker thread for generating example sentences using ChatGPT."""
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(str, dict)  # generated sentences, word translations
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
            
            all_sentences = []
            word_translations = {}  # Track English translations for image fetching
            total_words = len(self.words)
            
            for i, word in enumerate(self.words):
                if self.abort_flag:
                    break
                    
                self.update_signal.emit(f"Generating sentences for: {word}")
                self.progress_signal.emit(i + 1, total_words)
                
                # Create the prompt
                prompt = f"""For the Danish word "{word}", please provide:

1. **Grammar Information (in Danish):**
   - IPA pronunciation (in slashes like /pronunciation/)
   - Word type in Danish (substantiv, verbum, adjektiv, etc.)
   - If it's a noun: gender (en/et) and plural forms
   - If it's a verb: infinitive form and all conjugations
   - If it's an adjective: comparative and superlative forms
   - A brief Danish definition
   - The main English translation

2. **Example Sentences:**
   - Provide exactly 3 different example sentences using "{word}"
   - Use the exact word "{word}" in each sentence (not inflected forms)
   - Make sentences appropriate for {self.cefr_level} level
   - Provide English translations
   - Make sure sentences show different contexts/uses

Format your response exactly like this:
**{word}**

**Grammar Info:**
IPA: /pronunciation/
Type: [substantiv/verbum/adjektiv/etc.]
Gender: [en/et] (if noun)
Plural: [plural form] (if noun)
Inflections: [other forms, declensions, conjugations]
Definition: [Danish definition/explanation]
English word: [main English translation]

**Example Sentences:**
1. [Danish sentence using "{word}"] - [English translation]
2. [Danish sentence using "{word}"] - [English translation]  
3. [Danish sentence using "{word}"] - [English translation]

---"""
                
                try:
                    # Make API call
                    response = client.chat.completions.create(
                        model=AppConfig.OPENAI_MODEL,
                        messages=[
                            {"role": "system", "content": "You are a helpful Danish language teacher who provides accurate example sentences and usage tips for Danish words."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=AppConfig.OPENAI_MAX_TOKENS,
                        temperature=AppConfig.OPENAI_TEMPERATURE
                    )
                    
                    sentence_content = response.choices[0].message.content
                    
                    # Ensure the response ends with the separator
                    if not sentence_content.strip().endswith('---'):
                        sentence_content = sentence_content.rstrip() + '\n\n---'
                    
                    all_sentences.append(sentence_content)
                    
                    # Extract English translation for image fetching
                    english_translation = self._extract_english_translation(sentence_content)
                    if english_translation:
                        word_translations[word] = english_translation
                    
                    # Add a small delay to respect rate limits
                    time.sleep(AppConfig.REQUEST_DELAY)
                    
                except Exception as e:
                    error_msg = f"Error generating sentences for '{word}': {str(e)}"
                    self.update_signal.emit(error_msg)
                    all_sentences.append(f"**{word}**\n\nError: Could not generate sentences for this word.\n\n---")
            
            if not self.abort_flag:
                final_result = "\n\n".join(all_sentences)
                self.finished_signal.emit(final_result, word_translations)
            
        except Exception as e:
            self.error_signal.emit(f"Failed to initialize OpenAI: {str(e)}")

    def _extract_english_translation(self, content: str) -> str:
        """Extract the English translation from the ChatGPT response."""
        import re
        
        # First, look for the explicit "English word:" format
        english_word_match = re.search(r'English word:\s*([^\n]+)', content, re.IGNORECASE)
        if english_word_match:
            english_word = english_word_match.group(1).strip()
            # Clean up the word (remove any brackets, punctuation, etc.)
            english_word = re.sub(r'[^\w\s]', '', english_word).strip().lower()
            if english_word and len(english_word) > 1:
                return english_word
        
        # Fallback: try to extract from the Definition field if available
        definition_match = re.search(r'Definition:\s*([^\n]+)', content, re.IGNORECASE)
        if definition_match:
            definition = definition_match.group(1).strip()
            # Remove any leading Danish word if present (like "mel: flour")
            if ':' in definition:
                definition = definition.split(':', 1)[1].strip()
            # Extract the main English word (before any additional description)
            words = definition.split()
            if words:
                # Take the first word and clean it up
                main_word = words[0].strip('[]().,!?')
                if len(main_word) > 2:
                    return main_word.lower()
        
        # Last resort: analyze example sentences for frequent meaningful words
        sentence_pattern = r'\d+\.\s*[^-\n]+?\s*-\s*([^\n]+?)(?=\n\d+\.|\n\n|\Z)'
        matches = re.findall(sentence_pattern, content, re.DOTALL)
        
        if matches:
            # Analyze all translations to find the most likely main word
            word_frequency = {}
            filter_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'from', 'and', 'or', 'but', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your', 'his', 'her', 'its', 'our', 'their'}
            
            for translation in matches:
                words = re.findall(r'\b[a-zA-Z]+\b', translation.lower())
                content_words = [w for w in words if w not in filter_words and len(w) > 2]
                for word in content_words:
                    word_frequency[word] = word_frequency.get(word, 0) + 1
            
            # Return the most frequent meaningful word
            if word_frequency:
                most_common_word = max(word_frequency, key=word_frequency.get)
                return most_common_word
        
        return ""

    def abort(self) -> None:
        """Abort the sentence generation process."""
        self.abort_flag = True
        self.update_signal.emit("Aborting sentence generation...")
