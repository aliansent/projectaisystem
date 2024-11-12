import os
import json
import requests
import time
import openai
from openai import OpenAI
from route_mount import *
import generator_pages as gen_doc
from variables_use import *
import inspect
from functools import wraps

# Configure the OpenAI client with the API key
api_key = os.getenv('API_OPENAI')
openai.api_key = api_key

if not api_key:
    raise ValueError("OpenAI API key is not set in the environment variables.")

client = OpenAI(api_key=api_key)

# Ensure API_SUNO and API_LUMA are defined in variables_use or elsewhere
# For example:
API_SUNO = os.getenv('API_SUNO_KEY')
API_LUMA = os.getenv('API_SUNO_KEY')

def ignore_extra_kwargs(func):
    """
    Decorator to ignore extra parameters not defined in the function.
    """
    sig = inspect.signature(func)
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Filter kwargs to include only those that are in the signature
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
        return func(*args, **filtered_kwargs)
    return wrapper


class FunctionsCallingAvailable:    
    @staticmethod
    def video_generated(prompt_video, aspect_ratio="16:9"):
        """
        Generates a video using the Luma AI API.

        Args:
            prompt_video (str): Description of the video to generate.
            aspect_ratio (str, optional): Aspect ratio of the video. Defaults to "16:9".

        Returns:
            str: Video generation ID.
        """
        try:
            response = requests.post(
                "https://api.aimlapi.com/v2/generate/video/luma-ai/generation",
                headers={
                    "Authorization": f"Bearer {API_LUMA}",
                    "Content-Type": "application/json",
                },
                json={
                    "prompt": prompt_video,
                    "aspect_ratio": aspect_ratio,
                },
            )

            response.raise_for_status()
            data = response.json()
            print(data)
            generation_id = data.get("id")
            if not generation_id:
                print("No generation_id was received in the API response.")
                return None
            return generation_id
        except requests.exceptions.RequestException as e:
            print(f"Error generating video: {e}")
            return None

    @staticmethod
    @ignore_extra_kwargs
    def music_generated(music_lyrics, tags, title_song):
        """
        Generates music using the Suno AI API.

        Args:
            music_lyrics (str): Lyrics of the song.
            tags (list): List of tags related to the music.
            title_song (str): Title of the song.

        Returns:
            list: List of generated clip IDs.
        """
        try:
            response = requests.post(
                "https://api.aimlapi.com/v2/generate/audio/suno-ai/clip",
                headers={
                    "Authorization": f"Bearer {API_SUNO}",
                    "Content-Type": "application/json",
                },
                json={
                    "prompt": music_lyrics,
                    "tags": tags,
                    "title": title_song,
                },
            )

            response.raise_for_status()
            data = response.json()
            clip_ids = data.get("clip_ids", [])
            if not clip_ids:
                print("No clip_ids were received in the API response.")
            return clip_ids
        except requests.exceptions.RequestException as e:
            print(f"Error generating music: {e}")
            return []

    @staticmethod
    @ignore_extra_kwargs
    def generate_image(prompt, style=None, quality="standard", size="1024x1024", n=1):
        """
        Generates an image based on a prompt using the OpenAI API (DALL-E).

        Args:
            prompt (str): Description of the image to generate.
            style (str, optional): Style of the image (if applicable). Defaults to None.
            quality (str, optional): Quality of the image ('standard', 'high'). Defaults to 'standard'.
            size (str, optional): Size of the image (e.g., '1024x1024'). Defaults to '1024x1024'.
            n (int, optional): Number of images to generate. Defaults to 1.

        Returns:
            tuple: Confirmation message and URL of the generated image.
        """
        if not prompt:
            raise ValueError("The prompt cannot be empty")

        try:
            # Generate the image using the OpenAI client.
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=n,
            )

            # Get the URL of the first image.
            image_url = response.data[0].url

            # Return the message and the image URL.
            message = f"assistant: I have generated an image with the following description: {prompt}"
            return message, image_url
        except Exception as e:
            # Handle OpenAI API errors.
            print(f"Error generating image: {e}")
            return "assistant: An error occurred while generating the image.", ""

    @staticmethod
    @ignore_extra_kwargs
    def process_request_create_documents(title, context_instruction, content, images_insert_html):
        """
        Processes a request to create multiple documents and returns the generated HTML code.
        """
        try:
            instance_generate_new_doc = gen_doc.GenerateDocument(title, context_instruction, content, images_insert_html)
            Html_code = instance_generate_new_doc.generate_document()
            Html_code = Html_code.replace("```html", "").replace("```", "")
            return Html_code
        except Exception as e:
            return f"Error generating document: {str(e)}"

    @staticmethod
    @ignore_extra_kwargs
    def render_new_document_modified(code_html):
        """
        Renders a new modified document.

        Args:
            code_html (str): HTML code of the document.

        Returns:
            str: Rendered HTML code.
        """
        return code_html

    @staticmethod
    @ignore_extra_kwargs
    def edit_current_document(new_code_html_modified):
        """
        Processes and returns the modified HTML code.
        """
        return new_code_html_modified

    @staticmethod
    @ignore_extra_kwargs
    def recall_html(pseudo_args=None):
        return ""

