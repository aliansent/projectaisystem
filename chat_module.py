import json
import os
from pathlib import Path
import tiktoken
from openai import OpenAI
from functions_calling_module import *
import time
from generator_pages import *
from db_module import *
import requests

# Configure the OpenAI client with the API key delete_balance functions_render_available
api_key = os.getenv('API_OPENAI')
client = OpenAI(api_key=api_key)
encoding = tiktoken.encoding_for_model("gpt-4")

class gpt_run_session:
    def __init__(self, hahschat, balance_session, price_per_tokenGPT, price_per_img_GEN, balance_amount, instruction_minimalist=''):
        self.hash_session = hahschat
        self.instance_gpt = balance_session['session_thread']
        self.name_instance = balance_session['configs_gpts']['name_instance']
        self.function_minimalist_instruct = balance_session['configs_gpts']['function_minimalist_instruct']
        self.id_gpt_version = balance_session['configs_gpts']['id_gpt_version']
        self.price_per_token = 0.0000006
        self.pay_per_gpt = float(0.01)
        self.tokens_usage = 0
        self.run = None
        self.img_tokens_generated = 0
        self.instruction_minimalist = instruction_minimalist
        self.images_base64_computer_vision = []
        self.return_html_object = None
        self.current_document = ""
        self.return_html_final = None
        self.ejecute_vision_task = False
        self.type_of_action = None  # Añadido para rastrear el tipo de acción

    def call_function(self, function_name, *args, **kwargs):
        if function_name in functions_available:
            return functions_available[function_name](*args, **kwargs)
        else:
            raise ValueError("Function not available.")

    def functions_render_html(self, function_name, *args, **kwargs):
        if function_name in functions_render_available:
            render_html_code = functions_render_available[function_name](*args, **kwargs)
            self.return_html_final = render_html_code  # Asignar a self.return_html_final
            token_count = len(encoding.encode(render_html_code))
            return self.return_html_final  # Retornar self.return_html_final
        else:
            raise ValueError("Function render html out not available.")

    def process_tool_call(self, tool_call):
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        try:
            # Llamar a la función
            print(arguments)
            if isinstance(arguments, dict):
                output = self.call_function(function_name, **arguments)
            else:
                output = self.call_function(function_name, *arguments)
            
            # Asignar el tipo de acción basado en el nombre de la función
            if function_name in ["CreateNewDocument", "edit_current_document"]:
                self.type_of_action = "render_page_preview"
            elif function_name == "generate_image":
                self.type_of_action = "image_generated"
            elif function_name == "music_generated":
                self.type_of_action = "music_generated"
           
            # Procesar el resultado
            if function_name in ["CreateNewDocument", "edit_current_document"]:
                # La función ha retornado el código HTML directamente
                self.return_html_object = output
                self.return_html_final = self.return_html_object
                # Actualizar el conteo de tokens utilizados
                token_count = len(encoding.encode(str(self.return_html_object)))
                self.tokens_usage += token_count * self.price_per_token
                return self.return_html_object
            else:
                # Para otras funciones que necesitan renderizado
                if isinstance(output, tuple):
                    # Para funciones que retornan múltiples valores (como generate_image)
                    message, additional_data = output
                    out = self.functions_render_html(function_name, message, additional_data)
                elif isinstance(output, dict):
                    # Para funciones que retornan diccionarios
                    out = self.functions_render_html(function_name, **output)
                else:
                    # Para funciones que retornan cadenas u otros tipos
                    out = self.functions_render_html(function_name, output)
                # Asignar el valor 'out' a self.return_html_final
                self.return_html_final = out
                # Actualizar el conteo de tokens utilizados
                token_count = len(encoding.encode(str(self.return_html_final)))
                self.tokens_usage += token_count * self.price_per_token
                return self.return_html_final
        except Exception as e:
            return f"A problem occurred: {str(e)}"

    def check_new_msg(self):
        while self.run.status not in ['completed', 'requires_action']:
            self.run = client.beta.threads.runs.retrieve(
                thread_id=self.instance_gpt.id,
                run_id=self.run.id
            )
            time.sleep(1)

        if self.run.status == 'completed':
            messages = client.beta.threads.messages.list(
                thread_id=self.instance_gpt.id
            )
            for message in messages.data:
                if message.role == 'assistant':
                    return message.content[0].text.value
        elif self.run.status == 'requires_action':
            tool_outputs = []
            for tool_call in self.run.required_action.submit_tool_outputs.tool_calls:
                output = self.process_tool_call(tool_call)
                print("**** " * 16)
                print(output)
                print("**** " * 16)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": str(output)
                })

            if tool_outputs:
                try:
                    self.run = client.beta.threads.runs.submit_tool_outputs(
                        thread_id=self.instance_gpt.id,
                        run_id=self.run.id,
                        tool_outputs=tool_outputs
                    )

                    return self.check_new_msg()
                except Exception as e:
                    print(f"Error sending tool outputs: {e}")
                    return "An error occurred while processing the request."

    def push_new_msg_user(self, msg_user, AudioReturn, images_base64):
        self.return_html_final = None
        self.images_base64_computer_vision = images_base64
        self.type_of_action = None  # Reiniciar tipo de acción

        if float(self.tokens_usage) + self.img_tokens_generated >= self.pay_per_gpt:
            return "This session has expired due to extensive use, please log in again to continue chatting with MINI AI", None, None, None

        if self.ejecute_vision_task == True:
            return "I am still transcribing, please give me a moment, I need some time to finish creating the document...", None, None, None

        if len(self.images_base64_computer_vision) > 0:
            self.img_tokens_generated += len(self.images_base64_computer_vision) * 0.00128
            vision_module = computer_vision_module(msg_user, self.images_base64_computer_vision)
            if not self.ejecute_vision_task:
                self.ejecute_vision_task = True
                self.return_html_object = vision_module.generate_document()
                token_count = len(encoding.encode(self.return_html_object))
                self.tokens_usage += token_count * 0.000015
                self.return_html_object = self.return_html_object.replace("```html", "").replace("```", "").replace("\n", "")
                self.return_html_final = self.return_html_object
                self.ejecute_vision_task = False
                self.type_of_action = "render_page_preview"  # Corrected action type

                return (
                    "I have completed the transcription you requested. If there is anything else you need or more information to include, feel free to let me know. I'm here to assist you with whatever you need.",
                    None,
                    self.return_html_object,
                    self.type_of_action
                )
            else:
                return "I am still transcribing, please give me a moment, I need some time to finish creating the document...", None, None, None

        if self.run and self.run.status not in ['completed', 'requires_action']:
            return "Another run is currently active. Please wait until it's completed.", None, "", None

        message = client.beta.threads.messages.create(
            thread_id=self.instance_gpt.id,
            role="user",
            content=msg_user + ". It is mandatory that you always use your retrieval knowledge. Check the uploaded files and follow the instructions in the uploaded files. It is mandatory."
        )

        self.run = client.beta.threads.runs.create(
            thread_id=self.instance_gpt.id,
            assistant_id=self.id_gpt_version,
            instructions=self.function_minimalist_instruct
        )

        msg_respond = self.check_new_msg()

        if msg_respond is None:
            return "No response from the assistant.", None, "", None

        token_count = len(encoding.encode(msg_user))
        self.tokens_usage += token_count * self.price_per_token

        audio_generate = None  # Replace with the logic for generating audio

        return msg_respond, audio_generate, self.return_html_final, self.type_of_action

    def handle_user_interruption(self, msg_user):
        return "I am still working on creating your document, please give me a moment.", None, None, None

# json_configurations
