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
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"audio_{uuid.uuid4().hex[:8]}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Create audio file record
    audio_file = AudioFile(
        project_id=project_id,
        filename=file.filename,
        file_path=file_path,
        file_size_bytes=file.size,
        mime_type=file.content_type
    )
    
    db.add(audio_file)
    db.commit()
    db.refresh(audio_file)
    
    return audio_file

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
        # Generate preview image using your existing service
        from ..services.mock_services import get_ai_service
        ai_service = get_ai_service(prompt.service)
        
        # Create a temporary preview record (not saved to GeneratedImage table yet)
        task_id = str(uuid.uuid4())
        
        if prompt.service == "stable_diffusion":
            # For SD, generate and save to temporary location
            temp_image_path = ai_service.generate_image(prompt.prompt)
            preview_url = f"/uploads/preview_{task_id}.png"
            
            # Move to preview location
            import shutil
            preview_path = f"uploads/preview_{task_id}.png"
            shutil.copy(temp_image_path, preview_path)
            
        else:
            # For other services, get URL directly
            preview_url = ai_service.generate_image(prompt.prompt)
        
        # Store preview info temporarily (you might want to use Redis for this)
        # For now, we'll use a simple in-memory cache
        preview_cache.set(task_id, {
            "project_id": str(project_id),
            "prompt": prompt.prompt,
            "service": prompt.service,
            "preview_url": preview_url,
            "created_at": datetime.utcnow().isoformat()
        })
        
        return ImagePreviewResponse(
            task_id=task_id,
            preview_url=preview_url,
            prompt=prompt.prompt,
            service=prompt.service
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Image generation service temporarily unavailable: {str(e)}"
        )

@router.post("/{project_id}/approve-image", response_model=GeneratedImageResponse)
async def approve_image(
    project_id: UUID,
    preview_id: str,
    db: Session = Depends(get_db)
):
    """Approve a preview image and save it to the project"""
    # Validate project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get preview data from cache
    if preview_id not in preview_cache:
        raise HTTPException(status_code=404, detail="Preview image not found")
    
    preview_data = preview_cache.get([preview_id])
    if not preview_data:
        raise HTTPException(status_code=404, detail="Preview image not found")
    
    # Move from preview to permanent storage if it's a local file
    preview_url = preview_data["preview_url"]
    final_path = None
    final_url = None
    
    if preview_url.startswith("/uploads/preview_"):
        # It's a local file, move it to permanent location
        preview_file_path = preview_url[1:]  # Remove leading /
        final_filename = f"approved_{uuid.uuid4().hex[:8]}.png"
        final_path = f"uploads/{final_filename}"
        
        # Move file
        import shutil
        shutil.move(preview_file_path, final_path)
        final_url = f"/uploads/{final_filename}"
    else:
        # It's an external URL, keep as is
        final_url = preview_url
    
    # Create the approved image record
    generated_image = GeneratedImage(
        project_id=project_id,
        prompt=preview_data["prompt"],
        image_url=final_url,
        file_path=final_path,
        generator_service=preview_data["service"],
        generation_params={
            "prompt": preview_data["prompt"], 
            "service": preview_data["service"],
            "approved_from_preview": True
        },
        status="approved"  # Add this field to your model
    )
    
    db.add(generated_image)
    db.commit()
    db.refresh(generated_image)
    
    # Remove from preview cache
    preview_cache.delete([preview_id])
    
    return generated_image

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
