import requests
from dotenv import load_dotenv
import os
import json
from typing import List, Dict, Any, Optional, Union
import base64
import mimetypes

def get_mime_type(url):
    return mimetypes.guess_type(url)[0] or "image/jpeg"

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

    def get_image_description(self, image: str) -> str:
        """
        Get a description of the image using the OpenAI API.

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
    
    def get_image_description_from_url(self, image_url: str) -> str:
        # print(f"DEBUG: Getting image description for: {image_url}")
        try:
            # Download image
            image_bytes = requests.get(image_url, timeout=10).content
            mime_type = get_mime_type(image_url)
            b64_image = base64.b64encode(image_bytes).decode("utf-8")

            # Create request payload

            payload = {
                "model": self.model,  # or gpt-4o-mini if available
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Briefly describe this image."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{b64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 100
            }

            response = requests.post(
                self.url,
                headers=self.headers,
                json=payload,
            )

            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")

            data = response.json()
            description = data["choices"][0]["message"]["content"].strip()
            return description

        except Exception as e:
            print(f"DEBUG: Error getting image description: {e}")
            return f"Error getting image description: {e}"
        
    def generate_answer(self, question: str, context: str) -> str:
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
        return response.json()['choices'][0]['message']['tool_calls'][0]['function']['arguments']


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
    