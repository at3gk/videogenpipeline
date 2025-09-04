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
device = None

def get_device():
    """Determine the best available device"""
    if torch.cuda.is_available():
        device = "cuda"
        logger.info(f"CUDA available! Using GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    else:
        device = "cpu"
        logger.info("CUDA not available, using CPU")
    return device

def make_divisible_by_8(value, default=512):
    """Ensure dimension is divisible by 8"""
    try:
        value = int(value)
        return max(8, (value // 8) * 8)
    except (ValueError, TypeError):
        return default
        
def initialize_pipeline():
    """Initialize the Stable Diffusion pipeline with GPU support"""
    global pipeline, device
    try:
        device = get_device()
        logger.info("Loading Stable Diffusion model...")
        
        # Use cache directory to persist downloads
        cache_dir = "/root/.cache/huggingface"
        os.makedirs(cache_dir, exist_ok=True)
        
        # Choose appropriate dtype based on device
        torch_dtype = torch.float16 if device == "cuda" else torch.float32
        
        pipeline = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch_dtype,
            safety_checker=None,
            requires_safety_checker=False,
            cache_dir=cache_dir,
            local_files_only=False,
            resume_download=True
        )
        
        pipeline = pipeline.to(device)
        
        # GPU optimizations
        if device == "cuda":
            pipeline.enable_attention_slicing()
            pipeline.enable_model_cpu_offload()
            # Enable memory efficient attention if available
            try:
                pipeline.enable_xformers_memory_efficient_attention()
                logger.info("Enabled xformers memory efficient attention")
            except Exception as e:
                logger.info(f"xformers not available: {e}")
        
        logger.info(f"Model loaded successfully on {device}!")
        return True
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    gpu_info = {}
    if torch.cuda.is_available():
        gpu_info = {
            "gpu_available": True,
            "gpu_name": torch.cuda.get_device_name(0),
            "gpu_memory_total": f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB",
            "gpu_memory_free": f"{torch.cuda.memory_reserved(0) / 1024**3:.1f} GB"
        }
    else:
        gpu_info = {"gpu_available": False}
    
    return jsonify({
        "status": "healthy" if pipeline is not None else "loading",
        "model_loaded": pipeline is not None,
        "device": device,
        "gpu_info": gpu_info
    })

@app.route('/generate', methods=['POST'])
def generate_image():
    """Generate image from prompt with GPU acceleration"""
    try:
        if pipeline is None:
            return jsonify({"error": "Model not loaded yet"}), 503
        
        data = request.get_json()
        prompt = data.get('prompt', '')
        negative_prompt = data.get('negative_prompt', 'blurry, low quality, distorted, ugly, bad anatomy')
        steps = data.get('steps', 20)  # Can be higher with GPU
        width = data.get('width', 768)  # Higher resolution with GPU
        height = data.get('height', 768)  # Higher resolution with GPU
        guidance_scale = data.get('guidance_scale', 7.5)
        seed = data.get('seed', None)
        
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        
        # Validate and adjust resolution based on device
        if device == "cuda":
            # GPU can handle higher resolutions
            max_res = 1024
            if width > max_res or height > max_res:
                width = min(width, max_res)
                height = min(height, max_res)
        else:
            # CPU should stick to lower resolutions
            max_res = 512
            width = min(width, max_res)
            height = min(height, max_res)
        
        logger.info(f"Generating {width}x{height} image for prompt: '{prompt[:50]}...' on {device}")
        
        # Set up generator for reproducible results
        generator = None
        if seed is not None:
            generator = torch.Generator(device=device).manual_seed(seed)
        
        # Generate image
        with torch.no_grad():
            if device == "cuda":
                with torch.autocast("cuda"):
                    result = pipeline(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        num_inference_steps=steps,
                        width=width,
                        height=height,
                        guidance_scale=guidance_scale,
                        generator=generator
                    )
            else:
                result = pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    num_inference_steps=steps,
                    width=width,
                    height=height,
                    guidance_scale=guidance_scale,
                    generator=generator
                )
        
        image = result.images[0]
        
        # Save image to outputs directory
        os.makedirs("/app/outputs", exist_ok=True)
        filename = f"generated_{uuid.uuid4().hex[:8]}.png"
        filepath = f"/app/outputs/{filename}"
        image.save(filepath, quality=95, optimize=True)
        
        logger.info(f"Image saved to {filepath}")
        
        # Clear GPU cache if using CUDA
        if device == "cuda":
            torch.cuda.empty_cache()
        
        # Return metadata (don't include base64 for large images)
        return jsonify({
            "success": True,
            "filename": filename,
            "filepath": filepath,
            "prompt": prompt,
            "resolution": f"{width}x{height}",
            "steps": steps,
            "device": device
        })
        
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        # Clear GPU cache on error
        if device == "cuda":
            torch.cuda.empty_cache()
        return jsonify({"error": str(e)}), 500

@app.route('/generate-batch', methods=['POST'])
def generate_batch():
    """Generate multiple images from prompt"""
    try:
        if pipeline is None:
            return jsonify({"error": "Model not loaded yet"}), 503
        
        data = request.get_json()
        prompt = data.get('prompt', '')
        num_images = data.get('num_images', 1)
        negative_prompt = data.get('negative_prompt', 'blurry, low quality, distorted, deformed, cropped, extra limbs, bad anatomy, multiple faces, watermark, text, signature, cartoon, 3d render')
        steps = data.get('steps', 25)
        
        # Fix dimensions to be divisible by 8
        raw_width = data.get('width', 1024)
        raw_height = data.get('height', 1024)
        width = make_divisible_by_8(raw_width, 1024)
        height = make_divisible_by_8(raw_height, 1024)
        
        guidance_scale = data.get('guidance_scale', 7.5)
        seed = data.get('seed', None)
        
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        
        # Validate num_images
        num_images = min(max(1, int(num_images)), 10)  # Limit to 1-10 images
        
        logger.info(f"Generating {num_images} {width}x{height} images for prompt: '{prompt[:50]}...' on {device}")
        
        generated_images = []
        
        for i in range(num_images):
            try:
                # Set up generator with different seed for each image
                generator = None
                if seed is not None:
                    current_seed = seed + i
                    generator = torch.Generator(device=device).manual_seed(current_seed)
                else:
                    import random
                    current_seed = random.randint(1, 1000000)
                    generator = torch.Generator(device=device).manual_seed(current_seed)
                
                logger.info(f"Generating image {i+1}/{num_images} with seed {current_seed}")
                
                # Generate image with appropriate precision
                with torch.no_grad():
                    if device == "cuda":
                        with torch.autocast("cuda"):
                            result = pipeline(
                                prompt=prompt,
                                negative_prompt=negative_prompt,
                                num_inference_steps=steps,
                                width=width,
                                height=height,
                                guidance_scale=guidance_scale,
                                generator=generator
                            )
                    else:
                        result = pipeline(
                            prompt=prompt,
                            negative_prompt=negative_prompt,
                            num_inference_steps=steps,
                            width=width,
                            height=height,
                            guidance_scale=guidance_scale,
                            generator=generator
                        )
                
                image = result.images[0]
                
                # Save image to outputs directory
                os.makedirs("/app/outputs", exist_ok=True)
                filename = f"sd_batch_{i+1}_{uuid.uuid4().hex[:8]}.png"
                filepath = f"/app/outputs/{filename}"
                image.save(filepath, quality=95, optimize=True)
                
                generated_images.append({
                    "filename": filename,
                    "filepath": filepath,
                    "seed": current_seed,
                    "image_index": i + 1
                })
                
                logger.info(f"Image {i+1} saved to {filepath}")
                
            except Exception as e:
                logger.error(f"Error generating image {i+1}: {e}")
                # Continue with next image
                continue
        
        # Clear GPU cache
        if device == "cuda":
            torch.cuda.empty_cache()
        
        if not generated_images:
            return jsonify({"error": "Failed to generate any images"}), 500
        
        # Return success response with all generated images
        return jsonify({
            "success": True,
            "images": generated_images,
            "prompt": prompt,
            "resolution": f"{width}x{height}",
            "steps": steps,
            "device": device,
            "guidance_scale": guidance_scale,
            "total_generated": len(generated_images)
        })
        
    except Exception as e:
        logger.error(f"Error in batch generation: {e}")
        # Clear GPU cache on error
        if device == "cuda":
            torch.cuda.empty_cache()
        return jsonify({"error": str(e)}), 500

@app.route('/models', methods=['GET'])
def list_models():
    """List available models"""
    return jsonify({
        "models": ["stable-diffusion-v1-5"],
        "current": "stable-diffusion-v1-5",
        "device": device,
        "gpu_available": torch.cuda.is_available()
    })

if __name__ == '__main__':
    # Initialize pipeline on startup
    logger.info("Starting GPU-accelerated Stable Diffusion service...")
    success = initialize_pipeline()
    
    if not success:
        logger.error("Failed to initialize model, but starting server anyway...")
    
    # Start Flask server
    app.run(host='0.0.0.0', port=7860, debug=False)