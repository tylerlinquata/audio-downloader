# Danish Word Audio Downloader

A macOS application for downloading Danish word pronunciations from ordnet.dk and saving them to your Anki collection.

## Features

- Simple GUI interface
- Download audio for multiple Danish words from ordnet.dk
- Automatically validates audio files to ensure they're correct
- Saves files to a local folder and optionally copies them to your Anki media collection
- Keeps track of failed downloads

## Running the Application

### Method 1: Run the Python script directly

1. Make sure you have Python 3.x installed
2. Install the required packages:
   ```
   pip install PyQt5 requests beautifulsoup4
   ```
3. Run the application:
   ```
   python "Danish Word Audio Downloader GUI.py"
   ```

### Method 2: Build a macOS app bundle

1. Install the required packages:
   ```
   pip install PyQt5 requests beautifulsoup4 py2app
   ```
2. Build the app:
   ```
   python setup.py py2app
   ```
3. The application will be created in the `dist` folder
4. Copy the app to your Applications folder

## Usage

1. Enter Danish words in the text area (one word per line) or load them from a file
2. Configure the output directory and Anki media folder in the Settings tab
3. Check or uncheck the "Copy to Anki Media Folder" option as needed
4. Click "Start Download" to begin downloading audio files
5. View the progress in the log area

## Notes

- If a word fails to download, it will be added to a list of failed words
- Failed words will be saved to `failed_words.txt` in the output directory
- The application will remember your settings between runs

## Troubleshooting

- If downloads fail, check your internet connection
- Make sure the Anki media folder path is correct (typically found at ~/Library/Application Support/Anki2/User 1/collection.media)
- If Anki is running while you download files, you may need to synchronize or restart Anki to see the new audio files
