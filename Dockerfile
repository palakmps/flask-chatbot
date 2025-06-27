# Use the official Python base image
FROM python:3.10-slim
 
# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
 
# Set working directory
WORKDIR /code
 
# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libglib2.0-dev \
    libsm6 \
    libxrender1 \
    libxext6 \
    libpoppler-cpp-dev \
    python3-dev \
&& rm -rf /var/lib/apt/lists/*
 
# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy application code
COPY . .
 
# Expose the port Hugging Face expects
EXPOSE 7860
 
# Command to run the app using gunicorn
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:7860", "app:app"]