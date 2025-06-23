# Danish Word Learning Assistant

A Python application for downloading Danish word pronunciations from ordnet.dk and saving them to your Anki collection. Features a modern, modular architecture following Python best practices.

## Features

- **Unified Processing Workflow** - Single interface that automatically handles both audio downloads and sentence generation
- **Clean GUI Interface** - Streamlined two-tab interface for processing and settings
- **Audio Downloads** - Download audio for multiple Danish words from ordnet.dk with validation
- **AI-Powered Sentence Generation** - Generate context-appropriate sentences using ChatGPT with CEFR level targeting
- **Comprehensive Grammar Integration** - Automatically extract IPA pronunciation, word types, gender, and inflections
- **Advanced Anki Integration** - Export sentences as Anki-ready CSV files with multiple card types per word
- **Intelligent Word Processing** - Smart detection and handling of Danish inflected forms
- **Dual Progress Tracking** - Separate progress bars for audio downloads and sentence generation phases
- **Anki CSV Export** - Save sentences as structured CSV files ready for Anki import
- **Audio Validation** - Automatically validates downloaded files to ensure they're correct
- **Automatic Anki Integration** - Audio files are automatically saved locally and copied to your Anki media collection
- **Detailed Logging** - Real-time updates and comprehensive logging for both processing phases
- **Settings Management** - Persistent settings for directories, API keys, and preferences

## Project Structure

This project follows Python best practices with a modular architecture:

```
src/
├── danish_audio_downloader/
│   ├── __init__.py              # Package initialization
│   ├── core/                    # Core business logic
│   │   ├── __init__.py
│   │   ├── downloader.py        # Audio download functionality
│   │   ├── worker.py            # Download worker thread
│   │   └── sentence_worker.py   # Sentence generation worker
│   ├── gui/                     # User interface
│   │   ├── __init__.py
│   │   └── app.py               # Main application window
│   └── utils/                   # Utilities and configuration
│       ├── __init__.py
│       ├── config.py            # Configuration management
│       └── validators.py        # Validation utilities
├── main.py                      # Application entry point
└── tests/                       # Comprehensive test suite
```

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- macOS (primarily tested, should work on other platforms)

### Method 1: Run the Python application directly

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd audio-downloader
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python main.py
   ```

### Method 2: Build a macOS app bundle

1. **Follow steps 1-3 from Method 1**

2. **Install py2app:**
   ```bash
   pip install py2app
   ```

3. **Build the app:**
   ```bash
   # Using the build script (recommended)
   make build-app
   
   # Or manually
   chmod +x build-tools/build_app.sh
   ./build-tools/build_app.sh
   ```

4. **Find the app in the `dist` folder and copy to Applications**

## Usage

### Unified Word Processing
The application now combines audio downloads and sentence generation into a single streamlined workflow:

1. Launch the application and go to the "Process Words" tab
2. Enter Danish words (one per line) in the text area
3. Configure your settings in the **Settings tab**:
   - **Output Directory**: Where audio files will be saved
   - **Anki Media Folder**: Path to your Anki collection's media folder  
   - **CEFR Level**: Select A1-C2 for appropriate sentence difficulty
   - **OpenAI API Key**: Required for sentence generation
   - **Note**: Audio files are automatically saved to both the output directory and copied to your Anki Media Folder
4. Return to the "Process Words" tab and click the main action button to start processing (the button will dynamically change based on the application state):
   - **"Process Words (Audio + Sentences)"** - Click to start the unified workflow
   - **"Cancel Processing"** - Click during processing to cancel the current operation  
   - **"Save as Anki CSV"** - Click after completion to save results and return to processing mode
5. **Phase 1**: Audio files are downloaded first with progress tracking
6. **Phase 2**: Example sentences are automatically generated after audio completion
7. Monitor progress with dual progress bars and detailed logging

### Advanced Features

#### Comprehensive Grammar Integration
The app requests detailed grammar information from ChatGPT for each word in Danish:
- **IPA Pronunciation**: Actual Danish IPA transcription in slashes (e.g., `/hun/`)
- **Word Type**: Danish word types (substantiv, verbum, adjektiv, etc.)
- **Gender**: `en` or `et` for Danish nouns
- **Plural Forms**: Complete plural declensions
- **Inflections**: Definite forms, conjugations, comparative/superlative forms
- **Definitions**: Danish definitions and explanations

#### Anki CSV Format
The CSV export creates Anki-ready cards with these columns populated with real grammar data and Danish text throughout:
- **Front (Eksempel med ord fjernet eller blankt)**: Sentence with word removed or blanked
- **Front (Billede)**: Image placeholder (`<img src="myimage.jpg">`)
- **Front (Definition, grundform, osv.)**: Real Danish word type, gender, and definition
- **Back (et enkelt ord/udtryk, uden kontekst)**: The target word
- **- Hele sætningen (intakt)**: Complete sentence with word intact
- **- Ekstra info (IPA, køn, bøjning)**: Real IPA, Danish grammar labels (`køn:`, `flertal:`, `bøjning:`), and audio reference
- **• Lav 2 kort?**: Flag for creating additional card variations

All card content uses Danish labels and fallback text (e.g., "Definition nødvendig", "Grammatik info nødvendig") to maintain language consistency.

### Settings Configuration
The application provides a dedicated Settings tab for all configuration options:

1. Go to the "Settings" tab
2. **Folders**:
   - **Output Directory**: Set where audio files and failed word lists are saved
   - **Anki Media Folder**: Configure the path to your Anki collection's media folder
3. **Processing Options**:
   - **CEFR Level for Sentences**: Choose difficulty level (A1-C2) for generated example sentences
4. **API Settings**:
   - **OpenAI API Key**: Save your API key for sentence generation (securely stored)
5. Click "Save Settings" to persist your configuration across sessions

All processing options are now centralized in the Settings tab, making configuration easier and keeping the main processing interface clean and focused.

## Development

### Running Tests

The project includes a comprehensive test suite with 34+ tests covering core functionality and GUI components.

```bash
# Run all tests
python tests/run_tests.py

