import os
import json
from openai import OpenAI
from variables_use import model_generated_pages
def generate_html_document(html_code):
    return html_code

class computer_vision_module:
    def __init__(self, context_instruction, images_base64_computer_vision):
        self.instructions_to_transcribe = context_instruction
        self.client = OpenAI(api_key=os.getenv('API_OPENAI'))
        self.images_base64 = images_base64_computer_vision

    def generate_document(self):
        try:
            messages = self._create_messages()
            print("Messages created successfully:", messages)

            function_calling = [{
                "type": "function",
                "function": {
                    "name": "generate_html_document",
                    "description": "Generates an HTML document based on given input HTML code.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "html_code": {
                                "type": "string",
                                "description": "The complete HTML code including <script> and <style> tags."
                            }
                        },
                        "required": ["html_code"]
                    }
                }
            }]

            response = self.client.chat.completions.create(
                model="gpt-4o",  # Asegúrate de usar el modelo correcto
                messages=messages,
                tools=function_calling,
                tool_choice="auto"  # Permite que el modelo decida cuándo usar la función
            )

            print("Response received:", response)
            html_code = self._handle_response(response)
            print("HTML code generated successfully:", html_code)
            return html_code

        except Exception as e:
            print("Error in generate_document:", str(e))
            return "Error: Unable to generate document"

    def _create_messages(self):
        initial_content = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"""
You are a web developer. Recreate the images using HTML, CSS, and JavaScript. Each image should be a separate page within a div with class 'page'.
- Use semantic HTML5.
- Ensure clean and commented code.
- Use modern CSS (Flexbox, Grid).
- Make it responsive.
- Follow design principles (alignment, contrast, spacing).
- Choose a clean color palette and typography.
Details and instructions important: {self.instructions_to_transcribe}
                    """
                }
            ]
        }

        messages = [initial_content]

        if self.images_base64:
            for base64_image in self.images_base64:
                messages[0]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                })

        print("Final messages created:", messages)
        return messages

    def _handle_response(self, response):
        try:
            response_message = response.choices[0].message
            print("Response message:", response_message)
            tool_calls = response_message.tool_calls

            if tool_calls:
                for tool_call in tool_calls:
                    if tool_call.function.name == "generate_html_document":
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                            print("Function arguments parsed:", function_args)
                            return function_args.get("html_code", "")
                        except json.JSONDecodeError:
                            print("JSONDecodeError: Unable to parse function arguments")
                            return "Error: Unable to parse function arguments"
            else:
                # Si no hay tool_calls, buscar el contenido HTML en el mensaje
                for content in response_message.content:
                    if isinstance(content, dict) and content.get("type") == "text":
                        # Buscar código HTML en el texto
                        text = content.get("text", "")
                        print("Text content received:", text)
                        if "<html" in text and "</html>" in text:
                            start = text.find("<html")
                            end = text.find("</html>") + 7
                            return text[start:end]
                
                # Si no se encuentra código HTML, devolver un mensaje de error
                print("Error: No HTML code found in the response")
                return "Error: No HTML code found in the response"
        
        except Exception as e:
            print("Error in _handle_response:", str(e))
            return "Error: Unable to handle response"




class GenerateDocument:
    def __init__(self, title, context_instruction, content, images_insert_html):
        self.title = title
        self.context_instruction = context_instruction
        self.content = content        
        self.images_insert_html = images_insert_html
        self.client = OpenAI(api_key=os.getenv('API_OPENAI'))

    def generate_document(self):
        messages = self._create_messages()

        response = self.client.chat.completions.create(
            model=model_generated_pages,
            messages=messages,
            max_tokens=3000
        )

        html_code = self._handle_response(response)
        return html_code

    def _create_messages(self):
        initial_content = {
            "role": "user",
            "content": f"""
    Title: {self.title}
    Instruction: {self.context_instruction}

    Content:
    {self.content}

    Use these sources:
    {self.images_insert_html}
                """
            }

        messages = [initial_content]

        messages.append({
                "role": "user",
                "content": """
    
Please generate an HTML document that meets the following mandatory requirements:

- **Extensive and Detailed Content:** It is mandatory to generate a page with an extremely high level of detail, ensuring that the document appears full with a large amount of information and elements. Each piece of information must be extensively developed so that the page is rich in details and appears as a professional and complex design.
- **No Additional Information:** Do not invent any additional information that has not been provided by the user. All pieces of information in the document must be strictly based on the information given by the user. No data should be left blank.
- **Complex Design Elements:** Ensure that the design is extensive and includes many elements to complete a professional design. The page must include both visual and textual elements that make it rich and detailed, with well-differentiated sections for each part of the information. Add elements such as headers, lists, explanatory paragraphs, tables, and other components that contribute to a rich and complex design.
- **Information Distribution:** You must add line breaks between each element of the document, ensuring that the information is well distributed throughout the page vertically. This organization is crucial to guarantee clarity and readability of the information.
- **Direct HTML:** It is mandatory to create the HTML code of the document directly.

**Generated HTML Code:** The HTML code must be clear, clean, and well-structured, following HTML5 best practices. Use semantic tags (such as <header>, <section>, <footer>, etc.) to organize the content. Basic or inline CSS styles should be included to achieve an attractive visual presentation, but without inventing any additional information.

The final goal is to achieve a rich, content-filled page design that includes all possible details provided by the user, with a professional layout that invites reading and visual exploration. Please proceed now with creating the HTML code based on these instructions.
Ensure that the URLs for images, audio, or video on the webpage are placed within their respective <audio>, <img>, or <video> tags. Each URL should also be enclosed within an <a href> tag, corresponding to its specific media tag.

                """
            })
        return messages

    def _handle_response(self, response):
        response_message = response.choices[0].message
        
        content = str(response_message.content)
        print(content)
        if isinstance(content, str) and "<html" in content and "</html>" in content:
            start = content.find("<html")
            end = content.find("</html>") + len("</html>")
            return content[start:end].replace('\n', "")
        
        # Si no se encuentra código HTML, devolver un mensaje de error
        return "Error: No HTML code found in the response"

