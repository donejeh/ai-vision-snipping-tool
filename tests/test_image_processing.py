import unittest
from PIL import Image
from image_processing import encode_image_to_base64

class TestImageProcessing(unittest.TestCase):
    def test_encode_image(self):
        # Create a simple image for testing.
        img = Image.new('RGB', (10, 10), color='red')
        encoded = encode_image_to_base64(img)
        self.assertIsInstance(encoded, str)
        self.assertTrue(len(encoded) > 0)

if __name__ == '__main__':
    unittest.main()