# Run smoke tests
python tests/smoke_test.py

# Use Make commands (recommended)
make test              # Run all tests
make test-smoke        # Run smoke tests only
make build-app         # Build macOS app bundle
```

### Code Structure

- **Core Logic** (`src/danish_audio_downloader/core/`): Business logic separated from UI
- **GUI Components** (`src/danish_audio_downloader/gui/`): PyQt5-based user interface
- **Utilities** (`src/danish_audio_downloader/utils/`): Configuration, validation, and helper functions
- **Tests** (`tests/`): Comprehensive unit tests with mocking for external dependencies
- **Build Tools** (`build-tools/`): App building scripts and resources

### Dependencies

**Core Application:**
- PyQt5 - GUI framework
- requests - HTTP client for downloading
- beautifulsoup4 - HTML parsing
- openai - GPT integration for sentence generation

**Development & Testing:**
- pytest - Testing framework
- pytest-qt - GUI testing utilities
- pytest-mock - Mocking support

## Configuration

The application stores settings using Qt's QSettings system:
- **Output Directory**: Where audio files are saved
- **Anki Media Folder**: Path to Anki's media collection
- **OpenAI API Key**: For sentence generation feature
- **CEFR Level**: Default difficulty level for sentences

## Troubleshooting

### Audio Downloads
- **Downloads fail**: Check internet connection and verify ordnet.dk is accessible
- **Invalid audio files**: The app validates downloads automatically; failed files are logged
- **Permission errors**: Ensure write access to the output directory

### Anki Integration
- **Files not appearing in Anki**: Check that the media folder path is correct
- **Path location**: Usually `~/Library/Application Support/Anki2/User 1/collection.media` on macOS
- **Anki sync issues**: Restart Anki or sync manually after adding new files

### Sentence Generation
- **API errors**: Verify your OpenAI API key is valid and has credits
- **Rate limiting**: The app includes delays between requests to respect API limits
- **Model availability**: Uses GPT-3.5-turbo by default (configurable in code)

## Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature-name`
3. **Make your changes** following the existing code structure
4. **Run tests**: `python run_tests.py`
5. **Submit a pull request**

### Code Standards
- Follow PEP 8 style guidelines
- Add tests for new functionality
- Update documentation as needed
- Maintain the modular architecture

## License

This project is open source. See the LICENSE file for details.

## Support

For issues, feature requests, or questions:
1. Check the troubleshooting section above
2. Review existing issues in the repository
3. Create a new issue with detailed information about your problem

---

**Note**: This application is designed for educational and personal use. Please respect ordnet.dk's terms of service and rate limits when downloading audio files.
