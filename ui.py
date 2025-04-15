import sys
import time
import tkinter as tk
from PIL import ImageGrab, Image, ImageTk
import logging
from utils import get_virtual_screen_rect
from image_processing import encode_image_to_base64, process_image_with_openai
from formatter import format_and_insert_text
from config import DISPLAY_SIZE, TEXT_WIDGET_CONFIG

class SelectionWindow:
    """
    A fullscreen overlay that allows the user to drag a rectangle
    to select an area of the screen.
    """
    def __init__(self, master):
        if sys.platform.startswith('win'):
            virtual_screen = get_virtual_screen_rect()
            self.screen_x, self.screen_y, self.screen_width, self.screen_height = virtual_screen
            logging.info("Virtual screen dimensions: %s", virtual_screen)
        else:
            self.screen_x = 0
            self.screen_y = 0
            self.screen_width = master.winfo_screenwidth()
            self.screen_height = master.winfo_screenheight()

        self.top = tk.Toplevel(master)
        self.top.wm_overrideredirect(True)
        self.top.geometry(f"{self.screen_width}x{self.screen_height}+{self.screen_x}+{self.screen_y}")
        self.top.attributes('-alpha', 0.3)
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
            logging.info("Selected area: %s", self.bbox)
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
            logging.error("Error during cleanup: %s", e)
            try:
                self.top.destroy()
            except:
                pass

class SnippingToolApp:
    """
    The main application class that sets up the UI and manages the snipping logic.
    """
    def __init__(self, master):
        self.master = master
        master.title("Snipping Tool with OpenAI Vision")
        self.is_snipping = False

        # Main frame for image and text display.
        self.main_frame = tk.Frame(master)
        self.main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Image display area.
        self.image_frame = tk.Frame(self.main_frame)
        self.image_frame.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
        self.image_label = tk.Label(self.image_frame, text="Captured Image")
        self.image_label.pack(pady=5)

        # Text display area.
        self.text_frame = tk.Frame(self.main_frame)
        self.text_frame.pack(side=tk.RIGHT, padx=5, fill=tk.BOTH, expand=True)
        self.text_label = tk.Label(self.text_frame, text="Vision API Response")
        self.text_label.pack(pady=5)

        # Text widget to display formatted output.
        self.result_text = tk.Text(self.text_frame, **TEXT_WIDGET_CONFIG)
        self.result_text.pack(pady=5, fill=tk.BOTH, expand=True)
        self.configure_text_tags()

        # Button to capture an area.
        self.capture_button = tk.Button(master, text="Snip Area", command=self.capture_area)
        self.capture_button.pack(pady=10)

    def configure_text_tags(self):
        self.result_text.tag_configure("heading", font=("Helvetica", 14, "bold"))
        self.result_text.tag_configure("subheading", font=("Helvetica", 12, "bold"))
        self.result_text.tag_configure("list", lmargin1=20, lmargin2=40)
        self.result_text.tag_configure("code", font=("Courier", 10), background="#f0f0f0")
        self.result_text.tag_configure("bold", font=("Helvetica", 10, "bold"))

    def display_image(self, image):
        """
        Resize and display the captured image.
        """
        image.thumbnail(DISPLAY_SIZE)
        photo = ImageTk.PhotoImage(image)
        self.image_label.config(image=photo)
        self.image_label.image = photo  # Prevent garbage collection.

    def process_image(self, img):
        base64_image = encode_image_to_base64(img)
        answer = process_image_with_openai(img, base64_image)
        format_and_insert_text(self.result_text, answer)

    def capture_area(self):
        """
        Hides the main window, lets the user select an area via a fullscreen overlay,
        captures that area, and then processes the image.
        """
        if self.is_snipping:
            return
        self.is_snipping = True
        try:
            self.master.withdraw()
            self.master.update()
            time.sleep(0.3)
            selection = SelectionWindow(self.master)
            self.master.wait_window(selection.top)
            time.sleep(0.1)
            self.master.deiconify()
            self.master.update()
            if selection.bbox:
                try:
                    from PIL import ImageGrab
                    logging.info("Capturing area: %s", selection.bbox)
                    img = ImageGrab.grab(bbox=selection.bbox)
                    img.save("debug_capture.png")
                    self.display_image(img)
                    self.process_image(img)
                except Exception as e:
                    error_message = f"Error capturing image: {e}"
                    logging.error(error_message)
                    self.result_text.delete(1.0, tk.END)
                    self.result_text.insert(tk.END, error_message)
        finally:
            self.is_snipping = False
