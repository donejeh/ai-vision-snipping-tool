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

# For multi-monitor support on Windows
if sys.platform.startswith('win'):
    import ctypes
    user32 = ctypes.windll.user32
    
    def get_virtual_screen_rect():
        """Get the dimensions of the entire virtual screen (all monitors)."""
        # SM_XVIRTUALSCREEN and SM_YVIRTUALSCREEN give the coordinates of the top-left corner
        # SM_CXVIRTUALSCREEN and SM_CYVIRTUALSCREEN give the width and height
        x = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
        y = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
        width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
        height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
        return (x, y, width, height)

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

# Flag to track if we're currently snipping
is_snipping = False

def capture_area():
    """Hide the main window, let the user draw a selection, then capture that region."""
    global is_snipping
    
    # Prevent multiple snipping processes running simultaneously
    if is_snipping:
        return
        
    is_snipping = True
    
    try:
        # Hide the main window so it doesn't interfere with the snip
        root.withdraw()
        root.update()  # Force update to ensure window is hidden
        
        # Delay slightly to ensure window is hidden
        time.sleep(0.3)
        
        # Create a fullscreen transparent window for selection
        selection = SelectionWindow(root)
        
        # Wait for the selection window to be closed
        root.wait_window(selection.top)
        
        # Delay to ensure proper cleanup
        time.sleep(0.1)
        
        # Show the main window again
        root.deiconify()
        root.update()  # Force update to ensure window is shown
        
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
    finally:
        # Always reset the snipping flag
        is_snipping = False

class SelectionWindow:
    """Fullscreen overlay to let the user drag a selection rectangle."""
    def __init__(self, master):
        # Get screen dimensions - use multi-monitor aware function if on Windows
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
        
        # Create the toplevel window
        self.top = tk.Toplevel(master)
        
        # Make sure it doesn't show in taskbar
        self.top.wm_overrideredirect(True)
        
        # Set the geometry to cover the entire virtual screen
        self.top.geometry(f"{self.screen_width}x{self.screen_height}+{self.screen_x}+{self.screen_y}")
        
        # Set transparency and make it fullscreen
        self.top.attributes('-alpha', 0.3)  # semi-transparent overlay
        self.top.attributes('-topmost', True)  # Keep on top of other windows
        self.top.config(bg='gray')
        
        # Canvas matches entire screen/virtual screen size
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
        self.canvas.bind("<Escape>", self.on_escape)
        
        # Also allow canceling with Escape key at the window level
        self.top.bind("<Escape>", self.on_escape)
        
        # Bring to front and update
        self.top.lift()
        self.top.focus_force()
        self.top.update()
        
        logging.info(f"Selection window created: {self.screen_width}x{self.screen_height}")

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
        
        # Convert to actual screen coordinates
        if sys.platform.startswith('win'):
            # For multi-monitor setups, add the virtual screen offset
            actual_left = min(self.start_x, end_x) + self.screen_x
            actual_top = min(self.start_y, end_y) + self.screen_y
            actual_right = max(self.start_x, end_x) + self.screen_x
            actual_bottom = max(self.start_y, end_y) + self.screen_y
        else:
            # For single monitor or non-Windows
            actual_left = min(self.start_x, end_x)
            actual_top = min(self.start_y, end_y)
            actual_right = max(self.start_x, end_x)
            actual_bottom = max(self.start_y, end_y)
        
        # Ensure minimum size
        if actual_right - actual_left > 5 and actual_bottom - actual_top > 5:
            # Coordinates for ImageGrab
            self.bbox = (int(actual_left), int(actual_top), int(actual_right), int(actual_bottom))
            logging.info(f"Selected area: {self.bbox}")
        
        self.cleanup()

    def on_escape(self, event):
        """Cancel the selection process."""
        self.bbox = None
        self.cleanup()
        
    def cleanup(self):
        """Properly clean up and destroy the selection window."""
        try:
            # Clean up canvas items if they exist
            if self.rect:
                self.canvas.delete(self.rect)
                
            # Schedule destruction after a short delay to avoid race conditions
            self.top.after(10, self.top.destroy)
        except Exception as e:
            logging.error(f"Error during selection window cleanup: {e}")
            # Make sure the window gets destroyed no matter what
            try:
                self.top.destroy()
            except:
                pass

def process_image(img):
    """Encode the image and (attempt to) call an OpenAI 'vision' model."""
    try:
        base64_image = encode_image_to_base64(img)
        
        # "gpt-4o-mini"
        response = openai.ChatCompletion.create(
            model="gpt-4o",
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
