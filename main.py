from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import httpx
import base64


app = FastAPI()
# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

API_KEY = os.getenv("OPENROUTER_API_KEY")

def image_to_base64(image_path):
    """Convert an image file to a base64 encoded string."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    return encoded_string

def get_ai_answer(messages, tools):
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": "mistralai/mistral-small-3.1-24b-instruct:free",
        "messages": messages,
        "tools": tools,
        "tool_choice": "required",
        "stream": False,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"  # Replace with your actual API key if needed
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print("Status code:", response.status_code)
        print("Response text:", response.text)
        return {"error": "Failed to get a response from the model", "details": response.text}
    return response.json()


@app.get("/")
async def root():
    return {"message": "Hello, World!"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


json_schema = {
  "type": "object",
  "properties": {
    "answer": {
      "type": "string",
      "description": "The main textual answer or clarification"
    },
    "links": {
      "type": "array",
      "description": "List of supporting links for reference",
      "items": {
        "type": "object",
        "properties": {
          "url": {
            "type": "string",
            "format": "uri",
            "description": "URL to a forum post or reference"
          },
          "text": {
            "type": "string",
            "description": "Textual description or title of the link"
          }
        },
        "required": ["url", "text"]
      }
    }
  },
  "required": ["answer", "links"]
}


tools = [
    {
      "type": "function",
      "function": {
        "name": "get_answer",
        "description": "Get the answer to a question",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "The location to get the weather for, e.g. San Francisco, CA"
            },
            "format": {
              "type": "string",
              "description": "The format to return the weather in, e.g. 'celsius' or 'fahrenheit'",
              "enum": ["celsius", "fahrenheit"]
            }
          },
          "required": ["location", "format"]
        }
      }
    }
]

question = "What is product name?"
image_path = "image.png"

messages = [
    {
        "role": "system",
        "content": "Answer within 3 words."
    },
    {
        "role": "user",
        "content": question
    },
    {
        "role": "user",
        "content": image_to_base64(image_path)
    }
]

b64 = image_to_base64(image_path)
image_64_data = {"type": "input_image", "image_url": f"data:image/png;base64,{b64}"}

messeges.append({
    "role": "user",
    "content": [{"type": "text", "text": "Extract mfd"}]
})

@app.post("/ask")
async def ask_question(question: str):
    messages = [
        {
            "role": "user",
            "content": question
        }
    ]
    
    response = get_ai_answer(messages, tools)
    
    if "error" in response:
        return {"error": response["error"], "details": response.get("details", "")}
    
    answer = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    return {
        "answer": answer,
        "links": [
            {
                "url": "https://example.com",
                "text": "Example Link"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)
