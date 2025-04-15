import unittest
import tkinter as tk
from ui import SnippingToolApp

class TestUI(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.app = SnippingToolApp(self.root)

    def tearDown(self):
        self.root.destroy()

    def test_ui_initialization(self):
        self.assertIsNotNone(self.app.capture_button)
        self.assertIsNotNone(self.app.result_text)
        self.assertIsNotNone(self.app.image_label)

if __name__ == '__main__':
    unittest.main()
