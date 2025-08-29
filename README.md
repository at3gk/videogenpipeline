# YouTube Music Channel Automation Platform

A comprehensive automation platform that enables content creators to generate YouTube music videos by uploading audio files, generating AI-powered visual content, and automatically creating publish-ready videos with integrated YouTube API support.

## 🚀 Features

- **FastAPI-based web dashboard** with file upload capabilities
- **Docker containerized microservices** architecture
- **AI image generation** (DALL-E/Midjourney integration with mock services for development)
- **Automated video composition** and rendering using MoviePy
- **YouTube API integration** for direct publishing (mock implementation for development)
- **Review and approval workflow**
- **Mock testing environment** for development without API keys

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Dashboard │────│   FastAPI Core   │────│  Docker Services│
│   (React)       │    │   (Backend)      │    │   (Processing)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
            ┌───────▼───┐ ┌───▼───┐ ┌───▼────┐
            │ Database  │ │ Redis │ │ File   │
            │(PostgreSQL)│ │(Queue)│ │Storage │
            └───────────┘ └───────┘ └────────┘
```

## 🛠️ Technology Stack

### Backend Services
- **API Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 15+
- **Caching/Queue**: Redis 7+
- **Task Queue**: Celery 5+
- **File Storage**: Local file system (with MinIO support)

### AI Services
- **Image Generation**: 
  - Primary: OpenAI DALL-E 3 API (mock)
  - Secondary: Midjourney API (mock)
  - Fallback: Stable Diffusion (mock local)

### Video Processing
- **Video Composition**: FFmpeg 6+
- **Python Libraries**: 
  - `moviepy` for video editing
  - `Pillow` for image processing
  - `librosa` for audio analysis

### Frontend
- **Framework**: React 18+ with TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **File Upload**: React Dropzone
- **Notifications**: React Hot Toast

## 📋 Prerequisites

- Docker 24+ and Docker Compose
- Python 3.11+
- Node.js 18+
- Git

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd VideoGenPipeline

# Copy environment template
cp env.example .env

# Create necessary directories
mkdir -p uploads shared
```

### 2. Start Development Environment

```bash
# Start all services
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 30

# Verify database connection
docker-compose exec db pg_isready -U postgres -d youtube_music

# Verify Redis connection
docker-compose exec redis redis-cli -a redispass123 ping
```

### 3. Access the Platform

| Service | URL | Credentials |
|---------|-----|-------------|
| **Main Application** | http://localhost | - |
| **API Documentation** | http://localhost:8000/docs | - |
| **Database Admin (pgAdmin)** | http://localhost:5050 | admin@youtubemusic.local / admin123 |
| **Redis Admin (RedisInsight)** | http://localhost:8001 | - |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin123 |

## 🔧 Development Setup

### Backend Development

```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt

# Run FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
# Install Node.js dependencies
cd frontend
npm install

# Run React development server
npm start
```

### Database Management

```bash
# Connect to PostgreSQL directly
docker-compose exec db psql -U postgres -d youtube_music

# Run SQL queries
youtube_music=# SELECT * FROM projects;
youtube_music=# \dt  # List all tables
```

## 📱 Usage

### 1. Create a Project
- Navigate to the main dashboard
- Enter a project name and click "Create Project"

### 2. Upload Audio
- Select your project
- Drag and drop an audio file (MP3, WAV, M4A, FLAC)
- Wait for upload completion

### 3. Generate AI Images
- Enter a descriptive prompt
- Choose AI service (DALL-E, Midjourney, Stable Diffusion)
- Click "Generate Image"

### 4. Compose Video
- Configure video settings (resolution, FPS, transitions)
- Click "Compose Video" to start processing

### 5. Review & Download
- Preview the generated video
- Download in your preferred quality
- Publish directly to YouTube (when configured)

## 🔒 Mock Services

The platform includes mock implementations for all AI services, allowing full development and testing without API keys:

- **Mock DALL-E**: Returns random placeholder images
- **Mock Midjourney**: Simulates longer processing times
- **Mock Stable Diffusion**: Generates simple text-based images
- **Mock YouTube**: Simulates video uploads

## 🧪 Testing

### API Testing
```bash
# Test health endpoint
curl http://localhost:8000/api/health

# Test project creation
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project"}'
```

### Load Testing
```bash
# Test concurrent uploads
python load_test.py
```

## 🚀 Production Deployment

### 1. Environment Configuration
```bash
# Set production environment variables
USE_MOCK_SERVICES=false
OPENAI_API_KEY=your-actual-key
YOUTUBE_CLIENT_ID=your-client-id
```

### 2. Docker Production
```bash
# Build production images
docker-compose -f docker-compose.prod.yml up -d --build
```

### 3. SSL Configuration
```bash
# Configure Nginx with SSL certificates
# Update nginx/nginx.conf for HTTPS
```

## 📊 Monitoring

### Health Checks
- **Application**: `/api/health`
- **Database**: Connection status
- **Redis**: Queue health
- **File Storage**: Upload directory access

### Logs
```bash
# View service logs
docker-compose logs api
docker-compose logs worker
docker-compose logs db
```

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check if PostgreSQL is running
   docker-compose ps db
   
   # Restart database service
   docker-compose restart db
   ```

2. **Redis Connection Failed**
   ```bash
   # Check Redis status
   docker-compose exec redis redis-cli -a redispass123 ping
   
   # Restart Redis service
   docker-compose restart redis
   ```

3. **File Upload Issues**
   ```bash
   # Check upload directory permissions
   ls -la uploads/
   
   # Ensure directory exists
   mkdir -p uploads
   ```

### Performance Issues

1. **Slow Video Processing**
   - Check Celery worker status
   - Monitor Redis queue
   - Verify FFmpeg installation

2. **Memory Issues**
   - Adjust Docker memory limits
   - Monitor container resource usage

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation at `/docs`
- Review the troubleshooting section

## 🔮 Future Enhancements

### Phase 2
- Advanced video editing capabilities
- Multiple AI image generation services
- Batch processing for multiple projects
- Analytics and performance tracking

### Phase 3
- AI-powered music analysis for image prompts
- Social media multi-platform publishing
- Advanced video effects and transitions
- Collaborative project sharing

---

**Note**: This is a development version with mock services. For production use, configure real API keys and adjust security settings accordingly.
