import os
import sys
import torch
from PIL import Image
from diffusers import StableDiffusionXLPipeline, AutoPipelineForText2Image

def generate_image(prompt, file_name):
    """
    Generates an image based on a provided text prompt and saves the image using the specified file name.

    :param prompt: The text prompt used for generating the image.
    :param file_name: The name of the file to save the generated image as.

    :return: None. The generated image is saved to a file.
    """    
    neg_prompt = "(worst quality, low quality, illustration, 3d, 2d, painting, cartoons, sketch)"
    #pipe = StableDiffusionXLPipeline.from_pretrained("segmind/Segmind-Vega", torch_dtype=torch.float16, use_safetensors=True, variant="fp16")
    pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sdxl-turbo", torch_dtype=torch.float16)
    pipe.to("cuda")
    image = pipe(prompt=prompt, negative_prompt=neg_prompt, num_inference_steps=5).images[0]





    # Save the image using the provided filename
    image.save(file_name)

# Function to generate and save the image from a prompt in a text file
def generate_image_from_prompt_file_and_return_filepath(prompt_file_path, save_file_name, artist="Hiroshi Sugimoto", pipe="NotSet",  STEPS = 5, save_dir="images"):
    """
    Generates an image based on a text prompt provided in a file and saves the generated image to a specified directory.

    :param prompt_file_path: The file path to the text file containing the prompt for the image generation.
    :param save_file_name: The name of the file to save the generated image as.
    :param artist: The name of the artist to emulate in the generated image. Default is "Mort Künstler".
    :param pipe: The pipeline (model) to use for the image generation. Default is "NotSet".
    :param STEPS: The number of steps or iterations for the image generation process. Default is 5.
    :param save_dir: The directory where the generated image will be saved. Default is "images".

    :return: The file path of the saved generated image.
    """
    prompt_file_path = prompt_file_path.replace('.png','.txt').replace('.mp4','.txt').replace('.wav','.txt').replace('_edited.wav','.txt')

    with open(prompt_file_path, 'r') as file:
        prompt = file.read().strip()
    current_image, pipe = make_image_and_return_filepath(prompt, save_file_name, artist=artist, pipe=pipe, save_dir=save_dir)
    return save_file_name, pipe

def make_image_and_return_filepath(prompt, file_name, artist="Mort Künstler", pipe="NotSet", STEPS = 5, save_dir="images"):
    """
    Generates an image based on a provided text prompt and saves the image to a specified directory.

    :param prompt: The text prompt used for generating the image.
    :param file_name: The name of the file to save the generated image as.
    :param artist: The name of the artist style to emulate in the generated image. Default is "Mort Künstler".
    :param pipe: The pipeline or model to use for the image generation. Default is "NotSet".
    :param STEPS: The number of steps or iterations for the image generation process. Default is 5.
    :param save_dir: The directory where the generated image will be saved. Default is "images".

    :return: The file path of the saved generated image.
    """
    #neg_prompt = "(worst quality, low quality, illustration, 3d, 2d, painting, cartoons, sketch)" # Negative prompt

    if pipe == "NotSet":
        #pipe = StableDiffusionXLPipeline.from_pretrained("segmind/Segmind-Vega", torch_dtype=torch.float16, use_safetensors=True, variant="fp16")
        pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sdxl-turbo", torch_dtype=torch.float16)
        pipe.to("cuda")
    image = pipe(prompt=f"art by {artist}, intricate detail, phone photograph: {prompt}", 
                 width=768,
                 height=768,
                 num_inference_steps=STEPS, 
                 strength=0.1 + 1 / STEPS, 
                 guidance_scale=0.0).images[0]
    
    image.save(os.path.join(save_dir, file_name))
    #image_byte_arr = io.BytesIO()
    #image.save(image_byte_arr, format='PNG')
    #image_data = image_byte_arr.getvalue()
    #return Image.open(io.BytesIO(image_data))
    return os.path.join(save_dir, file_name), pipe


if __name__ == "__main__":
    prompt = sys.argv[1]
    file_name = sys.argv[2]
    generate_image(prompt, file_name)
