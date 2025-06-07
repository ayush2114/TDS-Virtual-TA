from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
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
        # "tools": tools,
        # "tool_choice": "auto",
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

image_path = "image2.jpg"

my_func = {
    "name": "product_info",
    "description": "Generates product manufacturing date, expiry date and answers user's question",
    "strict": True,
    "parameters": {
        "type": "object",
        "required": [
            "mfd",
            "expiry_date",
            "user_question"
        ],
        "properties": {
            "mfd": {
                "type": "string",
                "description": "Manufacturing date of the product in YYYY format"
            },
            "expiry_date": {
                "type": "string",
                "description": "Expiry date of the product in YYYY format"
            },
            "user_question": {
                "type": "string",
                "description": "The user's question regarding the product"
            },
            "name": {
                "type": "string",
                "description": "Name of the product"
            }
        },
        "additionalProperties": False
    }
}

messages = [
    {
        "role": "system",
        "content": "Answer within 3 words."
    }
]

b64 = image_to_base64(image_path)
image_64_data = {"type": "image_url", "image_url": {"url": f"data:image/jpg;base64,{b64}"}}

messages.append({
    "role": "user",
    "content": [{"type": "text", "text": "Extract all info"}, image_64_data]
})

@app.post("/ask")
async def ask_question(messages: List[dict] = messages, tools: List[Dict] = [my_func]):
    
    response = get_ai_answer(messages=messages, tools=tools)
    
    # answer = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    if "error" in response:
        return {"error": response["error"], "details": response.get("details", "")}
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)

# To run the FastAPI app, use the command:
# uvicorn main:app --reload