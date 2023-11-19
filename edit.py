#! /bin/env python

from gimpfu import *
import os
import json
import urllib2
import urllib
from base64 import b64decode
import mimetypes
import tempfile

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "gimp-dall-e")
CONFIG_FILE_NAME = "openai_key.json"
API_PATH = "https://api.openai.com/v1/images/edits"
IMAGE_MAX_SIZE_MB=3.99
MODEL_MAP = { 0: "dall-e-2" }
IMAGES_POSSIBLE_SIZE = {
        "256x256": "256x256",
        "512x512": "512x512",
        "1024x1024": "1024x1024",
        }

# validate if config dir does exists and, if not, create it
def create_config_dir():
    if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)

# saves the openai api key in a json file
def save_openai_api_key(api_key):
    """
    Saves the OpenAI API key in a JSON file.
    Args:
        api_key: the OpenAI API key
    Returns:
        None
    """

    create_config_dir()
    j = {"api_key": api_key}
    with open(os.path.join(CONFIG_DIR, CONFIG_FILE_NAME), "w") as f: json.dump(j, f)

def mask_openai_api_key(api_key):
    """
    Masks the OpenAI API key.
    Args:
        api_key: the OpenAI API key
    Returns:
        The masked OpenAI API key
    """

    if get_openai_api_key() == "": return ""
    return api_key[:2] + "*" * (len(api_key) - 4) + api_key[-2:]

def get_openai_api_key():
    """
    Returns the OpenAI API key.
    Args:
        None
    Returns:
        The OpenAI API key
    """

    if os.path.exists(os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)):
        with open(os.path.join(CONFIG_DIR, CONFIG_FILE_NAME), "r") as f:
            return json.load(f).get("api_key", "")
    return ""

def get_file_size(fp): return (os.path.getsize(fp)/(1024 ** 2))

def reduce_until_size_met(image, drawable, scale_factor, temp_filename):
    """
    Reduces the image size until it fits the max size.
    Args:
        image: the image to resize
        drawable: the drawable to resize
        scale_factor: the scale factor to use
        temp_filename: the temporary filename to use
    Returns:
        None
    """
    current_size = get_file_size(temp_filename)
    while current_size > IMAGE_MAX_SIZE_MB:
        new_width = int(drawable.width * scale_factor)
        new_height = int(drawable.height * scale_factor)
        pdb.gimp_image_scale(image, new_width, new_height)

        pdb.file_jpeg_save(image, drawable, temp_filename, temp_filename, 0.85, 0, 1, 0, "", 0, 0, 0, 0)
        current_size = get_file_size(temp_filename)

def resize_to_match(image_to_resize, reference_image_layer):
    """
    Resizes the image to match the reference image layer.
    Args:
        image_to_resize: the image to resize
        reference_image_layer: the reference image layer
    Returns:
        None
    """
    ref_width = pdb.gimp_drawable_width(reference_image_layer)
    ref_height = pdb.gimp_drawable_height(reference_image_layer)

    pdb.gimp_image_scale(image_to_resize, ref_width, ref_height)

def send_request(image_path, model, api_key, prompt, size, n):
    """
    Sends the request to the OpenAI API.
    Args:
        image_path: the path to the image
        model: the model to use
        api_key: the OpenAI API key
        prompt: the prompt to use
        size: the size of the image
        n: the number of completions
    Returns:
        None
    """
    print("Preparing to send request...")
    pdb.gimp_progress_set_text("Preparing to send request...")

    url = API_PATH
    headers = {"Authorization": "Bearer " + api_key}
    files = {'image': open(image_path, 'rb')}
    data = {
        'model': model,
        'prompt': prompt,
        'n': n,
        'size': size,
        'response_format': 'b64_json'
    }

    # set the content type to multipart/form-data
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    headers['Content-Type'] = 'multipart/form-data; boundary={}'.format(boundary)
    
    body = ""
    for key, value in data.items():
        body += "--{}\r\n".format(boundary)
        body += 'Content-Disposition: form-data; name="{}"\r\n\r\n'.format(key)
        body += "{}\r\n".format(value)
    for key, value in files.items():
        filename = value.name
        file_content = value.read()
        mime_type, encoding = mimetypes.guess_type(filename)
        body += "--{}\r\n".format(boundary)
        body += 'Content-Disposition: form-data; name="{}"; filename="{}"\r\n'.format(key, filename)
        body += 'Content-Type: {}\r\n\r\n'.format(mime_type or 'application/octet-stream')
        body += file_content + "\r\n"

    body += "--{}--\r\n".format(boundary)

    request = urllib2.Request(url, body)
    for key, value in headers.items():
        request.add_header(key, value)
    
    pdb.gimp_progress_set_text("Reading response...")
    try:
        response = urllib2.urlopen(request)
    except urllib2.HTTPError as e:
        with open("/tmp/error.txt", "w") as f:
            f.write(e.read())
        print("HTTPError: " + str(e.code))
        bad_response = json.load(e.read())
        print(e.read())
        gimp.message("Error: " + bad_response["error"]["message"])
        return

    response = json.load(response)

    print("Saving output image...")
    pdb.gimp_progress_set_text("Saving output image...")
    out_prefix = tempfile.mktemp()
    processed_images = []

    # Convert all base64 images to binary
    for idx, value in enumerate(response["data"]):
        img_decoded = b64decode(value["b64_json"])
        final_path = out_prefix + "-" + str(idx) + ".png"
        with open(final_path, "wb") as f:
            f.write(img_decoded)

        processed_images.append(final_path)
    return processed_images

