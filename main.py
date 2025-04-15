from utils import set_dpi_awareness
from ui import SnippingToolApp
import tkinter as tk

def main():
    set_dpi_awareness()
    root = tk.Tk()
    app = SnippingToolApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
