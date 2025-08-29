#!/bin/bash

echo "🚀 Setting up YouTube Music Channel Automation Platform..."

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads shared

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📋 Copying environment template..."
    cp env.example .env
    echo "✅ Environment file created. Please review and update .env with your settings."
else
    echo "✅ Environment file already exists."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

echo "🐳 Starting Docker services..."
docker-compose up -d

echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo "🔍 Checking service health..."

# Check database
if docker-compose exec db pg_isready -U postgres -d youtube_music > /dev/null 2>&1; then
    echo "✅ Database is ready"
else
    echo "❌ Database is not ready"
fi

# Check Redis
if docker-compose exec redis redis-cli -a redispass123 ping > /dev/null 2>&1; then
    echo "✅ Redis is ready"
else
    echo "❌ Redis is not ready"
fi

# Check MinIO
if curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo "✅ MinIO is ready"
else
    echo "❌ MinIO is not ready"
fi

echo ""
echo "🎉 Setup complete! Access your platform at:"
echo ""
echo "🌐 Main Application: http://localhost"
echo "📚 API Documentation: http://localhost:8000/docs"
echo "🗄️  Database Admin (pgAdmin): http://localhost:5050"
echo "   Email: admin@youtubemusic.com"
echo "   Password: admin123"
echo "🔴 Redis Admin (RedisInsight): http://localhost:8001"
echo "📦 MinIO Console: http://localhost:9001"
echo "   Username: minioadmin"
echo "   Password: minioadmin123"
echo ""
echo "📖 For more information, see README.md"
echo ""
echo "🚀 Happy creating!"
