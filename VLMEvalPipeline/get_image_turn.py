"""
Image Turn Extraction Utilities
------------------------------
This module provides functions to extract and process image turns from conversation data for different vision-language models. It is used to handle user turns that reference images in multi-modal evaluation pipelines.

Dependencies:
    - None (relies on standard Python and project-specific conventions)
"""
import base64
from mimetypes import guess_type
from PIL import Image
import os


# Function to encode a local image into data URL
def local_image_to_data_url(image_path):
    # Guess the MIME type of the image based on the file extension
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        mime_type = "application/octet-stream"  # Default MIME type if none is found

    # Read and encode the image file
    with open(image_path, "rb") as image_file:
        base64_encoded_data = base64.b64encode(image_file.read()).decode("utf-8")

    # Construct the data URL
    return f"data:{mime_type};base64,{base64_encoded_data}"


def get_img_turn_gpt4o(datarow, text_turn):
    image_path = datarow["MinedImages"]
    data_url = local_image_to_data_url(image_path)
    img_turn = {
        "role": "user",
        "content": [
            {"type": "text", "text": text_turn},
            {
                "type": "image_url",
                "image_url": {
                    "url": data_url,
                },
            },
        ],
    }
    return img_turn, None


def get_img_turn_phi3(datarow, text_turn):
    img_turn = {"role": "user", "content": "<|image_1|>\n" + text_turn.strip()}
    img_loaded = Image.open(datarow["MinedImages"])
    return img_turn, img_loaded


def get_img_turn_deepseek(datarow, text_turn):
    img_turn = {
        "role": "<|User|>",
        "content": "<image>\n<|ref|>" + text_turn.strip() + "<|/ref|>.",
        "images": [datarow["MinedImages"]],
    }
    return img_turn, "LoadedImage"


def get_img_turn_llama(datarow, text_turn):
    img_turn = {
        "role": "user",
        "content": [{"type": "image"}, {"type": "text", "text": text_turn.strip()}],
    }
    img_loaded = Image.open(datarow["MinedImages"])
    return img_turn, img_loaded


def get_img_turn_qwen(datarow, text_turn):
    # curr_path = os.path.dirname(os.path.abspath(__file__)) + "/"
    img_turn = {
        "role": "user",
        "content": [
            {"type": "image", "image": "file://" + datarow["MinedImages"]},
            {"type": "text", "text": text_turn.strip()},
        ],
    }
    return img_turn, "LoadedImage"


def get_img_turn_llava(datarow, text_turn):
    img_turn = {
        "role": "user",
        "content": [{"type": "text", "text": text_turn.strip()}, {"type": "image"}],
    }
    img_loaded = Image.open(datarow["MinedImages"])
    return img_turn, img_loaded


def get_img_turn_pixtral(datarow, text_turn):
    image_path = datarow["MinedImages"]
    data_url = local_image_to_data_url(image_path)
    img_turn = {
        "role": "user",
        "content": [
            {"type": "text", "text": text_turn.strip()},
            {"type": "image_url", "image_url": {"url": data_url}},
        ],
    }
    return img_turn, None
