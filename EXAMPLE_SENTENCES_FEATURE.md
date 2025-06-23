# Danish Word Audio Downloader - Example Sentences Feature

## New Feature: ChatGPT Example Sentences

The Danish Word Audio Downloader now includes a powerful new feature that generates contextual example sentences for Danish words using ChatGPT.

### How to Use the Example Sentences Feature:

1. **Open the Application**
   ```bash
   python "Danish Word Audio Downloader GUI.py"
   ```

2. **Navigate to the Example Sentences Tab**
   Click on the "Example Sentences" tab in the application.

3. **Enter Danish Words**
   - Type Danish words one per line in the text area, or
   - Use "Load from File" to import a text file with words

4. **Select Your CEFR Level**
   Choose your Danish proficiency level from the dropdown:
   - A1: Beginner
   - A2: Elementary
   - B1: Intermediate (default)
   - B2: Upper Intermediate
   - C1: Advanced
   - C2: Proficient

5. **Enter Your OpenAI API Key**
   - Get an API key from https://platform.openai.com/
   - Enter it in the API key field
   - You can save it in the Settings tab for future use

6. **Generate Sentences**
   Click "Generate Example Sentences" and wait for the results.

### Example Output:

For the word "hus" at B1 level, you might get:

```
**hus**

**Example Sentences:**
1. Vi bor i et stort hus ved havet. - We live in a big house by the sea.
2. Huset er bygget af røde mursten. - The house is built of red bricks.
3. Kan du se det hvide hus derovre? - Can you see the white house over there?

**Usage Tips:**
- "Hus" is a neuter noun (et hus), so use "et" not "en"
- The plural form is "huse"
- Common compounds: sommerhus (summer house), skolehus (school building)
```

### Features:

- **CEFR-Targeted**: Sentences are appropriate for your proficiency level
- **Accurate Translations**: Each Danish sentence includes an English translation
- **Usage Tips**: Learn grammar rules, common phrases, and cultural context
- **Quality Focused**: Prioritizes accuracy over quantity
- **Save Results**: Export generated sentences to a text file for study

### Requirements:

- OpenAI API key (paid service)
- Internet connection
- All existing dependencies plus: `pip install openai`

This feature is perfect for Danish language learners who want to see words used in realistic, level-appropriate contexts!
