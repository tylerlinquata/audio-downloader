# Danish Word Audio Downloader

A Python application for downloading Danish word pronunciations from ordnet.dk and saving them to your Anki collection. Features a modern, modular architecture following Python best practices.

## Features

- **Clean GUI Interface** - Intuitive tabbed interface for different functions
- **Audio Downloads** - Download audio for multiple Danish words from ordnet.dk
- **Example Sentences** - Generate context-appropriate sentences using ChatGPT with CEFR level targeting
- **Audio Validation** - Automatically validates downloaded files to ensure they're correct
- **Anki Integration** - Saves files locally and optionally copies them to your Anki media collection
- **Progress Tracking** - Real-time progress updates and detailed logging
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

### Audio Download
1. Launch the application and go to the "Download" tab
2. Enter Danish words (one per line) or load them from a text file
3. Configure output directory and Anki media folder in the "Settings" tab
4. Check "Copy to Anki Media Folder" if you want automatic Anki integration
5. Click "Start Download" to begin
6. Monitor progress in the log area

### Example Sentences Generation
1. Go to the "Example Sentences" tab
2. Enter Danish words (one per line) or load them from a file
3. Select your CEFR level (A1-C2) for appropriate difficulty
4. Enter your OpenAI API key (save it in Settings for convenience)
5. Click "Generate Example Sentences"
6. Save the results to a file when complete

### Settings Configuration
1. Go to the "Settings" tab
2. Set your preferred output directory
3. Configure your Anki media folder path
4. Save your OpenAI API key for sentence generation
5. Click "Save Settings" to persist your configuration

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
