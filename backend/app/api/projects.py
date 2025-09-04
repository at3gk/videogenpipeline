from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Dict
from uuid import UUID
import os
import aiofiles
import uuid
from datetime import datetime

from ..database import get_db
from ..models import Project, AudioFile, GeneratedImage, VideoOutput, ProcessingJob
from ..schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    AudioFileResponse, GeneratedImageResponse, VideoOutputResponse,
    ImagePrompt, VideoCompositionSettings, MultiAudioVideoCompositionSettings, EnhancedVideoCompositionSettings, TaskStartedResponse, ImageApprovalRequest, ImagePreviewResponse
)
from ..tasks import generate_ai_image, compose_video_multi_audio, publish_to_youtube
from ..config import settings
from ..services.preview_cache import preview_cache

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project"""
    # For now, use the first user (admin)
    from ..models import User
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="No users found")
    
    db_project = Project(
        name=project.name,
        user_id=user.id
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    return db_project

@router.get("/", response_model=List[ProjectResponse])
async def get_projects(db: Session = Depends(get_db)):
    """Get all projects"""
    projects = db.query(Project).all()
    return projects

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, db: Session = Depends(get_db)):
    """Get project details"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: UUID, project: ProjectUpdate, db: Session = Depends(get_db)):
    """Update project details"""
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    for field, value in project.dict(exclude_unset=True).items():
        setattr(db_project, field, value)
    
    db_project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_project)
    
    return db_project

