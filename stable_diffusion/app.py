from flask import Flask, request, jsonify
from diffusers import StableDiffusionPipeline
import torch
import uuid
import os
import base64
import io
from PIL import Image
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global pipeline variable
pipeline = None

def initialize_pipeline():
    """Initialize the Stable Diffusion pipeline"""
    global pipeline
    try:
        logger.info("Loading Stable Diffusion model...")
        pipeline = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float32,  # Use float32 for CPU
            safety_checker=None,  # Disable for faster loading
            requires_safety_checker=False
        )
        pipeline = pipeline.to("cpu")
        pipeline.enable_attention_slicing()  # Reduce memory usage
        logger.info("Model loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise e

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy" if pipeline is not None else "loading",
        "model_loaded": pipeline is not None
    })

@app.route('/generate', methods=['POST'])
def generate_image():
    """Generate image from prompt"""
    try:
        if pipeline is None:
            return jsonify({"error": "Model not loaded yet"}), 503
        
        data = request.get_json()
        prompt = data.get('prompt', '')
        negative_prompt = data.get('negative_prompt', '')
        steps = data.get('steps', 20)
        width = data.get('width', 512)
        height = data.get('height', 512)
        guidance_scale = data.get('guidance_scale', 7.5)
        
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        
        logger.info(f"Generating image for prompt: '{prompt}'")
        
        # Generate image
        with torch.no_grad():  # Reduce memory usage
            result = pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=steps,
                width=width,
                height=height,
                guidance_scale=guidance_scale,
                generator=torch.Generator().manual_seed(42)  # For reproducible results
            )
        
        image = result.images[0]
        
        # Save image to outputs directory
        os.makedirs("/app/outputs", exist_ok=True)
        filename = f"generated_{uuid.uuid4().hex[:8]}.png"
        filepath = f"/app/outputs/{filename}"
        image.save(filepath)
        
        logger.info(f"Image saved to {filepath}")
        
        # Also return base64 encoded image for immediate use
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        return jsonify({
            "success": True,
            "filename": filename,
            "filepath": filepath,
            "image_base64": img_base64,
            "prompt": prompt
        })
        
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/models', methods=['GET'])
def list_models():
    """List available models"""
    return jsonify({
        "models": ["stable-diffusion-v1-5"],
        "current": "stable-diffusion-v1-5"
    })

if __name__ == '__main__':
    # Initialize pipeline on startup
    initialize_pipeline()
    
    # Start Flask server
    app.run(host='0.0.0.0', port=7860, debug=False)