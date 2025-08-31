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
    ImagePrompt, VideoCompositionSettings, TaskStartedResponse, ImageApprovalRequest, ImagePreviewResponse
)
from ..tasks import generate_ai_image, compose_video, publish_to_youtube
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
    # Use a sanitized version of the original filename + UUID for uniqueness
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
    
    # Create audio file record - store the actual filename that was created
    audio_file = AudioFile(
        project_id=project_id,
        filename=file.filename,  # Keep original filename for display
        file_path=unique_filename,  # Store the actual sanitized filename that was created
        file_size_bytes=file.size,
        mime_type=file.content_type
    )
    
    db.add(audio_file)
    db.commit()
    db.refresh(audio_file)
    
    print(f"DEBUG: Audio file record created:")
    print(f"  ID: {audio_file.id}")
    print(f"  filename: {audio_file.filename}")
    print(f"  file_path: {audio_file.file_path}")
    
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

# # Simple in-memory cache for preview images (in production, use Redis)
# preview_cache: Dict[str, Dict] = {}
