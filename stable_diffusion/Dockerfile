# Base image with CUDA 11.8 and cuDNN 8
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

# Set working directory
WORKDIR /app

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    git \
    wget \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Symlink python3 to python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Upgrade pip
RUN pip3 install --upgrade pip

# Install PyTorch with CUDA support
RUN pip3 install --no-cache-dir \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install Python dependencies with compatible versions
RUN pip3 install --no-cache-dir \
    diffusers==0.21.4 \
    "transformers<4.30" \
    accelerate==0.24.1 \
    "huggingface-hub<0.16" \
    flask \
    requests \
    pillow \
    numpy \
    scipy \
    ftfy \
    regex

# Try to install xformers (optional for memory-efficient attention)
RUN pip3 install --no-cache-dir xformers || echo "xformers not available, continuing without it"

# Create necessary directories
RUN mkdir -p models outputs /root/.cache/huggingface

# Copy Flask app
COPY app.py .

# Expose port for Flask
EXPOSE 7860

# Start the Flask app
CMD ["python", "app.py"]
