FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU version first
RUN pip install --no-cache-dir \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies from main PyPI
RUN pip install --no-cache-dir \
    diffusers transformers accelerate \
    flask requests pillow numpy

# Create directories
RUN mkdir -p models outputs

# Create the API server
COPY app.py .

# Download a model on build (optional - can be done at runtime)
# RUN python -c "from diffusers import StableDiffusionPipeline; StableDiffusionPipeline.from_pretrained('runwayml/stable-diffusion-v1-5')"

EXPOSE 7860

CMD ["python", "app.py"]