@router.delete("/{project_id}")
async def delete_project(project_id: UUID, db: Session = Depends(get_db)):
    """Delete a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    
    return {"message": "Project deleted successfully"}

@router.post("/{project_id}/cleanup-orphaned-images")
async def cleanup_orphaned_images(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """Remove database records for images that no longer exist on disk"""
    print(f"🧹 Starting orphaned image cleanup for project {project_id}")
    
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get all images for this project
    images = db.query(GeneratedImage).filter(GeneratedImage.project_id == project_id).all()
    
    orphaned_count = 0
    valid_count = 0
    orphaned_details = []
    
    for img in images:
        is_orphaned = False
        img_path = None
        
        if img.file_path:
            # Check if file exists on disk
            if img.file_path.startswith('uploads/'):
                img_path = img.file_path
            elif '/' in img.file_path:
                img_path = img.file_path
            else:
                img_path = os.path.join("uploads", img.file_path)
            
            print(f"  Checking: {img_path}")
            
            if not os.path.exists(img_path):
                is_orphaned = True
                orphaned_details.append(f"Missing file: {img_path}")
                print(f"    ❌ File not found")
            else:
                # File exists, verify it's a valid image
                try:
                    from PIL import Image as PILImage
                    with PILImage.open(img_path) as pil_img:
                        pass  # Just verify it can be opened
                    valid_count += 1
                    print(f"    ✅ Valid image file")
                except Exception as e:
                    is_orphaned = True
                    orphaned_details.append(f"Corrupted file: {img_path} - {str(e)}")
                    print(f"    ❌ Corrupted image: {e}")
        elif img.image_url and img.image_url.startswith('http'):
            # External URLs are considered valid (we don't validate them)
            valid_count += 1
            print(f"  External URL: {img.image_url} - assumed valid")
        else:
            # No file_path or image_url - definitely orphaned
            is_orphaned = True
            orphaned_details.append(f"No file path or URL: ID {img.id}")
            print(f"  ❌ No file path or URL for image {img.id}")
        
        if is_orphaned:
            print(f"  🗑️  Removing orphaned image: {img.id} - {img.prompt[:50]}...")
            db.delete(img)
            orphaned_count += 1
    
    if orphaned_count > 0:
        db.commit()
        print(f"✅ Cleanup completed: Removed {orphaned_count} orphaned images, {valid_count} valid images remain")
    else:
        print(f"✅ No orphaned images found, {valid_count} valid images remain")
    
    return {
        "message": f"Cleanup completed",
        "orphaned_removed": orphaned_count,
        "valid_remaining": valid_count,
        "orphaned_details": orphaned_details
    }

@router.post("/{project_id}/audio", response_model=AudioFileResponse)
async def upload_audio(
    project_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload audio file for project"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate file type
    allowed_types = {'audio/mpeg', 'audio/wav', 'audio/mp4', 'audio/flac'}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # Validate file size
    if file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Create uploads directory if it doesn't exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Generate unique filename but keep original extension
    file_extension = os.path.splitext(file.filename)[1]
    import re
    safe_name = re.sub(r'[^\w\-_\.]', '_', file.filename or 'audio')
    base_name = os.path.splitext(safe_name)[0]
    unique_filename = f"{base_name}_{uuid.uuid4().hex[:8]}{file_extension}"
    
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    print(f"DEBUG: Uploading file:")
    print(f"  Original filename: {file.filename}")
    print(f"  Safe filename: {safe_name}")
    print(f"  Unique filename: {unique_filename}")
    print(f"  Full path: {file_path}")
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    print(f"DEBUG: File saved successfully to: {file_path}")
    print(f"DEBUG: File exists: {os.path.exists(file_path)}")
    print(f"DEBUG: File size on disk: {os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'}")
    
    # ✅ ENHANCED DURATION CALCULATION WITH DEBUGGING
    duration_seconds = None
    
    # Method 1: Try ffprobe first
    try:
        import subprocess
        print(f"DEBUG: Trying ffprobe for duration calculation...")
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', file_path
        ]
        print(f"DEBUG: ffprobe command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration_str = result.stdout.strip()
        print(f"DEBUG: ffprobe raw output: '{duration_str}'")
        
        if duration_str and duration_str != '':
            duration_seconds = float(duration_str)
            print(f"✅ SUCCESS: ffprobe calculated duration: {duration_seconds:.2f} seconds")
        else:
            print(f"⚠️  WARNING: ffprobe returned empty duration")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR: ffprobe failed with return code {e.returncode}")
        print(f"   STDERR: {e.stderr}")
        print(f"   STDOUT: {e.stdout}")
    except Exception as e:
        print(f"❌ ERROR: ffprobe exception: {e}")
    
    # Method 2: Try librosa if ffprobe failed
    if duration_seconds is None:
        try:
            print(f"DEBUG: Trying librosa for duration calculation...")
            import librosa
            duration_seconds = librosa.get_duration(path=file_path)
            print(f"✅ SUCCESS: librosa calculated duration: {duration_seconds:.2f} seconds")
        except Exception as e:
            print(f"❌ ERROR: librosa failed: {e}")
    
    # Method 3: Try alternative ffprobe command
    if duration_seconds is None:
        try:
            print(f"DEBUG: Trying alternative ffprobe method...")
            cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', file_path
            ]
            print(f"DEBUG: Alternative ffprobe command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration_str = result.stdout.strip()
            print(f"DEBUG: Alternative ffprobe output: '{duration_str}'")
            
            if duration_str and duration_str != '':
                duration_seconds = float(duration_str)
                print(f"✅ SUCCESS: Alternative ffprobe duration: {duration_seconds:.2f} seconds")
                
        except Exception as e:
            print(f"❌ ERROR: Alternative ffprobe failed: {e}")
    
    # Final fallback
    if duration_seconds is None or duration_seconds <= 0:
        print(f"⚠️  WARNING: All duration calculation methods failed, using fallback")
        duration_seconds = None  # Let the database handle NULL
    
    print(f"🎵 FINAL DURATION: {duration_seconds}")
    
    # Create audio file record
    audio_file = AudioFile(
        project_id=project_id,
        filename=file.filename,
        file_path=unique_filename,
        file_size_bytes=file.size,
        mime_type=file.content_type,
        duration_seconds=duration_seconds
    )
    
    db.add(audio_file)
    db.commit()
    db.refresh(audio_file)
    
    print(f"DEBUG: Audio file record saved:")
    print(f"  ID: {audio_file.id}")
    print(f"  filename: {audio_file.filename}")
    print(f"  duration_seconds: {audio_file.duration_seconds}")
    
    return audio_file

@router.get("/{project_id}/audio", response_model=List[AudioFileResponse])
async def get_project_audio_files(project_id: UUID, db: Session = Depends(get_db)):
    """Get all audio files for a project"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    audio_files = db.query(AudioFile).filter(AudioFile.project_id == project_id).all()
    
    print(f"DEBUG: Found {len(audio_files)} audio files for project {project_id}")
    for audio_file in audio_files:
        print(f"  - ID: {audio_file.id}")
        print(f"  - filename: {audio_file.filename}")
        print(f"  - file_path: {audio_file.file_path}")
        print(f"  - file_size_bytes: {audio_file.file_size_bytes}")
    
    return audio_files

