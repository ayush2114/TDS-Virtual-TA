from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import numpy as np
import os
import base64
from llms import Nomic, OpenRouter, Ollama
import json

print("DEBUG: Initializing FastAPI app...")
app = FastAPI()
print("DEBUG: Creating Nomic instance...")
nomic = Nomic()
print("DEBUG: Creating OpenRouter client...")
client = OpenRouter()
print("DEBUG: App initialization complete.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class QuestionRequest(BaseModel):
    question: str
    image: str = None

def load_embeddings():
    """Load embeddings from a file or database."""
    print("DEBUG: Loading embeddings from tds_course.npz...")
    data = np.load("tds_course.npz", allow_pickle=True)
    chunks = data["chunks"]
    embeddings = data["embeddings"]
    print(f"DEBUG: Loaded {len(chunks)} chunks and {len(embeddings)} embeddings")
    print(f"DEBUG: Embedding shape: {embeddings.shape}")
    return chunks, embeddings

def answer_question(question: str, image: str = None) -> Dict[str, str]:
    """
    Process the question and image to generate an answer.
    
    Args:
        question (str): The question to answer.
        image (str): Base64-encoded image string (optional).
        
    Returns:
        Dict[str, str]: The answer to the question.
    """
    print(f"DEBUG: Processing question: '{question[:100]}{'...' if len(question) > 100 else ''}'")
    print(f"DEBUG: Image provided: {image is not None}")
    
    if image:
        print("DEBUG: Getting image description...")
        image_description = client.get_image_description(image)
        print(f"DEBUG: Image description: '{image_description[:100]}{'...' if len(image_description) > 100 else ''}'")
        question += f" {image_description}"
        print(f"DEBUG: Updated question with image description")
    
    print("DEBUG: Getting question embedding...")
    question_embedding = nomic.get_embedding(question)
    print(f"DEBUG: Question embedding shape: {len(question_embedding)}")
    
    print("DEBUG: Loading embeddings...")
    chunks, embeddings = load_embeddings()
    
    print("DEBUG: Calculating similarities...")
    similarities = np.dot(embeddings, question_embedding) / (np.linalg.norm(embeddings, axis=1) * np.linalg.norm(question_embedding))
    print(f"DEBUG: Similarities shape: {similarities.shape}")
    print(f"DEBUG: Max similarity: {np.max(similarities):.4f}, Min similarity: {np.min(similarities):.4f}")
    
    top_indices = np.argsort(similarities)[-10:][::-1]
    print(f"DEBUG: Top 10 similarity indices: {top_indices}")
    print(f"DEBUG: Top 10 similarity scores: {[similarities[i] for i in top_indices]}")
    
    top_chunks = [chunks[i] for i in top_indices]
    print(f"DEBUG: Retrieved {len(top_chunks)} top chunks")
    print(f"DEBUG: First chunk preview: '{top_chunks[0][:100]}{'...' if len(top_chunks[0]) > 100 else ''}'" if top_chunks else "DEBUG: No chunks retrieved")
    
    context = "\n".join(top_chunks)
    print(f"DEBUG: Total context length: {len(context)} characters")
    
    print("DEBUG: Generating answer...")
    response = client.generate_answer(question, context)
    print(f"DEBUG: Generated response length: {len(str(response))} characters")
    print(f"DEBUG: Response preview: '{str(response)[:100]}{'...' if len(str(response)) > 100 else ''}'")
    
    return response

@app.post("/api")
async def answer(request: QuestionRequest):
    """
    API endpoint to answer questions with optional image input.
    
    Args:
        request (QuestionRequest): The request containing the question and optional image.
        
    Returns:
        Dict[str, str]: The answer to the question.
    """
    print(f"DEBUG: API endpoint called with question: '{request.question[:50]}{'...' if len(request.question) > 50 else ''}'")
    print(f"DEBUG: Request has image: {request.image is not None}")
    
    try:
        response = answer_question(request.question, request.image)
        print("DEBUG: Successfully generated response")
        response = json.loads(response) 
        return response
    except Exception as e:
        print(f"DEBUG: Error occurred: {type(e).__name__}: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}

@app.get("/")
async def root():
    """
    Root endpoint to check if the server is running.
    
    Returns:
        Dict[str, str]: A simple message indicating the server is running.
    """
    print("DEBUG: Root endpoint called")
    return {"message": "Server is running. Use POST /api to ask questions."}

if __name__ == "__main__":
    import uvicorn
    print("DEBUG: Starting FastAPI server on port 8000...")
    # Run the FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=7860)