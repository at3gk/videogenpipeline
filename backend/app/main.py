from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import urllib.parse

from .database import engine, Base
from .api import projects, health
from .config import settings

# Create database tables with retry logic
def create_tables():
    import time
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            print("Database tables created successfully")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Database connection failed (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Failed to create database tables after {max_retries} attempts: {e}")
                raise e

# Try to create tables
create_tables()

# Create FastAPI app
app = FastAPI(
    title="YouTube Music Channel Automation Platform",
    description="A comprehensive automation platform for generating YouTube music videos",
    version="1.0.0"
)

# Add CORS middleware with specific headers for audio files
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length", "Content-Type"]
)

# Include API routers
app.include_router(projects.router, prefix="/api")
app.include_router(health.router, prefix="/api")

# Custom static file handler with proper headers for audio
@app.get("/uploads/{filename}")
async def serve_upload_file(filename: str):
    """Serve uploaded files with proper headers for audio playback"""
    # Decode URL-encoded filename
    decoded_filename = urllib.parse.unquote(filename)
    print(f"DEBUG: Original filename: {filename}")
    print(f"DEBUG: Decoded filename: {decoded_filename}")
    
    # Try both the original and decoded filename
    possible_paths = [
        os.path.join("uploads", filename),
        os.path.join("uploads", decoded_filename)
    ]
    
    file_path = None
    for path in possible_paths:
        print(f"DEBUG: Checking path: {path}")
        if os.path.exists(path):
            file_path = path
            print(f"DEBUG: Found file at: {file_path}")
            break
    
    if not file_path:
        # List all files in uploads directory for debugging
        if os.path.exists("uploads"):
            available_files = os.listdir("uploads")
            print(f"DEBUG: Available files in uploads: {available_files}")
        raise HTTPException(status_code=404, detail=f"File not found: {filename} (decoded: {decoded_filename})")
    
    # Determine media type based on file extension
    file_ext = os.path.splitext(decoded_filename)[1].lower()
    media_type_mapping = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.flac': 'audio/flac',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif'
    }
    
    media_type = media_type_mapping.get(file_ext, 'application/octet-stream')
    print(f"DEBUG: Serving file with media_type: {media_type}")
    
    return FileResponse(
        file_path, 
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Type"
        }
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "YouTube Music Channel Automation Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }

@app.get("/api")
async def api_info():
    """API information"""
    return {
        "name": "YouTube Music Channel Automation Platform API",
        "version": "1.0.0",
        "endpoints": {
            "projects": "/api/projects",
            "health": "/api/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)