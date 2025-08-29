from sqlalchemy import Column, String, DateTime, Text, Integer, DECIMAL, BigInteger, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import uuid

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    projects = relationship("Project", back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    status = Column(String, default='draft')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    user = relationship("User", back_populates="projects")
    audio_files = relationship("AudioFile", back_populates="project", cascade="all, delete-orphan")
    generated_images = relationship("GeneratedImage", back_populates="project", cascade="all, delete-orphan")
    video_outputs = relationship("VideoOutput", back_populates="project", cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="project", cascade="all, delete-orphan")

class AudioFile(Base):
    __tablename__ = "audio_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(Text, nullable=False)
    duration_seconds = Column(DECIMAL(10, 2))
    file_size_bytes = Column(BigInteger)
    mime_type = Column(String(100))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="audio_files")

class GeneratedImage(Base):
    __tablename__ = "generated_images"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    prompt = Column(Text, nullable=False)
    image_url = Column(Text)
    file_path = Column(Text)
    generator_service = Column(String(50))
    generation_params = Column(JSON)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="generated_images")

class VideoOutput(Base):
    __tablename__ = "video_outputs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    file_path = Column(Text, nullable=False)
    duration_seconds = Column(DECIMAL(10, 2))
    resolution = Column(String(20))
    file_size_bytes = Column(BigInteger)
    status = Column(String(50), default='processing')
    youtube_video_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="video_outputs")

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    job_type = Column(String(50), nullable=False)
    status = Column(String(50), default='pending')
    progress = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="processing_jobs")
