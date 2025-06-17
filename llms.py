import requests
from dotenv import load_dotenv
import os
import json
from typing import List, Dict, Any, Optional, Union
import base64

prompt_template = """
You are a helpful assistant for the 'Tools in Data Science' course. A user will ask a question, and you will receive relevant context about the course to help answer it.

Your job is to:
- Provide a concise, factual, and helpful answer using only the provided context.
- If no answer can be confidently given from the context, return an empty string ("") as the answer.
- Use the `generate_structured_response` tool to respond, which requires:
  - `answer`: a short plain-English answer (no markdown)
  - `links`: URLs of the context, with a short justification for each

Respond ONLY by calling the `generate_structured_response` function. Do not generate any text directly.
"""

image_prompt = (
    "You are a visual assistant. Given an image, describe its content clearly and concisely in 2–3 plain English sentences. "
    "Focus on identifying the scene, objects, actions, or any relevant text. Do not speculate or make assumptions. "
    "Your response should help someone understand what the image shows without seeing it."
)

prompt_template_2 = f"""
You are an assistant for the 'Tools in Data Science' course. Given a question and context, respond with:

- A concise, accurate answer in plain English (no markdown or formatting).
- in JSON format.
"""

tools = [{
    "type": "function",
    "function": {
        "name": "generate_structured_response",
        "description": "Generate a structured response with an answer and URLs of the contexts used",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "The answer to the user's question"
                },
                "links": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string", 
                                "description": "URL of the context used"
                            },
                            "text": {
                                "type": "string",
                                "description": "Very brief justification of why this source is relevant to the answer"
                            }
                        }
                    },
                    "description": "Relevant sources that support the answer"
                }
            },
            "required": ["answer"]
        }
    }
}]

load_dotenv()

class OpenRouter:
    def __init__(self, model: str = "mistralai/mistral-small-3.1-24b-instruct:free"):
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        }

    def get_image_description(self, image: str) -> str:
        """
        Get a description of the image using the OpenRouter API.

        Args:
            image (str): Base64-encoded image string.

        Returns:
            str: The description of the image.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": image_prompt},{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}}]}
            ]
        }
        response = requests.post(self.url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    
    def generate_answer(self, question: str, context: str) -> str:
        """
        Generate an answer to a question using the OpenRouter API.

        Args:
            question (str): The question to answer.
            context (str): Context to help answer the question.

        Returns:
            str: The generated answer.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt_template},
                {"role": "user", "content": [{"type": "text", "text": question}]},
                {"role": "assistant", "content": [{"type": "text", "text": context}]}
            ],
            "tools": tools,
            "tool_choice": "required"
        }
        response = requests.post(self.url, headers=self.headers, json=payload)
        response.raise_for_status()
        print(f"[DEBUG] OpenRouter response text: {response.text}") 
        return response.json()['choices'][0]['message']['tool_calls'][0]['function']['arguments']

class Nomic:
    def __init__(self, model: str = "nomic-embed-text-v1.5"):
        self.model = model
        self.url = "https://api-atlas.nomic.ai/v1/embedding/text"  # Removed comma here
        self.headers = {
            "Authorization": f"Bearer {os.environ.get('NOMIC_API_KEY')}",
            "Content-Type": "application/json"
        }

    def get_embedding(self, text: str) -> list:
        """
        Gets the embedding for a given text using the Nomic API.

        Args:
            text (str): The text to embed.

        Returns:
            list: The embedding vector.
        """
        payload = {
            "model": self.model,
            "task_type": "search_document",
            "texts": [text]
        }
        response = requests.post(self.url, headers=self.headers, json=payload)
        print(f"[DEBUG] Nomic API response status code: {response.status_code}")
        return response.json()['embeddings'][0]
    
    def get_batch_embedding(self, texts: list) -> list:
        """
        Gets embeddings for a batch of texts using the Nomic API.

        Args:
            texts (list): List of texts to embed.

        Returns:
            list: List of embedding vectors.
        """
        payload = {
            "model": self.model,
            "task_type": "search_document",
            "texts": texts
        }
        response = requests.post(self.url, headers=self.headers, json=payload)
        return response.json()['embeddings']

