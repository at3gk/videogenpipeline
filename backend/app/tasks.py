from celery import current_task
from .celery_app import celery_app
from .services.mock_services import get_ai_service
from .services.video_composer import create_video_from_audio_and_images
from .database import SessionLocal
from .models import Project, GeneratedImage, VideoOutput, ProcessingJob, AudioFile
from sqlalchemy.orm import Session
import os
import uuid
from datetime import datetime

def get_db_session():
    """Get database session for tasks"""
    return SessionLocal()

@celery_app.task(bind=True)
def generate_ai_image(self, project_id: str, prompt: str, service: str = "dalle"):
    """Generate AI image task"""
    db = get_db_session()
    
    try:
        # Update job status
        current_task.update_state(state='PROGRESS', meta={'progress': 10})
        
        # Get AI service
        ai_service = get_ai_service(service)
        current_task.update_state(state='PROGRESS', meta={'progress': 30})
        
        # Generate image
        if hasattr(ai_service, 'generate_image'):
            if service == "stable_diffusion":
                image_path = ai_service.generate_image(prompt)
                image_url = None
            else:
                image_path = None
                image_url = ai_service.generate_image(prompt)
        else:
            raise Exception(f"Service {service} not supported")
        
        current_task.update_state(state='PROGRESS', meta={'progress': 70})
        
        # Save to database
        generated_image = GeneratedImage(
            project_id=project_id,
            prompt=prompt,
            image_url=image_url,
            file_path=image_path,
            generator_service=service,
            generation_params={"prompt": prompt, "service": service}
        )
        
        db.add(generated_image)
        db.commit()
        
        current_task.update_state(state='PROGRESS', meta={'progress': 100})
        
        return {
            "image_id": str(generated_image.id),
            "image_url": image_url,
            "file_path": image_path
        }
        
    except Exception as e:
        if db:
            db.rollback()
        raise e
    finally:
        if db:
            db.close()

@celery_app.task(bind=True)
def compose_video(self, project_id: str, composition_settings: dict):
    """Compose final video from audio and images"""
    db = get_db_session()
    
    try:
        # Update job status
        current_task.update_state(state='PROGRESS', meta={'progress': 10})
        
        # Get project and audio file
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise Exception("Project not found")
        
        audio_file = db.query(AudioFile).filter(AudioFile.project_id == project_id).first()
        if not audio_file:
            raise Exception("Audio file not found")
        
        current_task.update_state(state='PROGRESS', meta={'progress': 20})
        
        # Get generated images
        images = db.query(GeneratedImage).filter(GeneratedImage.project_id == project_id).all()
        image_paths = [img.file_path for img in images if img.file_path]
        
        current_task.update_state(state='PROGRESS', meta={'progress': 30})
        
        # Create output path
        output_filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join("uploads", output_filename)
        
        current_task.update_state(state='PROGRESS', meta={'progress': 40})
        
        # Create video composition
        video_path = create_video_from_audio_and_images(
            audio_file_path=audio_file.file_path,
            image_paths=image_paths,
            output_path=output_path,
            fps=composition_settings.get("fps", 30),
            resolution=composition_settings.get("resolution", "1920x1080"),
            transition_duration=composition_settings.get("transition_duration", 1.0)
        )
        
        current_task.update_state(state='PROGRESS', meta={'progress': 80})
        
        # Get video file size
        file_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0
        
        # Save video output to database
        video_output = VideoOutput(
            project_id=project_id,
            file_path=video_path,
            duration_seconds=float(audio_file.duration_seconds) if audio_file.duration_seconds else 0,
            resolution=composition_settings.get("resolution", "1920x1080"),
            file_size_bytes=file_size,
            status="completed"
        )
        
        db.add(video_output)
        db.commit()
        
        current_task.update_state(state='PROGRESS', meta={'progress': 100})
        
        return {
            "video_id": str(video_output.id),
            "video_path": video_path,
            "file_size": file_size
        }
        
    except Exception as e:
        if db:
            db.rollback()
        raise e
    finally:
        if db:
            db.close()

@celery_app.task(bind=True)
def publish_to_youtube(self, project_id: str, video_id: str, youtube_settings: dict):
    """Publish video to YouTube (mock implementation)"""
    db = get_db_session()
    
    try:
        # Update job status
        current_task.update_state(state='PROGRESS', meta={'progress': 10})
        
        # Get video output
        video_output = db.query(VideoOutput).filter(VideoOutput.id == video_id).first()
        if not video_output:
            raise Exception("Video output not found")
        
        current_task.update_state(state='PROGRESS', meta={'progress': 30})
        
        # Mock YouTube upload
        from .services.mock_services import get_youtube_service
        youtube_service = get_youtube_service()
        
        # Simulate upload delay
        import time
        time.sleep(3)
        
        current_task.update_state(state='PROGRESS', meta={'progress': 70})
        
        # Mock upload result
        mock_video_id = f"mock_{uuid.uuid4().hex[:8]}"
        
        # Update video output with YouTube ID
        video_output.youtube_video_id = mock_video_id
        video_output.status = "published"
        db.commit()
        
        current_task.update_state(state='PROGRESS', meta={'progress': 100})
        
        return {
            "youtube_video_id": mock_video_id,
            "status": "published"
        }
        
    except Exception as e:
        if db:
            db.rollback()
        raise e
    finally:
        if db:
            db.close()
