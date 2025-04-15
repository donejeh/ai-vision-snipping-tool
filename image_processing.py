import base64
from io import BytesIO
import openai
import logging
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def encode_image_to_base64(image):
    """
    Convert a PIL image to a base64-encoded PNG string.
    """
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def process_image_with_openai(img, base64_image):
    """
    Calls the OpenAI API with the provided image data and returns the response text.
    """
    try:
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
                                "2. Examine the extracted text and explain any problems or questions.\n"
                                "3. Use markdown-like formatting for clarity:\n"
                                "   - Headings: '### Heading'\n"
                                "   - Subheadings: '## Subheading'\n"
                                "   - Lists: '- Item'\n"
                                "   - Code blocks: ```code```\n"
                                "   - Inline bold: '**bold**'\n"
                                "4. Return the final answer in plain text."
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
        logging.info("OpenAI response: %s", answer)
        return answer
    except Exception as e:
        error_message = f"Error processing image: {e}"
        logging.error(error_message)
        return error_message