class HtmlFormatOut:
        
    @staticmethod
    def video_out_format(generation_id):
        """
        Generates HTML to play the generated video.

        Args:
            generation_id (str): Video generation ID.

        Returns:
            str: HTML string containing video player.
        """
        max_wait_time = 300  # Maximum wait time in seconds
        wait_interval = 10   # Time to wait between checks in seconds
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            try:
                response = requests.get(
                    "https://api.aimlapi.com/v2/generate/video/luma-ai/generation",
                    params={
                        "generation_id": generation_id,
                        "status": "completed",
                    },
                    headers={
                        "Authorization": f"Bearer {API_LUMA}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                # Print the data response
                print(f"Generation {generation_id}:", data)
                
                state = data.get('state')
                if state == 'completed':
                    # Extract the video_url and build the HTML.
                    video_url = data.get('video_url')
                    if video_url:
                        html_player = f"""
            <div class="video-player">
                <h2>Play Video</h2>
                <video controls width="600">
                    <source src="{video_url}" type="video/mp4">
                    Your browser does not support the video element.
                </video>
            </div>
                        """
                        return html_player
                    else:
                        print(f"Video URL not found for generation ID: {generation_id}")
                        return ""
                elif state == 'failed':
                    print(f"Video generation failed for ID {generation_id}.")
                    return ""
                else:
                    print(f"Video generation status for ID {generation_id}: {state}. Waiting...")
                    time.sleep(wait_interval)
                    elapsed_time += wait_interval
            except requests.exceptions.RequestException as e:
                print(f"Error retrieving video data for generation ID {generation_id}: {e}")
                return ""
        
        print(f"Timeout reached while waiting for video generation ID {generation_id}.")
        return ""


    @staticmethod
    @ignore_extra_kwargs
    def recall_html(pseudo_args=None):
        return ""

    @staticmethod
    @ignore_extra_kwargs
    def music_out_format(music_ids_out):
        """
        Generates HTML to play the generated music tracks.

        Args:
            music_ids_out (list): List of music clip IDs.

        Returns:
            str: HTML string containing audio players.
        """
        html_gui = []  # Initialize outside the loop to accumulate all entries.

        for music_id in music_ids_out:
            try:
                response = requests.get(
                    "https://api.aimlapi.com/v2/generate/audio/suno-ai/clip",
                    params={
                        "clip_id": music_id,
                        "status": "streaming",
                    },
                    headers={
                        "Authorization": f"Bearer {API_SUNO}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()

                # Extract the audio_url and add it to the list.
                audio_url = data.get('audio_url')
                if audio_url:
                    html_player = f"""
        <div class="audio-player">
            <h2>Play Music</h2>
            <audio controls>
                <source src="{audio_url}" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
        </div>
                    """
                    html_gui.append(html_player)
                else:
                    print(f"Audio URL not found for clip ID: {music_id}")
            except requests.exceptions.RequestException as e:
                print(f"Error retrieving clip data for clip ID {music_id}: {e}")

        # Join all HTML entries into a single string.
        return '\n'.join(html_gui)

        
    @staticmethod
    @ignore_extra_kwargs
    def image_generated(msgsend, img_uri):
        """
        Generates HTML to display a generated image.

        Args:
            msgsend (str): Confirmation message.
            img_uri (str): URL of the generated image.

        Returns:
            str: HTML string displaying the image.
        """
        html_return = f'<div style="font-weight: lighter;">AI Answer:</div>{msgsend}<center><div class="content_img"><img src="{img_uri}" class="img_return"></div></center>'
        return html_return

    @staticmethod
    @ignore_extra_kwargs
    def gen_document(title, context_instruction, content, images_insert_html):
        """
        Generates a document using the GenerateDocument class from generator_pages.

        Args:
            title (str): Title of the document.
            context_instruction (str): Context instruction for creating the document.
            content (str): Content of the document.
            images_insert_html (str): HTML to insert images.

        Returns:
            str: HTML code of the generated document.
        """
        instance_generate_new_doc = gen_doc.GenerateDocument(title, context_instruction, content, images_insert_html)
        Html_code = instance_generate_new_doc.generate_document()
        try:
            Html_code = Html_code.replace("```html", "")
            Html_code = Html_code.replace("```", "")
        except Exception as e:
            print(f"Error processing the document's HTML: {e}")
        return Html_code

    @staticmethod
    @ignore_extra_kwargs
    def render_new_document_modified(code_html):
        """
        Renders a new modified document.

        Args:
            code_html (str): HTML code of the document.

        Returns:
            str: Rendered HTML code.
        """
        return code_html


functions_available = {
    "recall_html": FunctionsCallingAvailable.recall_html,
    "generate_image": FunctionsCallingAvailable.generate_image,
    "CreateNewDocument": FunctionsCallingAvailable.process_request_create_documents,
    "edit_current_document": FunctionsCallingAvailable.edit_current_document,
    "music_generated": FunctionsCallingAvailable.music_generated,
    "video_generated": FunctionsCallingAvailable.video_generated  # Added video_generated
}

functions_render_available = {
    "recall_html": HtmlFormatOut.recall_html,
    "generate_image": HtmlFormatOut.image_generated,
    "CreateNewDocument": HtmlFormatOut.gen_document,
    "edit_current_document": HtmlFormatOut.render_new_document_modified,
    "music_generated": HtmlFormatOut.music_out_format,
    "video_generated": HtmlFormatOut.video_out_format  # Added video_generated
}
