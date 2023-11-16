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

MODEL_MAP = {
        0: "dall-e-2",
        }

# validate if config dir does exists and, if not, create it
def create_config_dir():
    if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)

# saves the openai api key in a json file
def save_openai_api_key(api_key):
    create_config_dir()
    j = {"api_key": api_key}
    with open(os.path.join(CONFIG_DIR, CONFIG_FILE_NAME), "w") as f: json.dump(j, f)

def mask_openai_api_key(api_key):
    if get_openai_api_key() == "": return ""
    return api_key[:2] + "*" * (len(api_key) - 4) + api_key[-2:]

def get_openai_api_key():
    # check if config file does exists, if does, read it and return the api key
    if os.path.exists(os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)):
        with open(os.path.join(CONFIG_DIR, CONFIG_FILE_NAME), "r") as f:
            return json.load(f).get("api_key", "")
    return ""

def send_request(image, layer, model, api_key, prompt, size, n):
    print("Preparing to send request...")

    if not pdb.gimp_edit_copy_visible(image) :
        return

    version = map(int, pdb.gimp_version().split('.'))
    if version[0] > 2 or version[0] == 2 and version[1] > 8:
        new_image = pdb.gimp_edit_paste_as_new_image()
    else:
        new_image = pdb.gimp_edit_paste_as_new()

    # Salvar a imagem temporariamente
    temp_path = "/tmp/temp_image.png"
    pdb.gimp_layer_add_alpha(new_image.layers[0])
    pdb.gimp_file_save(new_image, new_image.layers[0], temp_path, temp_path)
    # pdb.file_png_save_defaults(image, image.layers[0], temp_path, temp_path)
    
    print("Sending request to OpenAI API...")   
    print("Model: " + model)
    print("Prompt: " + prompt)
    print("Size: " + size)
    print("N: " + str(n))
    print("API Key: " + api_key)

    # Construir a chamada de API
    url = "https://api.openai.com/v1/images/edits"
    headers = {"Authorization": "Bearer " + api_key}
    files = {'image': open(temp_path, 'rb')}
    data = {
        'model': model,
        'prompt': prompt,
        'n': n,
        'size': size,
        'response_format': 'b64_json'
    }

    # Configurar o delimitador para a requisicao multipart/form-data
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    headers['Content-Type'] = 'multipart/form-data; boundary={}'.format(boundary)
    
    # Construir o corpo da requisicao multipart/form-data
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

    # save body to file for debugging
    with open("/tmp/body.txt", "w") as f:
        f.write(body)

    # Enviar a requisicao para a API usando urllib2
    request = urllib2.Request(url, body)
    for key, value in headers.items():
        request.add_header(key, value)

    print("Headers:")
    print(request.headers)
    

    print("Reading response...")
    try:
        response = urllib2.urlopen(request)
    except urllib2.HTTPError as e:
        with open("/tmp/error.txt", "w") as f:
            f.write(e.read())
        print("HTTPError: " + str(e.code))
        print(e.read())
        gimp.message("HTTPError: " + str(e.code))
        return

    # dumps response json to file for debugging
    # print("Saving response...")
    # response_dump_path = tempfile.mktemp(suffix=".json")
    # with open(response_dump_path, "w") as f:
    #     f.write(response.read())

    print(response)
    response = json.load(response)

    # with open(response_dump_path, "r") as f:
    #     response = json.load(f)

    # Salvar a imagem de saida
    print("Saving output image...")
    output_path = tempfile.mktemp()
    processed_images = []
    # Convert all base64 images to binary
    for idx, value in enumerate(response["data"]):
        img_decoded = b64decode(value["b64_json"])
        # save image to file 

        final_path = output_path + "-" + str(idx) + ".png"
        with open(output_path + "-" + str(idx) + ".png", "wb") as f:
            f.write(img_decoded)

        # add image to processed images list
        processed_images.append(final_path)

    # Adicionar a imagem de volta ao GIMP como uma nova camada
    for image_path in processed_images:
        new_layer = pdb.gimp_file_load_layer(new_image, image_path)
        pdb.gimp_image_insert_layer(new_image, new_layer, None, 0)

    # new_layer = pdb.gimp_file_load_layer(image, output_path)
    # pdb.gimp_image_insert_layer(image, new_layer, None, 0)

    # # Remover a camada temporaria
    # pdb.gimp_item_delete(new_layer)

    # Atualizar a exibicao do GIMP
    gimp.displays_flush()


def dall_e(image, layer, model, api_key, prompt):
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

    size = "512x512"
    n = 1
    send_request(image, layer, model, api_key, prompt, size, n)


register(
    "python_fu_dall-e_edit",
    "DALL-E plugin",
    "Edit and create images with the power of DALL-E",
    "Paulo Vinicius", "Paulo Vinicius", "2023",
    "Edit",
    "",
    [        
        (PF_IMAGE, "image", "Input image", None),
        (PF_LAYER, "layer", "Input layer", None),
        (PF_OPTION, "model", "Model", 0, (MODEL_MAP[0],)),
        (PF_STRING, "api_key", "OpenAI Key", mask_openai_api_key(get_openai_api_key())),
        (PF_TEXT, "prompt", "Prompt", " "),
    ],
    [],
    dall_e, 
    menu="<Image>/DALL-E"
)

main()
