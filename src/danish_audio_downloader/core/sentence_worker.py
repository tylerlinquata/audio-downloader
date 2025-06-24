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
        """Extract the most common English translation from the ChatGPT response."""
        import re
        
        # Look for patterns that might contain English translations
        # First, try to find the first English translation from the example sentences
        sentence_pattern = r'\d+\.\s*[^-\n]+?\s*-\s*([^\n]+?)(?=\n\d+\.|\n\n|\Z)'
        matches = re.findall(sentence_pattern, content, re.DOTALL)
        
        if matches:
            # Get the first English translation and extract the main word
            first_translation = matches[0].strip()
            # Remove articles and get the main noun/word
            words = first_translation.lower().split()
            # Filter out common articles, prepositions, etc.
            filter_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'from'}
            content_words = [w for w in words if w not in filter_words and len(w) > 2]
            if content_words:
                return content_words[0]  # Return the first meaningful word
        
        # Fallback: look for definition patterns
        definition_patterns = [
            r'Definition:\s*([^\n]+)',
            r'Definition:\s*\[([^\]]+)\]',
        ]
        
        for pattern in definition_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                definition = match.group(1).strip()
                # Extract English words from the definition
                words = definition.lower().split()
                content_words = [w for w in words if w not in filter_words and len(w) > 2]
                if content_words:
                    return content_words[0]
        
        return ""

    def abort(self) -> None:
        """Abort the sentence generation process."""
        self.abort_flag = True
        self.update_signal.emit("Aborting sentence generation...")
