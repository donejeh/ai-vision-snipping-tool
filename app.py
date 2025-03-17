import sys

# Make the Python process DPI-aware on Windows
if sys.platform.startswith('win'):
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Windows 8.1+
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()       # Fallback for older Windows

import tkinter as tk
from PIL import ImageGrab, Image, ImageTk
import openai
import os
import logging
import base64
from io import BytesIO
from dotenv import load_dotenv
import time

# Set up logging
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

# Main application window
root = tk.Tk()
root.title("Snipping Tool with OpenAI Vision")

# Create a frame to hold the image and text
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

# Text widget to display the OpenAI response
result_text = tk.Text(text_frame, height=15, width=50)
result_text.pack(pady=5, fill=tk.BOTH, expand=True)

def encode_image_to_base64(image):
    """Encode a PIL image to base64 (PNG format)."""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def display_image(image):
    """Resize and display the image in the GUI."""
    display_size = (400, 300)  # Maximum display size
    image.thumbnail(display_size, Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(image)
    image_label.config(image=photo)
    image_label.image = photo  # Keep a reference to prevent garbage collection

def capture_area():
    """Hide the main window, let the user draw a selection, then capture that region."""
    # Hide the main window so it doesn't interfere with the snip
    root.withdraw()
    
    # Delay slightly to ensure window is hidden
    time.sleep(0.2)
    
    # Create a fullscreen transparent window for selection
    selection = SelectionWindow(root)
    root.wait_window(selection.top)
    
    # Show the main window again
    root.deiconify()
    
    if selection.bbox:
        try:
            logging.info(f"Attempting to capture area: {selection.bbox}")
            # Capture the selected region
            img = ImageGrab.grab(bbox=selection.bbox)
            
            # Save a debug image if you want to see what's captured
            img.save("debug_capture.png")
            
            # Display the image in the GUI
            display_image(img)
            # Optionally, pass it to your function that calls OpenAI
            process_image(img)
            
        except Exception as e:
            error_message = f"Error capturing image: {e}"
            logging.error(error_message)
            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, error_message)

class SelectionWindow:
    """Fullscreen overlay to let the user drag a selection rectangle."""
    def __init__(self, master):
        self.screen_width = master.winfo_screenwidth()
        self.screen_height = master.winfo_screenheight()
        
        self.top = tk.Toplevel(master)
        self.top.attributes('-fullscreen', True)
        self.top.attributes('-alpha', 0.3)  # semi-transparent overlay
        self.top.config(bg='gray')
        
        # Canvas matches entire screen size
        self.canvas = tk.Canvas(self.top, cursor="cross", bg='gray', 
                                width=self.screen_width, height=self.screen_height)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.bbox = None
        
        # Optional label to show coordinates
        self.coord_label = tk.Label(self.top, bg="white", fg="black")
        self.coord_label.place(x=10, y=10)
        
        # Bind mouse events
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        
        # Bring to front
        self.top.lift()
        self.top.focus_force()

    def on_button_press(self, event):
        # Record the starting position (relative to the overlay)
        self.start_x = event.x
        self.start_y = event.y
        
        # Draw the initial rectangle
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 
                                                 self.start_x, self.start_y, 
                                                 outline='red', width=2)
        self.coord_label.config(text=f"Start: ({self.start_x}, {self.start_y})")

    def on_move_press(self, event):
        # Update the rectangle
        curX, curY = event.x, event.y
        self.canvas.coords(self.rect, self.start_x, self.start_y, curX, curY)
        self.coord_label.config(text=f"Start: ({self.start_x}, {self.start_y}), Current: ({curX}, {curY})")

    def on_button_release(self, event):
        end_x, end_y = event.x, event.y
        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        right = max(self.start_x, end_x)
        bottom = max(self.start_y, end_y)
        
        # Ensure minimum size
        if right - left > 5 and bottom - top > 5:
            # Coordinates for ImageGrab
            self.bbox = (int(left), int(top), int(right), int(bottom))
            logging.info(f"Selected area: {self.bbox}")
        
        self.top.destroy()

def process_image(img):
    """Encode the image and (attempt to) call an OpenAI 'vision' model."""
    try:
        base64_image = encode_image_to_base64(img)
        
        # "gpt-4o-mini" 
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze the image and extract the text. try to solve the problem. return the answer in a text format."
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
            max_tokens=300
        )
        
        answer = response.choices[0].message.content.strip()
        logging.info("OpenAI Vision response: %s", answer)
        
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, answer)
        
    except Exception as e:
        error_message = f"Error processing image: {e}"
        logging.error(error_message)
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, error_message)

# Button to initiate the snipping process
capture_button = tk.Button(root, text="Snip Area", command=capture_area)
capture_button.pack(pady=10)

# Start the GUI
root.mainloop()
