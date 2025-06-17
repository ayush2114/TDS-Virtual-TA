# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

# Copy requirements file first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies using uv (faster than pip)
RUN uv pip install --system -r requirements.txt

# Copy application files
COPY main.py llms.py ./
COPY tds_course.npz ./

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose the port for Hugging Face Spaces
EXPOSE 7860

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Command to run the FastAPI application on port 7860 for HF Spaces
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]