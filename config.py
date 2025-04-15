import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI API key from environment variables.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")

# UI configuration
DISPLAY_SIZE = (400, 300)
TEXT_WIDGET_CONFIG = {
    "height": 15,
    "width": 50,
    "wrap": "word"
}
