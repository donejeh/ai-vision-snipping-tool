#!/usr/bin/env python3
"""
Snipping Tool with OpenAI Vision

This application provides a snipping tool built with Tkinter that lets you select an area on your screen,
captures it, and then uses OpenAI's API to extract and process any text.
"""

import sys
import tkinter as tk
import ctypes
from PIL import ImageGrab, Image, ImageTk
import openai
import os
import logging
import base64
from io import BytesIO
from dotenv import load_dotenv
import time
import re

# ============================
#  Configuration & Environment
# ============================

# Make the Python process DPI-aware on Windows
if sys.platform.startswith('win'):
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Windows 8.1+
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()       # Fallback for older Windows

# For multi-monitor support on Windows:
if sys.platform.startswith('win'):
    user32 = ctypes.windll.user32

    def get_virtual_screen_rect():
        """Get the dimensions of the entire virtual screen (all monitors)."""
        x = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
        y = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
        width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
        height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
        return (x, y, width, height)
else:
    def get_virtual_screen_rect():
        # Default for non-Windows: use full primary screen (this might be adjusted as needed)
        return (0, 0, 800, 600)

# Set up logging
logging.basicConfig(
    filename='vision.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables and set OpenAI API key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")
openai.api_key = api_key

# Regular expression for inline bold formatting (e.g., **bold text**)
bold_pattern = re.compile(r'\*\*(.*?)\*\*')

# ============================
#  Utility Functions
# ============================

def encode_image_to_base64(image):
    """Encode a PIL Image to a base64 string in PNG format."""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def insert_bold_text(text_widget, line, base_tag=None):
    """
    Inserts text into the provided text widget, detecting any **bold** segments.
    Optionally, applies a base tag (for headings, lists, etc.) along with the inline bold.
    """
    start_idx = 0
    for match in bold_pattern.finditer(line):
        before_text = line[start_idx:match.start()]
        if before_text:
            text_widget.insert(tk.END, before_text, base_tag)
        bold_text = match.group(1)
        text_widget.insert(tk.END, bold_text, (base_tag, "bold") if base_tag else ("bold",))
        start_idx = match.end()
    if start_idx < len(line):
        text_widget.insert(tk.END, line[start_idx:], base_tag)

def format_and_insert_text(text_widget, content):
    """
    Parses the given content with markdown-like cues and inserts it into the text widget.
    
    Supported formatting includes:
      - Code blocks delimited by triple backticks (```).
      - Headings (lines starting with "### ").
      - Subheadings (lines starting with "## ").
      - List items (lines starting with "- ").
      - Inline bold text surrounded by **.
    """
    text_widget.delete(1.0, tk.END)
    in_code_block = False
    code_lines = []

    for line in content.splitlines():
        stripped_line = line.strip()
        # Check for code block delimiters
        if stripped_line.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lines = []
            else:
                # End of code block; insert code with a code tag
                code_text = "\n".join(code_lines)
                text_widget.insert(tk.END, code_text + "\n", "code")
                in_code_block = False
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        # Process non-code block lines with markdown cues
        if stripped_line.startswith("### "):
            heading_text = stripped_line[4:].strip()
            insert_bold_text(text_widget, heading_text, "heading")
            text_widget.insert(tk.END, "\n")
        elif stripped_line.startswith("## "):
            subheading_text = stripped_line[3:].strip()
            insert_bold_text(text_widget, subheading_text, "subheading")
            text_widget.insert(tk.END, "\n")
        elif stripped_line.startswith("- "):
            insert_bold_text(text_widget, stripped_line, "list")
            text_widget.insert(tk.END, "\n")
        else:
            insert_bold_text(text_widget, line)
            text_widget.insert(tk.END, "\n")

# ============================
#  UI and Application Code
# ============================

def setup_main_window():
    """
    Creates and sets up the main Tkinter window with image and text display areas,
    along with tagging configurations for formatted text.
    Returns the main window (root) and the text widget reference.
    """
    root = tk.Tk()
    root.title("Snipping Tool with OpenAI Vision")
    main_frame = tk.Frame(root)
    main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    # Image display area
    image_frame = tk.Frame(main_frame)
    image_frame.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
    global image_label  # used by display_image()
    image_label = tk.Label(image_frame, text="Captured Image")
    image_label.pack(pady=5)

    # Text display area
    text_frame = tk.Frame(main_frame)
    text_frame.pack(side=tk.RIGHT, padx=5, fill=tk.BOTH, expand=True)
    text_label = tk.Label(text_frame, text="Vision API Response")
    text_label.pack(pady=5)

    global result_text  # used by formatting functions
    result_text = tk.Text(text_frame, height=15, width=50, wrap="word")
    result_text.pack(pady=5, fill=tk.BOTH, expand=True)

    # Configure text widget tags
    result_text.tag_configure("heading", font=("Helvetica", 14, "bold"))
    result_text.tag_configure("subheading", font=("Helvetica", 12, "bold"))
    result_text.tag_configure("list", lmargin1=20, lmargin2=40)
    result_text.tag_configure("code", font=("Courier", 10), background="#f0f0f0")
    result_text.tag_configure("bold", font=("Helvetica", 10, "bold"))

    return root

def display_image(image):
    """
    Resizes and displays the captured image into the image display area.
    """
    display_size = (400, 300)  # Max display size
    image.thumbnail(display_size, Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(image)
    image_label.config(image=photo)
    image_label.image = photo  # Prevent garbage collection

def process_image(img):
    """
    Encodes the captured image, calls OpenAI for processing, and displays
    the formatted output in the text widget.
    """
    try:
        base64_image = encode_image_to_base64(img)
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Please perform the following tasks:\n"
                                "1. Analyze the provided image to extract all text accurately.\n"
                                "2. Examine the extracted text to determine if it contains a problem, question, or concept that needs explanation.\n"
                                "3. Provide a clear, step-by-step solution or explanation based on the extracted text.\n"
                                "4. Use markdown-like formatting for readability:\n"
                                "   - Headings: '### '\n"
                                "   - Subheadings: '## '\n"
                                "   - Bullet points: '- '\n"
                                "   - Code blocks: triple backticks (```)\n"
                                "   - Inline bold: '**bold text**'\n"
                                "5. Return the final answer in plain text format with these cues."
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        answer = response.choices[0].message.content.strip()
        logging.info("OpenAI Vision response: %s", answer)
        format_and_insert_text(result_text, answer)
    except Exception as e:
        error_message = f"Error processing image: {e}"
        logging.error(error_message)
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, error_message)

# ============================
#  Selection Window for Snipping
# ============================

class SelectionWindow:
    """
    Displays a fullscreen overlay to allow the user to select a screen region.
    """
    def __init__(self, master):
        if sys.platform.startswith('win'):
            virtual_screen = get_virtual_screen_rect()
            self.screen_x, self.screen_y, self.screen_width, self.screen_height = virtual_screen
            logging.info(f"Virtual screen dimensions: {virtual_screen}")
        else:
            self.screen_x = 0
            self.screen_y = 0
            self.screen_width = master.winfo_screenwidth()
            self.screen_height = master.winfo_screenheight()

        self.top = tk.Toplevel(master)
        self.top.wm_overrideredirect(True)
        self.top.geometry(f"{self.screen_width}x{self.screen_height}+{self.screen_x}+{self.screen_y}")
        self.top.attributes('-alpha', 0.3)  # semi-transparent overlay
        self.top.attributes('-topmost', True)
        self.top.config(bg='gray')

        self.canvas = tk.Canvas(self.top, cursor="cross", bg='gray',
                                width=self.screen_width, height=self.screen_height)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.start_x = None
        self.start_y = None
        self.rect = None
        self.bbox = None

        self.coord_label = tk.Label(self.top, bg="white", fg="black")
        self.coord_label.place(x=10, y=10)

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<Escape>", self.on_escape)
        self.top.bind("<Escape>", self.on_escape)

        self.top.lift()
        self.top.focus_force()
        self.top.update()
        logging.info(f"Selection window created: {self.screen_width}x{self.screen_height}")

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y,
                                                 self.start_x, self.start_y,
                                                 outline='red', width=2)
        self.coord_label.config(text=f"Start: ({self.start_x}, {self.start_y})")

    def on_move_press(self, event):
        curX, curY = event.x, event.y
        self.canvas.coords(self.rect, self.start_x, self.start_y, curX, curY)
        self.coord_label.config(text=f"Start: ({self.start_x}, {self.start_y}), Current: ({curX}, {curY})")

    def on_button_release(self, event):
        end_x, end_y = event.x, event.y
        if sys.platform.startswith('win'):
            actual_left = min(self.start_x, end_x) + self.screen_x
            actual_top = min(self.start_y, end_y) + self.screen_y
            actual_right = max(self.start_x, end_x) + self.screen_x
            actual_bottom = max(self.start_y, end_y) + self.screen_y
        else:
            actual_left = min(self.start_x, end_x)
            actual_top = min(self.start_y, end_y)
            actual_right = max(self.start_x, end_x)
            actual_bottom = max(self.start_y, end_y)

        if actual_right - actual_left > 5 and actual_bottom - actual_top > 5:
            self.bbox = (int(actual_left), int(actual_top), int(actual_right), int(actual_bottom))
            logging.info(f"Selected area: {self.bbox}")
        self.cleanup()

    def on_escape(self, event):
        self.bbox = None
        self.cleanup()

    def cleanup(self):
        try:
            if self.rect:
                self.canvas.delete(self.rect)
            self.top.after(10, self.top.destroy)
        except Exception as e:
            logging.error(f"Error during selection window cleanup: {e}")
            try:
                self.top.destroy()
            except Exception:
                pass

# ============================
#  Snipping and Main Loop
# ============================

is_snipping = False

def capture_area(root):
    """
    Hides the main window, launches the selection window, captures the selected area,
    and then processes the image.
    """
    global is_snipping
    if is_snipping:
        return
    is_snipping = True
    try:
        root.withdraw()
        root.update()
        time.sleep(0.3)
        selection = SelectionWindow(root)
        root.wait_window(selection.top)
        time.sleep(0.1)
        root.deiconify()
        root.update()
        if selection.bbox:
            try:
                logging.info(f"Attempting to capture area: {selection.bbox}")
                img = ImageGrab.grab(bbox=selection.bbox)
                img.save("debug_capture.png")
                display_image(img)
                process_image(img)
            except Exception as e:
                error_message = f"Error capturing image: {e}"
                logging.error(error_message)
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, error_message)
    finally:
        is_snipping = False

def main():
    """Main entry point for the application."""
    root = setup_main_window()
    # Create the Snip Area button and pack it outside the main frame.
    capture_button = tk.Button(root, text="Snip Area", command=lambda: capture_area(root))
    capture_button.pack(pady=10)
    root.mainloop()

if __name__ == "__main__":
    main()
