# AI Vision Snipping Tool

A desktop application that combines screen capture functionality with OpenAI's Vision API to analyze images and extract information from your screen.

[![MasterHead](https://raw.githubusercontent.com/donejeh/PolarBearGG/main/demo-1.png)](ai-vision-snipping-tool)
[![MasterHead](https://raw.githubusercontent.com/donejeh/PolarBearGG/main/demo-2.png)](ai-vision-snipping-tool)


![App Screenshot](debug_capture.png)

## Features

- 🖱️ Easy-to-use screen snipping interface
- 🔍 Capture any region of your screen
- 🤖 Analyze images using OpenAI's Vision models
- 📝 Extract text, solve problems, and analyze visual content
- 📊 See both the captured image and AI analysis side-by-side

## Description

This tool allows you to select any portion of your screen and instantly analyze it using OpenAI's Vision capabilities. It's useful for:

- Extracting text from images/screenshots
- Solving math problems visible on screen
- Analyzing graphs, charts or visual information
- Getting detailed descriptions of visual content

## Installation

### Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Tkinter (usually included with Python)
- Required Python packages

### Step 1: Clone the repository

```bash
git clone https://github.com/donejeh/ai-vision-snipping-tool.git
cd ai-vision-snipping-tool
```

### Step 2: Install dependencies

```bash
pip install -r requirements.txt
```

Or install dependencies manually:

```bash
pip install pillow openai python-dotenv
```

### Step 3: Configure your OpenAI API key

Create a `.env` or rename `.env.example` file in the root directory with:

```
OPENAI_API_KEY=your_api_key_here
```

## Usage

1. Run the application:
   ```bash
   python app.py
   ```

2. Click the "Snip Area" button to start capturing
3. Drag to select the region of your screen you want to analyze
4. Release to capture
5. View the AI analysis in the right panel

## Building an Executable

To create a standalone executable file that can be distributed without requiring Python:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Run the build script:
   ```bash
   python build_exe.py
   ```
   
   Or use PyInstaller directly:
   ```bash
   pyinstaller --name=AI_Vision_Snipping --onefile --windowed --add-data=".env;." app.py
   ```

3. Find your executable in the `dist` folder

### Notes about the executable:
- The executable will include your API key from the `.env` file
- For distribution to others, consider having users input their own API key
- The executable is specific to the OS it was built on (Windows exe won't run on Mac/Linux)

## How It Works

1. **Screen Selection**: Uses Tkinter to create a transparent overlay where you can select an area
2. **Image Capture**: Captures the selected area using PIL's ImageGrab
3. **Image Processing**: Converts the image to a format suitable for API transmission
4. **API Integration**: Sends the image to OpenAI's Vision API with a prompt
5. **Result Display**: Shows both the captured image and the API response

## Configuration

- The `vision.log` file contains logs of all API responses
- Debug captures are saved as `debug_capture.png` for troubleshooting
- You can modify the OpenAI prompt in the `process_image()` function

## Troubleshooting

- **Black Screenshots**: Make sure you're running with proper DPI awareness settings
- **API Errors**: Check your API key and internet connection
- **Display Issues**: The program saves debug images that you can check

## Requirements

- Python 3.8+
- OpenAI API key
- Pillow (PIL)
- Tkinter
- python-dotenv

## License

MIT

---

Created with ❤️ by eJEH