@router.delete("/{project_id}/audio/{audio_id}")
async def remove_audio_file(
    project_id: UUID,
    audio_id: UUID,
    db: Session = Depends(get_db)
):
    """Remove an audio file from the project"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Find the audio file
    audio_file = db.query(AudioFile).filter(
        AudioFile.id == audio_id,
        AudioFile.project_id == project_id
    ).first()
    
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    try:
        # Delete the physical file if it exists
        if audio_file.file_path:
            # Handle different file_path formats
            if audio_file.file_path.startswith('uploads/'):
                # Old format: "uploads/filename.mp3"
                file_to_delete = audio_file.file_path
            elif '/' in audio_file.file_path:
                # Full path format
                file_to_delete = audio_file.file_path
            else:
                # New format: just filename "filename.mp3"
                file_to_delete = os.path.join("uploads", audio_file.file_path)
            
            print(f"DEBUG: Attempting to delete file: {file_to_delete}")
            
            if os.path.exists(file_to_delete):
                os.remove(file_to_delete)
                print(f"DEBUG: Successfully deleted file: {file_to_delete}")
            else:
                print(f"DEBUG: File not found on filesystem: {file_to_delete}")
                # List available files for debugging
                if os.path.exists("uploads"):
                    available_files = os.listdir("uploads")
                    print(f"DEBUG: Available files: {available_files}")
        
        # Delete from database
        db.delete(audio_file)
        db.commit()
        
        print(f"DEBUG: Removed audio file {audio_id} from database")
        return {"message": "Audio file removed successfully"}
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: Failed to remove audio file: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to remove audio file: {str(e)}")

@router.post("/{project_id}/generate-image", response_model=TaskStartedResponse)
async def generate_image(
    project_id: UUID,
    prompt: ImagePrompt,
    db: Session = Depends(get_db)
):
    """Generate AI image from prompt"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        # Start background task
        task = generate_ai_image.delay(
            str(project_id),
            prompt.prompt,
            prompt.service
        )
        
        # Create processing job record
        processing_job = ProcessingJob(
            project_id=project_id,
            job_type="image_generation",
            status="pending"
        )
        
        db.add(processing_job)
        db.commit()
        
        return {
            "message": "Image generation started",
            "task_id": task.id,
            "job_id": str(processing_job.id)
        }
    except Exception as e:
        # If Celery task fails to start, create a failed job record
        processing_job = ProcessingJob(
            project_id=project_id,
            job_type="image_generation",
            status="failed",
            error_message=f"Failed to start task: {str(e)}"
        )
        
        db.add(processing_job)
        db.commit()
        
        # Return error response instead of 500
        raise HTTPException(
            status_code=503, 
            detail=f"Image generation service temporarily unavailable. Please try again later. Error: {str(e)}"
        )

