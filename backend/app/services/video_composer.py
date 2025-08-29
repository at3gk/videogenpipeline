import os
from typing import List
from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip, VideoFileClip
from PIL import Image
import uuid

class VideoComposer:
    def __init__(self, audio_file: str, images: List[str]):
        self.audio = AudioFileClip(audio_file)
        self.images = images
        self.duration = self.audio.duration
    
    def create_slideshow(self, transition_duration: float = 1.0, resolution: str = "1920x1080"):
        """Create slideshow from images"""
        width, height = map(int, resolution.split('x'))
        
        clips = []
        if self.images:
            image_duration = self.duration / len(self.images)
            
            for i, image_path in enumerate(self.images):
                # Load and resize image
                img = ImageClip(image_path, duration=image_duration)
                img = img.resize((width, height))
                img = img.set_start(i * image_duration)
                
                # Add transition effects
                if i > 0:
                    img = img.crossfadein(transition_duration)
                
                clips.append(img)
        else:
            # Create a default background if no images
            default_img = Image.new('RGB', (width, height), color='black')
            default_path = f"uploads/default_bg_{uuid.uuid4().hex[:8]}.jpg"
            default_img.save(default_path)
            
            img = ImageClip(default_path, duration=self.duration)
            clips.append(img)
        
        return CompositeVideoClip(clips, size=(width, height))
    
    def add_audio_visualization(self, video_clip):
        """Add audio waveform visualization (placeholder for future implementation)"""
        # This would add audio visualization overlay
        # For now, just return the video clip as-is
        return video_clip
    
    def render_final_video(self, output_path: str, fps: int = 30, resolution: str = "1920x1080"):
        """Render final video with optimizations"""
        video = self.create_slideshow(resolution=resolution)
        final_video = video.set_audio(self.audio)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        final_video.write_videofile(
            output_path,
            fps=fps,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False,
            logger=None
        )
        
        return output_path
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'audio'):
            self.audio.close()

def create_video_from_audio_and_images(
    audio_file_path: str,
    image_paths: List[str],
    output_path: str,
    fps: int = 30,
    resolution: str = "1920x1080",
    transition_duration: float = 1.0
) -> str:
    """Convenience function to create video from audio and images"""
    composer = VideoComposer(audio_file_path, image_paths)
    
    try:
        output_file = composer.render_final_video(
            output_path, 
            fps=fps, 
            resolution=resolution
        )
        return output_file
    finally:
        composer.cleanup()
