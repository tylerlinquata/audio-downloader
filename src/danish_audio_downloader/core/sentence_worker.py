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
    finished_signal = pyqtSignal(str)  # generated sentences
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
                    
                    # Add a small delay to respect rate limits
                    time.sleep(AppConfig.REQUEST_DELAY)
                    
                except Exception as e:
                    error_msg = f"Error generating sentences for '{word}': {str(e)}"
                    self.update_signal.emit(error_msg)
                    all_sentences.append(f"**{word}**\n\nError: Could not generate sentences for this word.\n\n---")
            
            if not self.abort_flag:
                final_result = "\n\n".join(all_sentences)
                self.finished_signal.emit(final_result)
            
        except Exception as e:
            self.error_signal.emit(f"Failed to initialize OpenAI: {str(e)}")

    def abort(self) -> None:
        """Abort the sentence generation process."""
        self.abort_flag = True
        self.update_signal.emit("Aborting sentence generation...")