@router.post("/{project_id}/compose-video", response_model=VideoOutputResponse)
async def compose_video_endpoint(
    project_id: UUID,
    composition_settings: VideoCompositionSettings,
    db: Session = Depends(get_db)
):
    """Create video from audio and images"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if project has audio file
    audio_file = db.query(AudioFile).filter(AudioFile.project_id == project_id).first()
    if not audio_file:
        raise HTTPException(status_code=400, detail="Project must have an audio file")
    
    # Start background task
    task = compose_video.delay(
        str(project_id),
        composition_settings.dict()
    )
    
    # Create processing job record
    processing_job = ProcessingJob(
        project_id=project_id,
        job_type="video_composition",
        status="pending"
    )
    
    db.add(processing_job)
    db.commit()
    
    return {
        "message": "Video composition started",
        "task_id": task.id,
        "job_id": str(processing_job.id)
    }

@router.get("/{project_id}/images", response_model=List[GeneratedImageResponse])
async def get_project_images(project_id: UUID, db: Session = Depends(get_db)):
    """Get all generated images for a project"""
    images = db.query(GeneratedImage).filter(GeneratedImage.project_id == project_id).all()
    return images

@router.get("/{project_id}/videos", response_model=List[VideoOutputResponse])
async def get_project_videos(project_id: UUID, db: Session = Depends(get_db)):
    """Get all video outputs for a project"""
    videos = db.query(VideoOutput).filter(VideoOutput.project_id == project_id).all()
    return videos

@router.get("/{project_id}/jobs", response_model=List[dict])
async def get_project_jobs(project_id: UUID, db: Session = Depends(get_db)):
    """Get all processing jobs for a project"""
    jobs = db.query(ProcessingJob).filter(ProcessingJob.project_id == project_id).all()
    return [
        {
            "id": str(job.id),
            "job_type": job.job_type,
            "status": job.status,
            "progress": job.progress,
            "created_at": job.created_at
        }
        for job in jobs
    ]

@router.post("/{project_id}/generate-image-preview", response_model=ImagePreviewResponse)
async def generate_image_preview(
    project_id: UUID,
    prompt: ImagePrompt,
    db: Session = Depends(get_db)
):
    """Generate AI image preview (doesn't save to project until approved)"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        print(f"Generating preview for project {project_id}")
        print(f"Prompt: {prompt.prompt}")
        print(f"Service: {prompt.service}")
        print(f"Size: {prompt.size}")
        print(f"Quality: {prompt.quality}")
        
        # Generate preview image using your existing service with parameters
        from ..services.mock_services import get_ai_service
        ai_service = get_ai_service(prompt.service)
        
        # Create a unique task ID
        task_id = str(uuid.uuid4())
        
        if prompt.service == "stable_diffusion":
            # Pass the parameters from the frontend
            temp_image_path = ai_service.generate_image(
                prompt.prompt,
                resolution=prompt.size,  # Pass resolution
                steps=prompt.quality,    # Pass quality steps
                size=prompt.size,        # Also pass as size for compatibility
                quality=prompt.quality   # Also pass as quality for compatibility
            )
            print(f"SD Generated image at: {temp_image_path}")
            
            # Create preview URL
            if temp_image_path.startswith("uploads/"):
                preview_url = f"/{temp_image_path}"
            else:
                filename = os.path.basename(temp_image_path)
                preview_url = f"/uploads/{filename}"
                
        else:
            # For other services (DALL-E, Midjourney)
            preview_url = ai_service.generate_image(prompt.prompt, size=prompt.size, quality=prompt.quality)
            temp_image_path = None
        
        print(f"Preview URL: {preview_url}")
        
        # Store preview info
        preview_data = {
            "project_id": str(project_id),
            "prompt": prompt.prompt,
            "service": prompt.service,
            "size": prompt.size,
            "quality": prompt.quality,
            "preview_url": preview_url,
            "file_path": temp_image_path,
            "created_at": datetime.utcnow().isoformat()
        }
        
        preview_cache.set(task_id, preview_data)
        print(f"Stored preview data for task {task_id}")
        
        return ImagePreviewResponse(
            task_id=task_id,
            preview_url=preview_url,
            prompt=prompt.prompt,
            service=prompt.service
        )
        
    except Exception as e:
        print(f"Error in generate_image_preview: {str(e)}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=503, 
            detail=f"Image generation service error: {str(e)}"
        )

@router.post("/{project_id}/generate-image-batch-preview", response_model=List[ImagePreviewResponse])
async def generate_image_batch_preview(
    project_id: UUID,
    request: Dict,  # Contains prompt data + num_images
    db: Session = Depends(get_db)
):
    """Generate multiple AI image previews at once"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        # Extract parameters
        prompt_data = request.get('prompt', {})
        num_images = request.get('num_images', 1)
        
        print(f"Generating {num_images} previews for project {project_id}")
        print(f"Prompt data: {prompt_data}")
        
        # Validate num_images
        num_images = min(max(1, int(num_images)), 6)  # Limit to 1-6 images
        
        # Generate multiple preview images
        from ..services.mock_services import get_ai_service
        ai_service = get_ai_service(prompt_data.get('service', 'stable_diffusion'))
        
        preview_responses = []
        
        if prompt_data.get('service') == "stable_diffusion":
            # Use batch generation for Stable Diffusion
            try:
                generated_images = ai_service.generate_images(
                    prompt_data.get('prompt', ''),
                    num_images=num_images,
                    resolution=prompt_data.get('size', '1024x1024'),
                    steps=prompt_data.get('quality', '25'),
                    size=prompt_data.get('size', '1024x1024'),
                    quality=prompt_data.get('quality', '25')
                )
                
                for i, img_data in enumerate(generated_images):
                    task_id = str(uuid.uuid4())
                    
                    # Create preview URL
                    if img_data['path'].startswith("uploads/"):
                        preview_url = f"/{img_data['path']}"
                    else:
                        filename = os.path.basename(img_data['path'])
                        preview_url = f"/uploads/{filename}"
                    
                    # Store preview info
                    preview_data = {
                        "project_id": str(project_id),
                        "prompt": prompt_data.get('prompt', ''),
                        "service": prompt_data.get('service', 'stable_diffusion'),
                        "size": prompt_data.get('size', '1024x1024'),
                        "quality": prompt_data.get('quality', '25'),
                        "preview_url": preview_url,
                        "file_path": img_data['path'],
                        "seed": img_data.get('seed'),
                        "resolution": img_data.get('resolution'),
                        "steps": img_data.get('steps'),
                        "batch_index": i + 1,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    preview_cache.set(task_id, preview_data)
                    
                    preview_responses.append(ImagePreviewResponse(
                        task_id=task_id,
                        preview_url=preview_url,
                        prompt=prompt_data.get('prompt', ''),
                        service=prompt_data.get('service', 'stable_diffusion')
                    ))
                
            except Exception as e:
                print(f"Batch generation failed: {e}")
                raise HTTPException(status_code=503, detail=f"Batch generation failed: {str(e)}")
                
        else:
            # For other services, generate individually
            for i in range(num_images):
                try:
                    task_id = str(uuid.uuid4())
                    preview_url = ai_service.generate_image(
                        prompt_data.get('prompt', ''),
                        size=prompt_data.get('size', '1024x1024'),
                        quality=prompt_data.get('quality', 'standard')
                    )
                    
                    # Store preview info
                    preview_data = {
                        "project_id": str(project_id),
                        "prompt": prompt_data.get('prompt', ''),
                        "service": prompt_data.get('service', 'dalle'),
                        "size": prompt_data.get('size', '1024x1024'),
                        "quality": prompt_data.get('quality', 'standard'),
                        "preview_url": preview_url,
                        "file_path": None,
                        "batch_index": i + 1,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    preview_cache.set(task_id, preview_data)
                    
                    preview_responses.append(ImagePreviewResponse(
                        task_id=task_id,
                        preview_url=preview_url,
                        prompt=prompt_data.get('prompt', ''),
                        service=prompt_data.get('service', 'dalle')
                    ))
                    
                except Exception as e:
                    print(f"Failed to generate image {i+1}: {e}")
                    continue
        
        if not preview_responses:
            raise HTTPException(status_code=503, detail="Failed to generate any images")
        
        print(f"Successfully generated {len(preview_responses)} preview images")
        return preview_responses
        
    except Exception as e:
        print(f"Error in batch preview generation: {str(e)}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=503, 
            detail=f"Batch image generation service error: {str(e)}"
        )
@router.post("/{project_id}/approve-image", response_model=GeneratedImageResponse)
async def approve_image(
    project_id: UUID,
    request: Dict,  # Accept a dict with preview_id
    db: Session = Depends(get_db)
):
    """Approve a preview image and save it to the project"""
    preview_id = request.get("preview_id")
    
    if not preview_id:
        raise HTTPException(status_code=400, detail="preview_id is required")
    
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get preview data using PreviewCache method (not dictionary access)
    preview_data = preview_cache.get(preview_id)
    if not preview_data:
        raise HTTPException(status_code=404, detail="Preview image not found or expired")
    
    try:
        # Create the approved image record
        generated_image = GeneratedImage(
            project_id=project_id,
            prompt=preview_data["prompt"],
            image_url=preview_data["preview_url"],
            file_path=preview_data.get("file_path"),
            generator_service=preview_data["service"],
            generation_params={
                "prompt": preview_data["prompt"], 
                "service": preview_data["service"],
                "approved_from_preview": True
            },
            status="approved"
        )
        
        db.add(generated_image)
        db.commit()
        db.refresh(generated_image)
        
        # Remove from preview cache using .delete() method
        preview_cache.delete(preview_id)
        
        print(f"Approved image {generated_image.id} for project {project_id}")
        
        return generated_image
        
    except Exception as e:
        db.rollback()
        print(f"Error approving image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to approve image: {str(e)}")

@router.post("/{project_id}/reject-image")
async def reject_image(
    project_id: UUID,
    request: Dict,  # Contains preview_id
    db: Session = Depends(get_db)
):
    """Reject a preview image and clean up files"""
    preview_id = request.get("preview_id")
    
    if not preview_id:
        raise HTTPException(status_code=400, detail="preview_id is required")
    
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        # Get preview data using PreviewCache method
        preview_data = preview_cache.get(preview_id)
        if not preview_data:
            # If preview doesn't exist in cache, it's already been handled or expired
            return {"message": "Preview image not found or already processed"}
        
        print(f"Rejecting preview image: {preview_id}")
        print(f"Preview data: {preview_data}")
        
        # If it's a local file (from stable diffusion), delete the physical file
        file_path = preview_data.get("file_path")
        if file_path:
            try:
                # Handle different file path formats
                if file_path.startswith("uploads/"):
                    full_path = file_path
                elif "/" not in file_path:
                    full_path = f"uploads/{file_path}"
                else:
                    full_path = file_path
                
                print(f"Attempting to delete file: {full_path}")
                
                if os.path.exists(full_path):
                    os.remove(full_path)
                    print(f"Successfully deleted file: {full_path}")
                else:
                    print(f"File not found: {full_path}")
                    # List available files for debugging
                    if os.path.exists("uploads"):
                        available_files = os.listdir("uploads")[:10]  # Limit output
                        print(f"Available files in uploads (first 10): {available_files}")
                        
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
                # Continue with cache cleanup even if file deletion fails
        
        # Remove from preview cache
        preview_cache.delete(preview_id)
        print(f"Removed preview {preview_id} from cache")
        
        return {"message": "Preview image rejected and cleaned up successfully"}
        
    except Exception as e:
        print(f"Error rejecting preview image: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Still try to clean up the cache entry
        try:
            preview_cache.delete(preview_id)
        except:
            pass
            
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to reject preview image: {str(e)}"
        )

@router.delete("/{project_id}/images/{image_id}")
async def remove_image(
    project_id: UUID,
    image_id: UUID,
    db: Session = Depends(get_db)
):
    """Remove an image from the project"""
    image = db.query(GeneratedImage).filter(
        GeneratedImage.id == image_id,
        GeneratedImage.project_id == project_id
    ).first()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Delete the file if it exists locally
    if image.file_path and os.path.exists(image.file_path):
        os.remove(image.file_path)
    
    # Delete from database
    db.delete(image)
    db.commit()
    
    return {"message": "Image removed successfully"}

@router.get("/{project_id}/images", response_model=List[GeneratedImageResponse])
async def get_project_images(project_id: UUID, db: Session = Depends(get_db)):
    """Get all approved images for a project"""
    images = db.query(GeneratedImage).filter(
        GeneratedImage.project_id == project_id,
        GeneratedImage.status == "approved"  # Only return approved images
    ).all()
    return images

@router.post("/{project_id}/compose-video-ffmpeg", response_model=dict)
async def compose_video_ffmpeg_endpoint(
    project_id: UUID,
    composition_settings: VideoCompositionSettings,
    db: Session = Depends(get_db)
):
    """Create video from audio and images using FFmpeg"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if project has audio file
    audio_file = db.query(AudioFile).filter(AudioFile.project_id == project_id).first()
    if not audio_file:
        raise HTTPException(status_code=400, detail="Project must have an audio file")
    
    # Check if project has approved images
    images = db.query(GeneratedImage).filter(
        GeneratedImage.project_id == project_id,
        GeneratedImage.status == "approved"
    ).count()
    
    if images == 0:
        raise HTTPException(status_code=400, detail="Project must have at least one approved image")
    
    try:
        # Start background task
        from ..tasks import compose_video_ffmpeg
        task = compose_video_ffmpeg.delay(
            str(project_id),
            composition_settings.dict()
        )
        
        # Create processing job record
        processing_job = ProcessingJob(
            project_id=project_id,
            job_type="video_composition_ffmpeg",
            status="pending",
            progress=0
        )
        
        db.add(processing_job)
        db.commit()
        
        return {
            "message": "Video composition started using FFmpeg",
            "task_id": task.id,
            "job_id": str(processing_job.id),
            "status": "pending"
        }
        
    except Exception as e:
        # Create failed job record
        processing_job = ProcessingJob(
            project_id=project_id,
            job_type="video_composition_ffmpeg",
            status="failed",
            error_message=f"Failed to start task: {str(e)}"
        )
        
        db.add(processing_job)
        db.commit()
        
        raise HTTPException(
            status_code=503, 
            detail=f"Video composition service unavailable: {str(e)}"
        )

@router.post("/{project_id}/compose-video-multi-audio", response_model=dict)
async def compose_video_multi_audio_endpoint(
    project_id: UUID,
    composition_settings: dict,  # Use dict to accept flexible settings
    db: Session = Depends(get_db)
):
    """Create video from multiple audio files and images using FFmpeg"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if project has audio files
    audio_files = db.query(AudioFile).filter(AudioFile.project_id == project_id).all()
    if not audio_files:
        raise HTTPException(status_code=400, detail="Project must have at least one audio file")
    
    # Check if project has approved images
    images = db.query(GeneratedImage).filter(
        GeneratedImage.project_id == project_id,
        GeneratedImage.status == "approved"
    ).count()
    
    if images == 0:
        raise HTTPException(status_code=400, detail="Project must have at least one approved image")
    
    try:
        # Start multi-audio background task
        from ..tasks import compose_video_multi_audio
        task = compose_video_multi_audio.delay(
            str(project_id),
            composition_settings
        )
        
        # Create processing job record
        processing_job = ProcessingJob(
            project_id=project_id,
            job_type="video_composition_multi_audio",
            status="pending",
            progress=0
        )
        
        db.add(processing_job)
        db.commit()
        
        return {
            "message": f"Multi-audio video composition started with {len(audio_files)} audio files",
            "task_id": task.id,
            "job_id": str(processing_job.id),
            "status": "pending",
            "audio_files_count": len(audio_files),
            "settings": composition_settings
        }
        
    except Exception as e:
        # Create failed job record
        processing_job = ProcessingJob(
            project_id=project_id,
            job_type="video_composition_multi_audio",
            status="failed",
            error_message=f"Failed to start task: {str(e)}"
        )
        
        db.add(processing_job)
        db.commit()
        
        raise HTTPException(
            status_code=503, 
            detail=f"Multi-audio video composition service unavailable: {str(e)}"
        )

@router.get("/{project_id}/audio-composition-info")
async def get_audio_composition_info(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    """Get information about how multiple audio files will be combined"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        from ..tasks import get_audio_composition_info
        result = get_audio_composition_info.delay(str(project_id)).get()
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting audio composition info: {str(e)}"
        )

