import redis
import json
from typing import Dict, Optional
from datetime import datetime, timedelta
from ..config import settings

class PreviewCache:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.prefix = "preview_image:"
        self.ttl = 3600  # 1 hour TTL for preview images
    
    def set(self, preview_id: str, data: Dict) -> None:
        """Store preview data with TTL"""
        key = f"{self.prefix}{preview_id}"
        self.redis_client.setex(
            key, 
            self.ttl, 
            json.dumps(data, default=str)
        )
    
    def get(self, preview_id: str) -> Optional[Dict]:
        """Get preview data"""
        key = f"{self.prefix}{preview_id}"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None
    
    def delete(self, preview_id: str) -> None:
        """Delete preview data"""
        key = f"{self.prefix}{preview_id}"
        self.redis_client.delete(key)
    
    def exists(self, preview_id: str) -> bool:
        """Check if preview exists"""
        key = f"{self.prefix}{preview_id}"
        return self.redis_client.exists(key) > 0

# Global instance
preview_cache = PreviewCache()