class OpenAI:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {os.environ.get('AIPROXY_TOKEN')}",
            "Content-Type": "application/json"
        }
    
    def generate_response(self, question: str, context: List[Dict[str, str]] = None, 
                         image_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a structured response with answer and links using OpenAI's function calling capabilities.
        
        Args:
            question (str): User's question
            context (List[Dict]): List of context documents with 'text' and 'url' fields
            image_path (str, optional): Path to an image file if provided
            
        Returns:
            Dict: Structured response with answer and links
        """
        print(f"[DEBUG] generate_response: Starting with question: '{question[:50]}...'")
        print(f"[DEBUG] generate_response: Context provided: {len(context) if context else 0} items")
        print(f"[DEBUG] generate_response: Image path: {image_path}")
        
        # Create system message
        system_message = "You are a helpful teaching assistant. Answer questions based on the context provided."
        
        # Add image description to system message if an image is provided
        if image_path:
            try:
                print(f"[DEBUG] generate_response: Getting image description for: {image_path}")
                image_description = self.get_image_description(image_path)
                print(f"[DEBUG] generate_response: Got image description, length: {len(image_description)}")
                system_message += "\n\nThe user has provided an image. Here is a detailed description of that image:\n\n"
                system_message += image_description
                system_message += "\n\nUse this image description along with any other context to answer the user's question."
            except Exception as e:
                print(f"[DEBUG] generate_response: Error getting image description: {str(e)}")
                print(f"[DEBUG] generate_response: Error type: {type(e).__name__}")
        
        print(f"[DEBUG] generate_response: Final system message length: {len(system_message)}")
        messages = [{"role": "system", "content": system_message}]
        
        # Add context message if available
        if context:
            context_str = "\n\n".join([f"Source ({doc['url']}):\n{doc['text']}" for doc in context])
            messages.append({"role": "system", "content": f"Use the following context to answer the question:\n\n{context_str}"})
        
        # Create the user message with optional image
        user_message = {"role": "user", "content": []}
        
        # Add text content
        user_message["content"].append({
            "type": "text", 
            "text": question
        })
        
        # Add image content if provided
        if image_path:
            image_b64 = self._encode_image(image_path)
            user_message["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_b64}"
                }
            })
        
        messages.append(user_message)
        
        # Define the function for structured output
        functions = [{
            "type": "function",
            "function": {
                "name": "generate_structured_response",
                "description": "Generate a structured response with an answer and relevant links",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {
                            "type": "string",
                            "description": "The answer to the user's question"
                        },
                        "links": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "url": {
                                        "type": "string", 
                                        "description": "URL of the source"
                                    },
                                    "text": {
                                        "type": "string",
                                        "description": "Brief description of what the source contains"
                                    }
                                }
                            },
                            "description": "Relevant sources that support the answer"
                        }
                    },
                    "required": ["answer"]
                }
            }
        }]
        
        # Prepare payload for API call
        payload = {
            "model": self.model,
            "messages": messages,
            "functions": functions,            "function_call": {"name": "generate_structured_response"},
            "temperature": 0.3,
            "max_tokens": 1000
        }
        response = requests.post(self.url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        # Extract function call response
        function_call = response.json()["choices"][0]["message"]["function_call"]
        structured_response = json.loads(function_call["arguments"])
        return structured_response
    
    def get_image_description(self, image_path: str) -> str:
        """
        Get a detailed description of an image that can be used by an LLM to answer user questions.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            str: Detailed description of the image
        """
        print(f"[DEBUG] get_image_description: Starting with image_path: {image_path}")
        try:
            # Encode the image to base64
            print("[DEBUG] get_image_description: Encoding image to base64")
            image_b64 = self._encode_image(image_path)
            print(f"[DEBUG] get_image_description: Successfully encoded image, length: {len(image_b64)}")
            
            messages = [
                {
                    "role": "system", 
                    "content": [
                        {
                            "type": "text", 
                            "text": (
                                "You are a vision assistant specialized in providing detailed descriptions of images "
                                "for educational purposes. Analyze the image thoroughly and provide a comprehensive "
                                "description covering:\n\n"
                                "1. Primary subject/topic - What is the main focus of the image?\n"
                                "2. Visual elements - Charts, graphs, diagrams, illustrations, screenshots, or photographs?\n"
                                "3. Text content - Transcribe any visible text, formulas, code, or labels\n"
                                "4. Data representation - Describe values, trends, and patterns in charts/graphs\n"
                                "5. Educational context - How does this relate to teaching/learning?\n"
                                "6. Technical details - For code/diagrams, explain technical elements\n\n"
                                "Structure your response to be directly usable by an LLM to answer student questions about the image. "
                                "Be specific, factual, and comprehensive."
                            )
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please provide a detailed description of this image."
                        },                    {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ]
            
            payload = {
                "model": "gpt-4o-mini",  # Using GPT-4o-mini for best vision capabilities
                "messages": messages,
                "max_tokens": 1500
            }
            
            print("[DEBUG] get_image_description: Preparing to send request to OpenAI API")
            print(f"[DEBUG] get_image_description: API key present: {'Yes' if os.environ.get('OPENAI_API_KEY') else 'No'}")
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",  # Use direct OpenAI API for vision
                headers={
                    "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            print(f"[DEBUG] get_image_description: Response status code: {response.status_code}")
            response.raise_for_status()
            
            result = response.json()['choices'][0]['message']['content']
            print(f"[DEBUG] get_image_description: Successfully got image description, length: {len(result)}")
            return result
        except Exception as e:
            print(f"[DEBUG] get_image_description: Error: {str(e)}")
            print(f"[DEBUG] get_image_description: Error type: {type(e).__name__}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[DEBUG] get_image_description: Error response: {e.response.text}")
            raise

class Ollama:
    def __init__(self, model_name: str = "gemma3:1b"):
        self.model_name = model_name

    def chat(self, messages: list[dict]) -> dict:
        url = f"http://localhost:11434/api/chat"
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
        }
        headers = {
            "Content-Type": "application/json",
        }
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_image_description(self, image: str) -> str:
        """
        Get a description of the image using the Ollama API.

        Args:
            image (str): Base64-encoded image string.

        Returns:
            str: The description of the image.
        """
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Please provide a detailed description of what this image contains."},{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}}]}
            ]
        }
        response = requests.post("http://localhost:11434/api/chat", json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    
    def generate_answer(self, question: str, context: str) -> str:
        """
        Generate an answer to a question using the Ollama API.

        Args:
            question (str): The question to answer.
            context (str): Context to help answer the question.

        Returns:
            str: The generated answer.
        """
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a teaching assistant for the course 'Tools in Data Science'. Answer the user's questions strictly based on the provided context. Do not provide explanations—only give direct, precise answers. Do not include contents of context in your response."},
                {"role": "user", "content": [{"type": "text", "text": question}]},
                {"role": "assistant", "content": [{"type": "text", "text": context}]}
            ]
        }
        response = requests.post("http://localhost:11434/api/chat", json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']