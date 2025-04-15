import sys
import ctypes
import logging

# Set up logging.
logging.basicConfig(
    filename='vision.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def set_dpi_awareness():
    """Make the process DPI-aware on Windows."""
    if sys.platform.startswith('win'):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Windows 8.1+
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()       # Fallback for older Windows

def get_virtual_screen_rect():
    """
    Return the dimensions of the entire virtual screen (across all monitors)
    on Windows.
    """
    if sys.platform.startswith('win'):
        user32 = ctypes.windll.user32
        x = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
        y = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
        width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
        height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
        return (x, y, width, height)
    else:
        return (0, 0, 800, 600)  # Fallback values for non-Windows systems.
