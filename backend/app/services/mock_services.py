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
    
    def _wait_for_service(self, timeout=60):
        """Wait for SD service to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(5)
        return False
    
    def generate_image(self, prompt: str, **kwargs) -> str:
        """Generate image using local Stable Diffusion"""
        try:
            # Wait for service
            if not self._wait_for_service():
                raise Exception("Stable Diffusion service not available")
            
            payload = {
                "prompt": prompt,
                "negative_prompt": "blurry, low quality, low resolution, oversaturated",
                "steps": 20,  # Faster generation
                "width": 550,
                "height": 550
            }
            
            response = requests.post(
                f"{self.base_url}/generate",
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("success"):
                # The image is saved to /app/outputs in SD container
                # Which maps to ./uploads on host
                filename = result["filename"]
                local_path = f"uploads/{filename}"
                
                print(f"SD generation successful: {local_path}")
                return local_path  # Return the path accessible to main app
                
                # For now, just return the shared path
                return f"shared/{result['filename']}"
            else:
                raise Exception(f"Generation failed: {result.get('error')}")
                
        except Exception as e:
            print(f"SD generation failed: {e}, falling back to mock")
            # Fallback to your existing mock implementation
            return self._generate_mock(prompt)
    
    def _generate_mock(self, prompt: str) -> str:
        """Fallback mock implementation"""
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.new('RGB', (512, 512), color='lightblue')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        text = f"SD: {prompt[:30]}..."
        draw.text((50, 250), text, fill='white', font=font)
        
        os.makedirs("uploads", exist_ok=True)
        filename = f"mock_sd_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join("uploads", filename)
        img.save(filepath)
        return filepath


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
