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
                prompt = f"""Give me some example sentences for "{word}" in Danish, and give me translations for each sentence. Please make sure that you're pulling these examples from sources that aren't likely to be incorrect or machine-translated; it's better to give me a few correct sentences than a lot of sentences where some may be incorrect. Make sure the sentences are appropriate for a {self.cefr_level} learner.

Format your response like this:
**{word}**

**Example Sentences:**
1. [Danish sentence] - [English translation]
2. [Danish sentence] - [English translation]
3. [Danish sentence] - [English translation]

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
