import random
import uuid
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import os
import requests  # Add this if not already there
import json      # Add this if not already there
import time
import shutil


class MockDALLEService:
    def __init__(self):
        self.mock_images = [
            "https://picsum.photos/1024/1024?random=1",
            "https://picsum.photos/1024/1024?random=2",
            "https://picsum.photos/1024/1024?random=3",
        ]
    
    def generate_image(self, prompt: str, size: str = "1024x1024", quality: str = "standard") -> str:
        """Return mock image URL"""
        import time
        time.sleep(2)  # Simulate API delay
        return random.choice(self.mock_images)

class MockMidjourneyService:
    def generate_image(self, prompt: str, size: str = "1024x1024", quality: str = "standard") -> str:
        """Return mock Midjourney-style image"""
        import time
        time.sleep(5)  # Simulate longer processing time
        return f"https://picsum.photos/1024/1024?random={hash(prompt) % 100}"

class StableDiffusionService:
    def __init__(self, base_url="http://stable-diffusion:7860"):
        self.base_url = base_url
    
    def _parse_resolution(self, resolution_option: str) -> tuple:
        """Parse resolution from frontend dropdown options"""
        resolution_mapping = {
            "512x512": (512, 512),
            "768x768": (768, 768), 
            "1024x1024": (1024, 1024)
        }
        
        # Extract just the resolution part (before any parentheses)
        resolution_key = resolution_option.split(' ')[0]
        
        return resolution_mapping.get(resolution_key, (1024, 1024))  # Default to 1024x1024
    
    def _parse_steps(self, steps_option: str) -> int:
        """Parse steps from frontend dropdown options"""
        steps_mapping = {
            "15": 15,
            "25": 25,
            "50": 50
        }
        
        # Extract just the number part (before any parentheses)
        steps_key = steps_option.split(' ')[0]
        
        return steps_mapping.get(steps_key, 25)  # Default to 25
    
    def _wait_for_service(self, timeout=60):
        """Wait for SD service to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200 and response.json().get('model_loaded', False):
                    print(f"Stable Diffusion service ready at {self.base_url}")
                    return True
            except Exception as e:
                print(f"Waiting for SD service: {e}")
                pass
            time.sleep(5)
        return False
    
    def generate_image(self, prompt: str, **kwargs) -> str:
        """Generate image using GPU Stable Diffusion container with frontend parameters"""
        try:
            print(f"Requesting GPU SD generation for: {prompt[:50]}...")
            print(f"Received kwargs: {kwargs}")
            
            # Wait for service to be ready
            if not self._wait_for_service():
                raise Exception("Stable Diffusion GPU service not available")
            
            # Parse frontend parameters
            resolution = kwargs.get('resolution', '1024x1024')
            steps = kwargs.get('steps', '25')
            
            # Handle different parameter formats
            if isinstance(resolution, str):
                width, height = self._parse_resolution(resolution)
            else:
                width, height = 1024, 1024  # Default
            
            if isinstance(steps, str):
                num_steps = self._parse_steps(steps)
            else:
                num_steps = int(steps) if steps else 25
            
            print(f"Parsed parameters: {width}x{height}, {num_steps} steps")
            
            # Prepare payload with parsed parameters
            payload = {
                "prompt": prompt,
                "negative_prompt": kwargs.get("negative_prompt", "blurry, distorted, extra limbs, deformed, text, watermark, signature, 3d render, photorealistic, low quality, ugly, cropped"),
                "steps": num_steps,
                "width": width,
                "height": height,
                "guidance_scale": kwargs.get("guidance_scale", 7.5)
            }
            
            print(f"Sending request to GPU SD: {payload}")
            
            response = requests.post(
                f"{self.base_url}/generate",
                json=payload,
                timeout=180  # Longer timeout for high quality generations
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"GPU SD Response: {result}")
            
            if result.get("success"):
                filename = result["filename"]
                local_path = f"uploads/{filename}"
                
                # Verify the file exists
                if os.path.exists(local_path):
                    print(f"GPU SD generation successful: {local_path}")
                    return local_path
                else:
                    print(f"File not found at {local_path}, checking alternatives...")
                    # Try different path possibilities
                    alternative_paths = [
                        f"shared/{filename}",
                        filename  # Just the filename
                    ]
                    for alt_path in alternative_paths:
                        if os.path.exists(alt_path):
                            print(f"Found file at alternative path: {alt_path}")
                            return alt_path
                    
                    raise Exception(f"Generated file not found at expected paths: {local_path}")
            else:
                raise Exception(f"GPU generation failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"GPU SD generation failed: {e}")
            # Fallback to local mock for development continuity
            return self._generate_fallback_mock(prompt, kwargs.get('resolution', '1024x1024'))
    
    def _generate_fallback_mock(self, prompt: str, resolution: str = "1024x1024") -> str:
        """Fallback mock when GPU service fails"""
        print("Falling back to mock generation...")
        try:
            # Parse resolution for mock
            width, height = self._parse_resolution(resolution)
            
            img = Image.new('RGB', (width, height), color='lightcoral')
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.load_default()
            except:
                font = None
            
            # Add text indicating fallback
            text_lines = [
                "FALLBACK MODE",
                "GPU SD Failed",
                f"{width}x{height}",
                f"{prompt[:20]}..."
            ]
            
            y_offset = height // 2 - 60
            for line in text_lines:
                if font:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                else:
                    text_width = len(line) * 6
                
                x = (width - text_width) // 2
                draw.text((x, y_offset), line, fill='white', font=font)
                y_offset += 30
            
            os.makedirs("uploads", exist_ok=True)
            filename = f"fallback_sd_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join("uploads", filename)
            img.save(filepath)
            print(f"Fallback mock created: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"Even fallback generation failed: {e}")
            return "uploads/generation_error.png"


# class MockStableDiffusionService:
#     def generate_image(self, prompt: str, size: str = "1024x1024", quality: str = "standard") -> str:
#         """Generate local mock image"""
#         # Create simple generated image using PIL
#         img = Image.new('RGB', (1024, 1024), color='skyblue')
#         draw = ImageDraw.Draw(img)
        
#         # Try to use a default font, fallback to basic if not available
#         try:
#             font = ImageFont.truetype("arial.ttf", 40)
#         except:
#             font = ImageFont.load_default()
        
#         # Add text to the image
#         text = f"Generated: {prompt[:50]}"
#         bbox = draw.textbbox((0, 0), text, font=font)
#         text_width = bbox[2] - bbox[0]
#         text_height = bbox[3] - bbox[1]
        
#         x = (1024 - text_width) // 2
#         y = (1024 - text_height) // 2
        
#         draw.text((x, y), text, fill='white', font=font)
        
#         # Create uploads directory if it doesn't exist
#         os.makedirs("uploads", exist_ok=True)
        
#         filename = f"mock_generated_{uuid.uuid4().hex[:8]}.jpg"
#         filepath = os.path.join("uploads", filename)
#         img.save(filepath)
#         return filepath

class MockYouTubeService:
    def __init__(self):
        self.mock_videos = {}
    
    def upload_video(self, video_path: str, metadata: dict) -> dict:
        """Mock YouTube upload"""
        video_id = f"mock_{uuid.uuid4().hex[:8]}"
        
        self.mock_videos[video_id] = {
            "id": video_id,
            "title": metadata.get("title", "Untitled"),
            "description": metadata.get("description", ""),
            "status": "uploaded",
            "url": f"https://youtube.com/watch?v={video_id}",
            "thumbnail": "https://picsum.photos/320/180"
        }
        
        return self.mock_videos[video_id]
    
    def get_video_status(self, video_id: str) -> dict:
        """Get mock video status"""
        return self.mock_videos.get(video_id, {"status": "not_found"})

# Service factory based on environment
# Update your service factory
def get_ai_service(service_name: str):
    """Get AI service instance based on service name"""
    if service_name == "dalle":
        return MockDALLEService()
    elif service_name == "midjourney": 
        return MockMidjourneyService()
    elif service_name == "stable_diffusion":
        return StableDiffusionService()  # Use real SD service
    else:
        return StableDiffusionService()  # Default to SD

def get_youtube_service():
    """Get YouTube service instance"""
    return MockYouTubeService()
