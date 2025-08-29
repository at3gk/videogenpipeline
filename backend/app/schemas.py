from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

# User schemas
class UserBase(BaseModel):
    email: str
    username: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

# Project schemas
class ProjectBase(BaseModel):
    name: str

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    status: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    user_id: UUID
    
    class Config:
        from_attributes = True

# Audio file schemas
class AudioFileBase(BaseModel):
    filename: str
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None

class AudioFileCreate(AudioFileBase):
    file_path: str

class AudioFileResponse(BaseModel):
    id: UUID
    project_id: UUID
    filename: str
    file_path: str  # Make this required, not optional
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_at: datetime
    
    class Config:
        from_attributes = True
# Image generation schemas
class ImagePrompt(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    service: str = Field(default="dalle", pattern="^(dalle|midjourney|stable_diffusion)$")
    size: Optional[str] = Field(default="1024x1024")
    quality: Optional[str] = Field(default="standard")

class GeneratedImageBase(BaseModel):
    prompt: str
    generator_service: str

class GeneratedImageCreate(GeneratedImageBase):
    image_url: Optional[str] = None
    file_path: Optional[str] = None
    generation_params: Optional[dict] = None

class GeneratedImageResponse(GeneratedImageBase):
    id: UUID
    project_id: UUID
    image_url: Optional[str] = None
    file_path: Optional[str] = None
    generation_params: Optional[dict] = None
    generated_at: datetime
    status: Optional[str] = "approved"  # Add this line
    
    class Config:
        from_attributes = True

class TaskStartedResponse(BaseModel):
    message: str
    task_id: str
    job_id: str

class ImagePreviewResponse(BaseModel):
    task_id: str
    preview_url: str
    prompt: str
    service: str
    status: str = "preview"

class ImageApprovalRequest(BaseModel):
    preview_id: str

# Video composition schemas
class VideoCompositionSettings(BaseModel):
    resolution: str = Field(default="1920x1080")
    fps: int = Field(default=30, ge=1, le=60)
    transition_duration: float = Field(default=1.0, ge=0.1, le=5.0)
    add_audio_visualization: bool = Field(default=True)

class VideoOutputBase(BaseModel):
    file_path: str
    duration_seconds: Optional[float] = None
    resolution: Optional[str] = None
    file_size_bytes: Optional[int] = None

class VideoOutputCreate(VideoOutputBase):
    pass

class VideoOutputResponse(VideoOutputBase):
    id: UUID
    project_id: UUID
    status: str
    youtube_video_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Processing job schemas
class ProcessingJobBase(BaseModel):
    job_type: str
    status: str = "pending"
    progress: int = Field(default=0, ge=0, le=100)

class ProcessingJobCreate(ProcessingJobBase):
    pass

class ProcessingJobResponse(ProcessingJobBase):
    id: UUID
    project_id: UUID
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# YouTube publishing schemas
class YouTubePublishSettings(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default="", max_length=5000)
    tags: Optional[List[str]] = Field(default=[])
    privacy_status: str = Field(default="private", pattern="^(private|unlisted|public)$")
    category_id: str = Field(default="10")  # Music category

# Health check schema
class HealthCheck(BaseModel):
    status: str
    checks: dict
