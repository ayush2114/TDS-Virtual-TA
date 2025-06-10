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
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")


def image_to_base64(image_path):
    """Convert an image file to a base64 encoded string."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    return encoded_string


tools = [
    {
        "type": "function",
        "function": {
            "name": "answer_user_question",
            "description": "Answer the user's question",
            # "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "Answer to the user's question based on tools in data science course",
                    },
                    "links": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Links to relevant resources or information"
                        },
                        "description": "Links to relevant resources or information"
                    }
                },
                "required": ["answer", "links"],
            }
        }
    }
]

my_func = {
    "name": "product_info",
    "description": "Generates product manufacturing date, expiry date and answers user's question",
    "strict": True,
    "parameters": {
        "type": "object",
        "required": [
            "mfd",
            "expiry_date",
            "user_question",
            "name"
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
                "description": "The user's question regarding tools in data science course"
            },
            "name": {
                "type": "string",
                "description": "Name of the product"
            }
        },
        "additionalProperties": False
    }
}

tools2 = [{"type": "function", "function": my_func}]

def get_gpt_answer(messages):
    url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "tools": tools2,
        "tool_choice": "required",
        "stream": False,
    }
    headers = {
        "Content-Type": "application/json",
        # Replace with your actual API key if needed
        "Authorization": f"Bearer {AIPROXY_TOKEN}"
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def get_ai_answer(messages):
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
        # Replace with your actual API key if needed
        "Authorization": f"Bearer {API_KEY}"
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print("Status code:", response.status_code)
        print("Response text:", response.text)
        return {"error": "Failed to get a response from the model", "details": response.text}
    return response.json()


sample_question = "What is the value of e?"
sample_image = image_to_base64("image2.jpg")


def prepare_messages(question: str = sample_question, image: str = sample_image) -> List[Dict]:
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant for the Tools in Data Science course at IIT Madras. Answer accurately and briefly, and include links if available."
        },
        {
            "role": "user",
            "content": [
                { "type": "text", "text": question },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpg;base64,{sample_image}"
                    }
                }
            ]
        }
    ]

    # Add text content
    # messages[-1]["content"].append({
    #     "type": "text",
    #     "text": question
    # })

    # # Add image if provided
    # b64 = image_to_base64(image_path)
    # image_data = {
    #     "type": "image_url",
    #     "image_url": {
    #         "url": f"data:image/jpg;base64,{b64}"
    #     }
    # }
    # messages[-1]["content"].append(image_data)

    return messages


@app.get("/")
async def root():
    return {"message": "Hello, World!"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}

messages = prepare_messages()

@app.get("/ask")
async def ask_question_get():
    return """
    <h1>Ask a Question</h1>
    <form action="/ask" method="post">
    <label for="question">Question:</label><br>
    <input type="text" id="question" name="question" value="What is the value of e?"><br>
    <label for="image">Image Path:</label><br>
    <input type="text" id="image" name="image" value="image2.jpg"><br>
    <input type="submit" value="Submit">
    </form>
    <p>Use the /ask endpoint to ask a question with an image.</p>
    <p>Use the /gpt-ask endpoint to ask a question using GPT-4o-mini.</p>
    <p>Example question: "What is the value of e?"</p>
    """

@app.post("/ask")
async def ask_question(data: Dict[str, str]):
    question = data.get("question", sample_question)
    image = data.get("image", sample_image)
    messages = prepare_messages(question=question, image=image)

    response = get_ai_answer(messages=messages)

    # answer = response.get("choices", [{}])[0].get("message", {}).get("content", "")
   
    return response

@app.post("/gpt-ask")
async def gpt_ask_question(question: str = sample_question, image: str = sample_image):
    messages = prepare_messages(question=question, image=image)
    response = get_gpt_answer(messages=messages)
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)

# To run the FastAPI app, use the command:
# uvicorn main:app --reload