# Update the existing enhanced endpoint to automatically detect multi-audio
@router.post("/{project_id}/compose-video-enhanced", response_model=dict)
async def compose_video_enhanced_endpoint(
    project_id: UUID,
    composition_settings: dict,  # Accept flexible settings
    db: Session = Depends(get_db)
):
    """Enhanced video composition that automatically detects single or multi-audio"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Count audio files to determine which composition method to use
    audio_files = db.query(AudioFile).filter(AudioFile.project_id == project_id).all()
    if not audio_files:
        raise HTTPException(status_code=400, detail="Project must have at least one audio file")
    
    # Check if project has approved images
    images = db.query(GeneratedImage).filter(
        GeneratedImage.project_id == project_id,
        GeneratedImage.status == "approved"
    ).count()
    
    if images == 0:
        raise HTTPException(status_code=400, detail="Project must have at least one approved image")
    
    try:
        if len(audio_files) > 1:
            # Multi-audio composition
            from ..tasks import compose_video_multi_audio
            task = compose_video_multi_audio.delay(
                str(project_id),
                composition_settings
            )
            
            processing_job = ProcessingJob(
                project_id=project_id,
                job_type="video_composition_multi_audio",
                status="pending",
                progress=0
            )
            
            message = f"Multi-audio video composition started with {len(audio_files)} audio files"
        else:
            # Single audio composition
            from ..tasks import compose_video_ffmpeg
            task = compose_video_ffmpeg.delay(
                str(project_id),
                composition_settings
            )
            
            processing_job = ProcessingJob(
                project_id=project_id,
                job_type="video_composition_enhanced",
                status="pending",
                progress=0
            )
            
            message = "Enhanced video composition started"
        
        db.add(processing_job)
        db.commit()
        
        return {
            "message": message,
            "task_id": task.id,
            "job_id": str(processing_job.id),
            "status": "pending",
            "is_multi_audio": len(audio_files) > 1,
            "audio_files_count": len(audio_files),
            "settings": composition_settings
        }
        
    except Exception as e:
        processing_job = ProcessingJob(
            project_id=project_id,
            job_type="video_composition_enhanced",
            status="failed",
            error_message=f"Failed to start task: {str(e)}"
        )
        
        db.add(processing_job)
        db.commit()
        
        raise HTTPException(
            status_code=503,
            detail=f"Enhanced video composition service unavailable: {str(e)}"
        )

@router.get("/{project_id}/video-status/{task_id}")
async def get_video_composition_status(
    project_id: UUID,
    task_id: str,
    db: Session = Depends(get_db)
):
    """Get the status of a video composition task"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        from celery.result import AsyncResult
        from ..celery_app import celery_app
        
        result = AsyncResult(task_id, app=celery_app)
        
        if result.state == 'PENDING':
            return {
                'status': 'pending', 
                'progress': 0,
                'message': 'Task is waiting to start'
            }
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
                'message': 'Video composition completed',
                'result': result.result
            }
        elif result.state == 'FAILURE':
            return {
                'status': 'failed',
                'progress': 0,
                'message': 'Video composition failed',
                'error': str(result.info)
            }
        else:
            return {
                'status': result.state.lower(),
                'progress': 0,
                'message': f'Task state: {result.state}'
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking task status: {str(e)}"
        )

