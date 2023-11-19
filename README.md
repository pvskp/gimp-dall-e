# DALL-E GIMP Plugin

## Overview

This repository contains a GIMP plugin for integrating with OpenAI's DALL-E service, a powerful AI model that can generate and edit images based on textual descriptions. The plugin offers two main functionalities: creating new images and editing existing ones using DALL-E's capabilities.

## Features

- **Edit existing images**: Select a region in an image and use DALL-E to fill or modify that region based on a given prompt.
- **Create new images**: Generate entirely new images based on textual prompts, offering various customization options like image size, style, and quality.
- **Configurable models**: Choose between different DALL-E models for varied results.

## Requirements

- GIMP (version 2.10 or later recommended)
- Active OpenAI API key
- Python 2.7, once this is the only one currently supported by stable GIMP.

## Installation

To install the DALL-E GIMP Plugin, follow these steps:

1. Ensure you have GIMP installed on your system.
2. Clone this repository or download the source code.
3. Copy the plugin files (`dall-e_edit.py` and `dall-e_create.py`) to your GIMP plugin directory. Typically, this directory is located at `~/.config/GIMP/2.10/plug-ins` on Linux or `C:\Users\YourUsername\AppData\Roaming\GIMP\2.10\plug-ins` on Windows.
4. Restart GIMP to load the new plugin.

## Usage

### Setting Up

Before using the plugin, you need to set your OpenAI API key:

1. Go to `DALL-E` in the GIMP menu.
2. Enter your OpenAI API key when prompted.

### Editing Images

1. Open an image in GIMP.
2. Select a region you wish to edit.
3. Navigate to `DALL-E -> Edit` in the GIMP menu.
4. Enter your desired prompt and adjust settings like model and image size.
5. Click `OK` to start the editing process.

### Creating Images

1. Navigate to `DALL-E -> Create` in the GIMP menu.
2. Enter your desired prompt and adjust settings like model, image size, style, and quality.
3. Click `OK` to generate a new image.

## Known Limitations

- Large images: Until now (11/2023), DALL-E OpenAI API's does not support images with size > 4mb. So, to allow the user to edit it's image anyway, this plugin tries, incrementally, to reduce the size of the image, affecting the final result.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

pvskp

## Contributing

Contributions to the DALL-E GIMP Plugin are welcome. Please feel free to fork the repository, make changes, and submit pull requests.

## Support

If you encounter any issues or have suggestions, please open an issue in this GitHub repository.