def extract_dalle_completions(original_image, filled_image_path, selection_coordinates):
    """
    Extracts the selected region from the filled image and pastes it in the original image.
    Args:
        original_image: the image with the selection
        filled_image_path: the image with the filled region
        selection_coordinates: the coordinates of the selection in the original image
    Returns:
        None
    """
    x1, y1, x2, y2 = selection_coordinates

    # load the filled image
    filled_image = pdb.gimp_file_load(filled_image_path, filled_image_path)
    pdb.gimp_layer_add_alpha(filled_image.active_layer)
    
    # resize the filled image to match the original image
    resize_to_match(filled_image, original_image.layers[0])

    width = x2 - x1
    height = y2 - y1

    pdb.gimp_image_select_rectangle(filled_image, CHANNEL_OP_REPLACE, x1, y1, width, height)

    # invert the selection and clear it
    pdb.gimp_selection_invert(filled_image)
    pdb.gimp_edit_clear(filled_image.layers[0])

    pdb.gimp_file_save(filled_image, filled_image.layers[0], filled_image_path, filled_image_path)

def process_image(image, drawable, model, api_key, prompt, size, n):
    """
    Process the image and paste the result in the original image.
    Args:
        image: the original image
        drawable: the original drawable
        model: the model to use
        api_key: the OpenAI API key
        prompt: the prompt to use
        size: the size of the image
        n: the number of completions
    Returns:
        None
    """
    # check if there is a selection
    if pdb.gimp_selection_is_empty(image):
        gimp.message("Please, select a region first.")
        return

    if not pdb.gimp_drawable_has_alpha(drawable):
        pdb.gimp_layer_add_alpha(drawable)

    _, x1, y1, x2, y2 = pdb.gimp_selection_bounds(image)

    selection_coordinates = [x1, y1, x2, y2]

    # copy the selected region to a new image
    image_copy = pdb.gimp_image_duplicate(image)
    pdb.gimp_layer_resize_to_image_size(image_copy.layers[0])
    drawable_copy = pdb.gimp_image_get_active_drawable(image_copy)
    pdb.gimp_edit_clear(drawable_copy)

    image_with_space = tempfile.mktemp() + ".png"
    pdb.gimp_file_save(image_copy, drawable_copy, image_with_space, image_with_space, run_mode=1)

    # if image is too big, reduce it until it fits the max size
    if get_file_size(image_with_space) > IMAGE_MAX_SIZE_MB:
        gimp.message("Image is too big. Resizing...")
        reduce_until_size_met(image, drawable, 0.9, image_with_space)

    # send request to openai
    processed_images = send_request(image_with_space, model, api_key, prompt, size, n)
    os.remove(image_with_space)

    for path in processed_images:
        # extract the selected region from the filled image and paste it in the original image
        extract_dalle_completions(image, path, selection_coordinates)
        new_layer = pdb.gimp_file_load_layer(image, path)
        pdb.gimp_image_insert_layer(image, new_layer, None, -1)
        os.remove(path)

    # update the image
    pdb.gimp_displays_flush()

def dall_e(image, layer, model, size, api_key, prompt):
    model = MODEL_MAP[model]
    print("DALL-E plugin started...")

    if api_key[:3] == "sk*":
        print("Using saved OpenAI API key.")
        api_key = get_openai_api_key()
    elif api_key == "":
        print("No OpenAI API key set.")
        gimp.message("You need to set your OpenAI API key first.")
        return
    elif api_key[:2] != "sk":
        print("Invalid OpenAI API key.")
        gimp.message("Invalid OpenAI API key.")
        return
    else:
        print("Saving OpenAI API key.")
        save_openai_api_key(api_key)

    n = 1
    process_image(image, layer, model, api_key, prompt, size, n)


register(
    "python_fu_dall-e_edit",
    "DALL-E plugin",
    "Edit and create images with the power of DALL-E",
    "Paulo Vinicius", "Paulo Vinicius", "2023",
    "Edit",
    "",
    [        
        (PF_IMAGE, "image", "Input image", None),
        (PF_DRAWABLE, "drawable", "Input drawable", None),
        (PF_OPTION, "model", "Model", 0, tuple(MODEL_MAP.values())),
        (PF_RADIO, "size", "Image size", "512x512", tuple(IMAGES_POSSIBLE_SIZE.items())),
        (PF_STRING, "api_key", "OpenAI Key", mask_openai_api_key(get_openai_api_key())),
        (PF_TEXT, "prompt", "Prompt", " "),
    ],
    [],
    dall_e, 
    menu="<Image>/DALL-E"
)

main()