@router.post("/{project_id}/cancel-video/{task_id}")
async def cancel_video_composition(
    project_id: UUID,
    task_id: str,
    db: Session = Depends(get_db)
):
    """Cancel a running video composition task"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        from ..celery_app import celery_app
        
        # Revoke the task
        celery_app.control.revoke(task_id, terminate=True)
        
        # Update processing job status
        processing_job = db.query(ProcessingJob).filter(
            ProcessingJob.project_id == project_id,
            ProcessingJob.job_type.in_(["video_composition", "video_composition_ffmpeg"])
        ).order_by(ProcessingJob.created_at.desc()).first()
        
        if processing_job:
            processing_job.status = "cancelled"
            processing_job.error_message = "Cancelled by user"
            db.commit()
        
        return {
            "message": "Video composition task cancelled",
            "task_id": task_id,
            "status": "cancelled"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error cancelling task: {str(e)}"
        )

@router.get("/{project_id}/video-preview/{video_id}")
async def get_video_preview(
    project_id: UUID,
    video_id: UUID,
    db: Session = Depends(get_db)
):
    """Get video preview information"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get video output
    video = db.query(VideoOutput).filter(
        VideoOutput.id == video_id,
        VideoOutput.project_id == project_id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Generate video URL
    base_url = "http://localhost:8000"  # This should come from config
    video_url = f"{base_url}/uploads/{video.file_path}"
    
    return {
        "id": str(video.id),
        "project_id": str(video.project_id),
        "video_url": video_url,
        "file_path": video.file_path,
        "duration_seconds": float(video.duration_seconds) if video.duration_seconds else 0,
        "resolution": video.resolution,
        "file_size_bytes": video.file_size_bytes,
        "status": video.status,
        "youtube_video_id": video.youtube_video_id,
        "created_at": video.created_at.isoformat(),
        "download_url": video_url
    }
# # Simple in-memory cache for preview images (in production, use Redis)
# preview_cache: Dict[str, Dict] = {}
