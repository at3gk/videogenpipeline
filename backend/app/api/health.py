from fastapi import APIRouter
from ..schemas import HealthCheck
import psycopg2
import redis
import os

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/", response_model=HealthCheck)
async def health_check():
    """Application health check"""
    checks = {}
    
    # Database check
    try:
        from ..database import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        checks["database"] = False
        print(f"Database health check failed: {e}")
    
    # Redis check
    try:
        from ..config import settings
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        checks["redis"] = True
    except Exception as e:
        checks["redis"] = False
    
    # File storage check
    try:
        upload_dir = "./uploads"
        os.makedirs(upload_dir, exist_ok=True)
        test_file = os.path.join(upload_dir, "health_check.txt")
        with open(test_file, "w") as f:
            f.write("health check")
        os.remove(test_file)
        checks["file_storage"] = True
    except Exception as e:
        checks["file_storage"] = False
    
    # AI services check (mock services are always available)
    checks["ai_services"] = True
    
    # Celery worker check
    try:
        from ..celery_app import celery_app
        # Try to get active workers
        active_workers = celery_app.control.inspect().active()
        checks["celery_worker"] = active_workers is not None and len(active_workers) > 0
    except Exception as e:
        checks["celery_worker"] = False
        print(f"Celery worker check failed: {e}")
    
    status = "healthy" if all(checks.values()) else "unhealthy"
    
    return HealthCheck(status=status, checks=checks)
