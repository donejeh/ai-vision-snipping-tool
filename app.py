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

# Make the Python process DPI-aware on Windows
if sys.platform.startswith('win'):
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Windows 8.1+
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()       # Fallback for older Windows

# For multi-monitor support on Windows
# SM_XVIRTUALSCREEN
 # SM_YVIRTUALSCREEN
 # SM_CXVIRTUALSCREEN
 # SM_CYVIRTUALSCREEN
if sys.platform.startswith('win'):
    user32 = ctypes.windll.user32
    def get_virtual_screen_rect():
        """Get the dimensions of the entire virtual screen (all monitors)."""
        x = user32.GetSystemMetrics(76)  
        y = user32.GetSystemMetrics(77) 
        width = user32.GetSystemMetrics(78)  
        height = user32.GetSystemMetrics(79) 
        return (x, y, width, height)

# play around by Set up logging
logging.basicConfig(
    filename='vision.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")
openai.api_key = api_key

# Here is Main application window
root = tk.Tk()
root.title("Snipping Tool with OpenAI Vision")

# Create a main frame to hold image and text
main_frame = tk.Frame(root)
main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Image display area
image_frame = tk.Frame(main_frame)
image_frame.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
image_label = tk.Label(image_frame, text="Captured Image")
image_label.pack(pady=5)

# Text display area
text_frame = tk.Frame(main_frame)
text_frame.pack(side=tk.RIGHT, padx=5, fill=tk.BOTH, expand=True)
text_label = tk.Label(text_frame, text="Vision API Response")
text_label.pack(pady=5)

# Text widget for displaying the OpenAI response
result_text = tk.Text(text_frame, height=15, width=50, wrap="word")
result_text.pack(pady=5, fill=tk.BOTH, expand=True)

# ------------------------
#  TAG CONFIGURATIONS
# ------------------------
result_text.tag_configure("heading", font=("Helvetica", 14, "bold"))
result_text.tag_configure("subheading", font=("Helvetica", 12, "bold"))
result_text.tag_configure("list", lmargin1=20, lmargin2=40)  # Adjust margins as needed
result_text.tag_configure("code", font=("Courier", 10), background="#f0f0f0")
result_text.tag_configure("bold", font=("Helvetica", 10, "bold"))

# Regex for detecting bold text segments like **bold text**
bold_pattern = re.compile(r'\*\*(.*?)\*\*')

def encode_image_to_base64(image):
    """Encode a PIL image to base64 (PNG format)."""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def display_image(image):
    """Resize and display the image in the GUI."""
    display_size = (400, 300)  # Max display size
    image.thumbnail(display_size, Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(image)
    image_label.config(image=photo)
    image_label.image = photo  # Keep reference to avoid GC

def insert_bold_text(text_widget, line, base_tag=None):
    """
    Inserts text into 'text_widget' while detecting **bold** segments.
    If 'base_tag' is provided (e.g., "list", "heading"), that style
    will apply to the entire line in addition to inline bold.
    """
    start_idx = 0
    
    for match in bold_pattern.finditer(line):
        # Text before the bold part
        before_text = line[start_idx:match.start()]
        if before_text:
            text_widget.insert(tk.END, before_text, base_tag)
        
        # The bold text (group(1))
        bold_text = match.group(1)
        text_widget.insert(tk.END, bold_text, (base_tag, "bold") if base_tag else ("bold",))
        
        start_idx = match.end()
    
    # Remaining text after the last bold segment
    if start_idx < len(line):
        text_widget.insert(tk.END, line[start_idx:], base_tag)

def format_and_insert_text(text_widget, content):
    """
    Parse the content and insert formatted text into the text widget.
    Handles:
      - Code blocks (triple backticks)
      - Headings (`### Heading`)
      - Subheadings (`## Subheading`)
      - Lists (`- Item`)
      - Inline bold text (`**bold**`)
    """
    # Clear existing text
    text_widget.delete(1.0, tk.END)
    
    in_code_block = False
    code_lines = []
    
    lines = content.splitlines()
    
    for line in lines:
        stripped_line = line.strip()
        
        # Check for start/end of code block
        if stripped_line.startswith("```"):
            if not in_code_block:
                # Start code block
                in_code_block = True
                code_lines = []
            else:
                # End code block => insert the accumulated code
                code_text = "\n".join(code_lines)
                text_widget.insert(tk.END, code_text + "\n", "code")
                in_code_block = False
            continue
        
        if in_code_block:
            # Accumulate code lines
            code_lines.append(line)
            continue
        
        # Not in a code block => interpret markdown cues
        if stripped_line.startswith("### "):
            # Heading
            heading_text = stripped_line[4:].strip()
            insert_bold_text(text_widget, heading_text, "heading")
            text_widget.insert(tk.END, "\n")  # Newline after heading
        elif stripped_line.startswith("## "):
            # Subheading
            subheading_text = stripped_line[3:].strip()
            insert_bold_text(text_widget, subheading_text, "subheading")
            text_widget.insert(tk.END, "\n")
        elif stripped_line.startswith("- "):
            # List item
            # Insert the dash as well if you want it displayed
            item_text = stripped_line
            # One approach: insert the entire line with "list" tag, then parse bold
            insert_bold_text(text_widget, item_text, "list")
            text_widget.insert(tk.END, "\n")
        else:
            # Normal text line => just insert with inline bold detection
            insert_bold_text(text_widget, line)
            text_widget.insert(tk.END, "\n")

def process_image(img):
    """Encode the image, call the OpenAI model, and display formatted output."""
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
                                "3. Provide a clear, step-by-step solution or explanation based on the content of the extracted text.\n"
                                "4. Use markdown-like formatting for readability:\n"
                                "   - Headings: '### '\n"
                                "   - Subheadings: '## '\n"
                                "   - Bullet points: '- '\n"
                                "   - Code blocks: triple backticks (```)\n"
                                "   - Inline bold: '**bold text**'\n"
                                "5. Return the final answer in plain text format with these cues included."
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
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

# Flag to track if we're currently snipping
is_snipping = False

class SelectionWindow:
    """Fullscreen overlay to let the user drag a selection rectangle."""
    def __init__(self, master):
        if sys.platform.startswith('win'):
            virtual_screen = get_virtual_screen_rect()
            self.screen_x = virtual_screen[0]
            self.screen_y = virtual_screen[1]
            self.screen_width = virtual_screen[2]
            self.screen_height = virtual_screen[3]
            logging.info(f"Virtual screen dimensions: {virtual_screen}")
        else:
            self.screen_x = 0
            self.screen_y = 0
            self.screen_width = master.winfo_screenwidth()
            self.screen_height = master.winfo_screenheight()
        
        self.top = tk.Toplevel(master)
        self.top.wm_overrideredirect(True)
        self.top.geometry(f"{self.screen_width}x{self.screen_height}+{self.screen_x}+{self.screen_y}")
        self.top.attributes('-alpha', 0.3)  # semi-transparent
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
            except:
                pass

def capture_area():
    """Hide the main window, let the user draw a selection, then capture that region."""
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

# Button to initiate the snipping process
capture_button = tk.Button(root, text="Snip Area", command=capture_area)
capture_button.pack(pady=10)

# Start the GUI main loop
root.mainloop()
