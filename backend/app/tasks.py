from celery import current_task
from .celery_app import celery_app
from .services.mock_services import get_ai_service
from .services.video_composer import FFmpegVideoComposer, create_video_from_audio_and_images
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
def generate_ai_image(self, project_id: str, prompt: str, service: str = "dalle", **kwargs):
    """Generate AI image task with parameters"""
    db = get_db_session()
    
    # Extract parameters that might come from the frontend
    size = kwargs.get('size', '1024x1024')
    quality = kwargs.get('quality', '25')
    
    print(f"DEBUG - generate_ai_image called with:")
    print(f"  project_id: {project_id}")
    print(f"  prompt: {prompt}")
    print(f"  service: {service}")
    print(f"  size: {size}")
    print(f"  quality: {quality}")
    print(f"  additional kwargs: {kwargs}")
    
    try:
        # Update job status
        current_task.update_state(state='PROGRESS', meta={'progress': 10})
        
        # Get AI service
        ai_service = get_ai_service(service)
        current_task.update_state(state='PROGRESS', meta={'progress': 30})
        
        # Generate image with parameters
        if hasattr(ai_service, 'generate_image'):
            if service == "stable_diffusion":
                # Pass all parameters to Stable Diffusion
                image_path = ai_service.generate_image(
                    prompt, 
                    resolution=size,
                    steps=quality,
                    **kwargs  # Pass any additional parameters
                )
                image_url = None
            else:
                # For other services, use the standard parameters
                image_path = None
                image_url = ai_service.generate_image(prompt, size=size, quality=quality)
        else:
            raise Exception(f"Service {service} not supported")
        
        current_task.update_state(state='PROGRESS', meta={'progress': 70})
        
        # Save to database with generation parameters
        generated_image = GeneratedImage(
            project_id=project_id,
            prompt=prompt,
            image_url=image_url,
            file_path=image_path,
            generator_service=service,
            generation_params={
                "prompt": prompt, 
                "service": service,
                "size": size,
                "quality": quality,
                **kwargs
            }
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
def compose_video_ffmpeg(self, project_id: str, composition_settings: dict):
    """Compose final video from audio and images using FFmpeg"""
    db = get_db_session()
    
    try:
        # Update job status
        current_task.update_state(state='PROGRESS', meta={'progress': 5, 'status': 'Initializing'})
        
        # Get project and validate
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise Exception("Project not found")
        
        current_task.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Loading audio file'})
        
        # Get audio file
        audio_file = db.query(AudioFile).filter(AudioFile.project_id == project_id).first()
        if not audio_file:
            raise Exception("No audio file found for this project")
        
        # Construct full audio file path
        if audio_file.file_path.startswith('uploads/'):
            audio_path = audio_file.file_path
        elif '/' in audio_file.file_path:
            audio_path = audio_file.file_path
        else:
            audio_path = os.path.join("uploads", audio_file.file_path)
        
        if not os.path.exists(audio_path):
            raise Exception(f"Audio file not found: {audio_path}")
        
        current_task.update_state(state='PROGRESS', meta={'progress': 20, 'status': 'Loading images'})
        
        # Get selected/approved images
        images = db.query(GeneratedImage).filter(
            GeneratedImage.project_id == project_id,
            GeneratedImage.status == "approved"
        ).all()
        
        if not images:
            raise Exception("No approved images found for this project")
        
        # Prepare image paths
        image_paths = []
        for img in images:
            if img.file_path:
                # Handle different file path formats
                if img.file_path.startswith('uploads/'):
                    img_path = img.file_path
                elif '/' in img.file_path:
                    img_path = img.file_path
                else:
                    img_path = os.path.join("uploads", img.file_path)
                
                if os.path.exists(img_path):
                    image_paths.append(img_path)
                    print(f"Added image: {img_path}")
                else:
                    print(f"Warning: Image file not found: {img_path}")
            elif img.image_url and img.image_url.startswith('http'):
                # For external URLs, we'd need to download them first
                print(f"Warning: External image URLs not yet supported: {img.image_url}")
        
        if not image_paths:
            raise Exception("No valid image files found")
        
        current_task.update_state(state='PROGRESS', meta={'progress': 30, 'status': f'Preparing video composition with {len(image_paths)} images'})
        
        # Extract composition settings
        resolution = composition_settings.get("resolution", "1920x1080")
        fps = composition_settings.get("fps", 30)
        transition_duration = composition_settings.get("transition_duration", 1.0)
        transition_type = composition_settings.get("transition_type", "fade")
        add_ken_burns = composition_settings.get("add_ken_burns", False)
        add_audio_visualization = composition_settings.get("add_audio_visualization", False)
        
        print(f"Video settings:")
        print(f"  Resolution: {resolution}")
        print(f"  FPS: {fps}")
        print(f"  Transition: {transition_type} ({transition_duration}s)")
        print(f"  Ken Burns: {add_ken_burns}")
        print(f"  Audio Viz: {add_audio_visualization}")
        
        current_task.update_state(state='PROGRESS', meta={'progress': 40, 'status': 'Starting FFmpeg video composition'})
        
        # Create output path
        output_filename = f"video_{project.name}_{uuid.uuid4().hex[:8]}.mp4"
        # Sanitize filename
        import re
        output_filename = re.sub(r'[^\w\-_\.]', '_', output_filename)
        output_path = os.path.join("uploads", output_filename)
        
        print(f"Creating video: {output_path}")
        print(f"Audio source: {audio_path}")
        print(f"Image count: {len(image_paths)}")
        
        # Create video using enhanced FFmpeg composer
        composer = FFmpegVideoComposer(audio_path, image_paths)
        
        # Update progress during video creation
        current_task.update_state(state='PROGRESS', meta={'progress': 50, 'status': 'Rendering video (this may take several minutes)'})
        
        if add_ken_burns or add_audio_visualization:
            video_path = composer.create_video_with_effects(
                resolution=resolution,
                fps=fps,
                transition_type=transition_type,
                add_ken_burns=add_ken_burns,
                add_audio_visualization=add_audio_visualization
            )
        else:
            video_path = composer.create_slideshow_video(
                resolution=resolution,
                fps=fps,
                transition_duration=transition_duration
            )
        
        current_task.update_state(state='PROGRESS', meta={'progress': 80, 'status': 'Finalizing video'})
        
        # Move to final output path if needed
        if video_path != output_path:
            if os.path.exists(video_path):
                os.rename(video_path, output_path)
                video_path = output_path
        
        # Get video file info
        file_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0
        
        current_task.update_state(state='PROGRESS', meta={'progress': 90, 'status': 'Saving to database'})
        
        # Save video output to database
        video_output = VideoOutput(
            project_id=project_id,
            file_path=output_filename,  # Store relative path
            duration_seconds=float(audio_file.duration_seconds) if audio_file.duration_seconds else 0,
            resolution=resolution,
            file_size_bytes=file_size,
            status="completed"
        )
        
        db.add(video_output)
        db.commit()
        
        # Cleanup temporary files
        composer.cleanup()
        
        current_task.update_state(state='PROGRESS', meta={'progress': 100, 'status': 'Video creation completed'})
        
        print(f"Video created successfully: {video_path} ({file_size} bytes)")
        
        return {
            "video_id": str(video_output.id),
            "video_path": output_filename,
            "file_size": file_size,
            "duration": video_output.duration_seconds,
            "resolution": resolution,
            "status": "completed"
        }
        
    except Exception as e:
        print(f"Video composition error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if db:
            db.rollback()
        raise e
    finally:
        if db:
            db.close()

@celery_app.task(bind=True)
def compose_video_ffmpeg(self, project_id: str, composition_settings: dict):
    """Enhanced compose video that automatically handles single or multiple audio files"""
    db = get_db_session()
    
    try:
        # Check how many audio files we have
        audio_files = db.query(AudioFile).filter(AudioFile.project_id == project_id).all()
        
        if len(audio_files) > 1:
            # Use multi-audio composition
            print(f"Detected {len(audio_files)} audio files - using multi-audio composition")
            return compose_video_multi_audio.apply_async(
                args=[project_id, composition_settings],
                task_id=self.request.id
            ).get()
        else:
            # Use single audio composition (existing logic)
            print("Using single audio composition")
            # Your existing single audio composition code here
            # (keeping the original code from the previous implementation)
            
            # Update job status
            current_task.update_state(state='PROGRESS', meta={'progress': 5, 'status': 'Initializing'})
            
            # Get project and validate
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise Exception("Project not found")
            
            current_task.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Loading audio file'})
            
            # Get audio file
            audio_file = db.query(AudioFile).filter(AudioFile.project_id == project_id).first()
            if not audio_file:
                raise Exception("No audio file found for this project")
            
            # [Rest of single audio composition logic...]
            # (Use the existing implementation from the fixed video composer)
            
            # For brevity, I'll call the multi-audio version with single file
            return compose_video_multi_audio.apply_async(
                args=[project_id, composition_settings],
                task_id=self.request.id
            ).get()
            
    except Exception as e:
        if db:
            db.rollback()
        raise e
    finally:
        if db:
            db.close()

@celery_app.task(bind=True)
def compose_video_multi_audio(self, project_id: str, composition_settings: dict):
    """Compose final video from multiple audio files and images using FFmpeg"""
    db = get_db_session()
    
    try:
        # Update job status
        current_task.update_state(state='PROGRESS', meta={'progress': 5, 'status': 'Initializing multi-audio composition'})
        
        # Get project and validate
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise Exception("Project not found")
        
        current_task.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Loading audio files'})
        
        # Get ALL audio files for this project (not just one)
        audio_files = db.query(AudioFile).filter(AudioFile.project_id == project_id).all()
        if not audio_files:
            raise Exception("No audio files found for this project")
        
        # Construct full audio file paths
        audio_paths = []
        total_duration = 0
        
        for audio_file in audio_files:
            if audio_file.file_path.startswith('uploads/'):
                audio_path = audio_file.file_path
            elif '/' in audio_file.file_path:
                audio_path = audio_file.file_path
            else:
                audio_path = os.path.join("uploads", audio_file.file_path)
            
            if not os.path.exists(audio_path):
                print(f"Warning: Audio file not found: {audio_path}")
                continue
            
            audio_paths.append(audio_path)
            total_duration += audio_file.duration_seconds or 0
            print(f"Added audio file: {audio_path} ({audio_file.duration_seconds or 0:.2f}s)")
        
        if not audio_paths:
            raise Exception("No valid audio files found")
        
        print(f"Total audio duration: {total_duration:.2f} seconds from {len(audio_paths)} files")
        
        current_task.update_state(state='PROGRESS', meta={'progress': 20, 'status': 'Loading images'})
        
        # Get selected/approved images
        images = db.query(GeneratedImage).filter(
            GeneratedImage.project_id == project_id,
            GeneratedImage.status == "approved"
        ).all()
        
        if not images:
            raise Exception("No approved images found for this project")
        
        # Prepare image paths
        image_paths = []
        for img in images:
            if img.file_path:
                if img.file_path.startswith('uploads/'):
                    img_path = img.file_path
                elif '/' in img.file_path:
                    img_path = img.file_path
                else:
                    img_path = os.path.join("uploads", img.file_path)
                
                if os.path.exists(img_path):
                    image_paths.append(img_path)
                    print(f"Added image: {img_path}")
                else:
                    print(f"Warning: Image file not found: {img_path}")
            elif img.image_url and img.image_url.startswith('http'):
                print(f"Warning: External image URLs not yet supported: {img.image_url}")
        
        if not image_paths:
            raise Exception("No valid image files found")
        
        current_task.update_state(state='PROGRESS', meta={
            'progress': 30, 
            'status': f'Preparing multi-audio video composition: {len(audio_paths)} audio files + {len(image_paths)} images'
        })
        
        # Extract composition settings
        resolution = composition_settings.get("resolution", "1920x1080")
        fps = composition_settings.get("fps", 30)
        transition_duration = composition_settings.get("transition_duration", 1.0)
        add_ken_burns = composition_settings.get("add_ken_burns", False)
        image_distribution = composition_settings.get("image_distribution", "equal")
        
        print(f"Multi-audio video settings:")
        print(f"  Resolution: {resolution}")
        print(f"  FPS: {fps}")
        print(f"  Transition duration: {transition_duration}s")
        print(f"  Ken Burns: {add_ken_burns}")
        print(f"  Image distribution: {image_distribution}")
        print(f"  Audio files: {len(audio_paths)}")
        print(f"  Total expected duration: {total_duration:.2f}s")
        
        current_task.update_state(state='PROGRESS', meta={'progress': 40, 'status': 'Starting multi-audio FFmpeg composition'})
        
        # Create output path
        output_filename = f"video_{project.name}_multi_{uuid.uuid4().hex[:8]}.mp4"
        # Sanitize filename
        import re
        output_filename = re.sub(r'[^\w\-_\.]', '_', output_filename)
        output_path = os.path.join("uploads", output_filename)
        
        print(f"Creating multi-audio video: {output_path}")
        print(f"Audio sources: {[os.path.basename(p) for p in audio_paths]}")
        print(f"Image count: {len(image_paths)}")
        
        # Import the new multi-audio composer
        from .services.video_composer import MultiAudioVideoComposer
        
        # Create video using multi-audio composer
        composer = MultiAudioVideoComposer(audio_paths, image_paths)
        
        # Update progress during video creation
        current_task.update_state(state='PROGRESS', meta={
            'progress': 50, 
            'status': 'Combining audio files and rendering video (this may take several minutes)'
        })
        
        if add_ken_burns:
            video_path = composer.create_video_with_effects(
                resolution=resolution,
                fps=fps,
                add_ken_burns=add_ken_burns,
                image_distribution=image_distribution
            )
        else:
            video_path = composer.create_slideshow_video(
                resolution=resolution,
                fps=fps,
                transition_duration=transition_duration,
                image_distribution=image_distribution
            )
        
        current_task.update_state(state='PROGRESS', meta={'progress': 80, 'status': 'Finalizing multi-audio video'})
        
        # Move to final output path if needed
        if video_path != output_path:
            if os.path.exists(video_path):
                os.rename(video_path, output_path)
                video_path = output_path
        
        # Get video file info
        file_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0
        
        current_task.update_state(state='PROGRESS', meta={'progress': 90, 'status': 'Saving to database'})
        
        # Save video output to database
        video_output = VideoOutput(
            project_id=project_id,
            file_path=output_filename,  # Store relative path
            duration_seconds=float(total_duration),  # Use calculated total duration
            resolution=resolution,
            file_size_bytes=file_size,
            status="completed"
        )
        
        db.add(video_output)
        db.commit()
        
        # Cleanup temporary files
        composer.cleanup()
        
        # Get audio composition info for response
        audio_info = composer.get_audio_info()
        
        current_task.update_state(state='PROGRESS', meta={'progress': 100, 'status': 'Multi-audio video creation completed'})
        
        print(f"Multi-audio video created successfully: {video_path} ({file_size} bytes)")
        
        return {
            "video_id": str(video_output.id),
            "video_path": output_filename,
            "file_size": file_size,
            "duration": total_duration,
            "resolution": resolution,
            "status": "completed",
            "audio_info": {
                "file_count": len(audio_paths),
                "total_duration": total_duration,
                "individual_files": [os.path.basename(p) for p in audio_paths]
            },
            "composition_settings": composition_settings
        }
        
    except Exception as e:
        print(f"Multi-audio video composition error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if db:
            db.rollback()
        raise e
    finally:
        if db:
            db.close()

# New task to get audio composition preview
@celery_app.task(bind=True)
def get_audio_composition_info(self, project_id: str):
    """Get information about how multiple audio files will be combined"""
    db = get_db_session()
    
    try:
        # Get all audio files for the project
        audio_files = db.query(AudioFile).filter(AudioFile.project_id == project_id).all()
        
        if not audio_files:
            return {"error": "No audio files found"}
        
        total_duration = 0
        file_info = []
        
        for i, audio_file in enumerate(audio_files):
            duration = audio_file.duration_seconds or 0
            total_duration += duration
            
            file_info.append({
                "index": i + 1,
                "filename": audio_file.filename,
                "duration": duration,
                "start_time": total_duration - duration,
                "end_time": total_duration,
                "size": audio_file.file_size_bytes
            })
        
        return {
            "file_count": len(audio_files),
            "total_duration": total_duration,
            "files": file_info,
            "preview": {
                "estimated_video_length": f"{int(total_duration // 60)}:{int(total_duration % 60):02d}",
                "combination_method": "sequential",
                "transition_type": "seamless"
            }
        }
        
    except Exception as e:
        return {"error": str(e)}
    finally:
        if db:
            db.close()

            
@celery_app.task(bind=True)
def publish_to_youtube(self, project_id: str, video_id: str, youtube_settings: dict):
    """Publish video to YouTube (mock implementation)"""
    db = get_db_session()
    
    try:
        # Update job status
        current_task.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Initializing YouTube upload'})
        
        # Get video output
        video_output = db.query(VideoOutput).filter(VideoOutput.id == video_id).first()
        if not video_output:
            raise Exception("Video output not found")
        
        current_task.update_state(state='PROGRESS', meta={'progress': 30, 'status': 'Connecting to YouTube API'})
        
        # Mock YouTube upload
        from .services.mock_services import get_youtube_service
        youtube_service = get_youtube_service()
        
        # Simulate upload delay
        import time
        time.sleep(3)
        
        current_task.update_state(state='PROGRESS', meta={'progress': 70, 'status': 'Uploading video'})
        
        # Mock upload result
        mock_video_id = f"mock_{uuid.uuid4().hex[:8]}"
        
        # Update video output with YouTube ID
        video_output.youtube_video_id = mock_video_id
        video_output.status = "published"
        db.commit()
        
        current_task.update_state(state='PROGRESS', meta={'progress': 100, 'status': 'Upload completed'})
        
        return {
            "youtube_video_id": mock_video_id,
            "status": "published",
            "url": f"https://youtube.com/watch?v={mock_video_id}"
        }
        
    except Exception as e:
        if db:
            db.rollback()
        raise e
    finally:
        if db:
            db.close()

# New task for checking video composition progress
@celery_app.task(bind=True)
def get_video_composition_status(self, task_id: str):
    """Get the status of a video composition task"""
    try:
        from celery.result import AsyncResult
        result = AsyncResult(task_id, app=celery_app)
        
        if result.state == 'PENDING':
            return {'status': 'pending', 'progress': 0}
        elif result.state == 'PROGRESS':
            return {
                'status': 'progress',
                'progress': result.info.get('progress', 0),
                'message': result.info.get('status', 'Processing...')
            }
        elif result.state == 'SUCCESS':
            return {
                'status': 'success',
                'progress': 100,
                'result': result.info
            }
        elif result.state == 'FAILURE':
            return {
                'status': 'failed',
                'progress': 0,
                'error': str(result.info)
            }
        else:
            return {
                'status': result.state.lower(),
                'progress': 0
            }
    except Exception as e:
        return {
            'status': 'error',
            'progress': 0,
            'error': str(e)
        }