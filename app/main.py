"""
Executor Balancer - Main Application Module
Упрощенная система распределения заявок между исполнителями
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
import os

from core.config import settings
from core.database import init_database, init_redis, cleanup
from api.routes import router
from utils.helpers import create_sample_executors, create_sample_requests, create_sample_rules

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Executor Balancer...")
    
    try:
        # Initialize database
        await init_database(settings.DATABASE_URL)
        logger.info("Database initialized")
        
        # Initialize Redis
        await init_redis(settings.REDIS_URL)
        logger.info("Redis initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Fallback to in-memory mode
        logger.warning("Falling back to in-memory mode")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Executor Balancer...")
    await cleanup()

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Система распределения заявок между исполнителями с метриками и аналитикой",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)

# Mount static files
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Include API routes
app.include_router(router)

# Initialize sample data if enabled
if settings.LOAD_SAMPLE_DATA:
    logger.info("Loading sample data...")
    
    # Import the database lists from routes
    from api.routes import executors_db, requests_db, rules_db
    
    # Add sample data
    sample_executors = create_sample_executors()
    sample_requests = create_sample_requests()
    sample_rules = create_sample_rules()
    
    executors_db.extend(sample_executors)
    requests_db.extend(sample_requests)
    rules_db.extend(sample_rules)
    
    logger.info(f"Loaded {len(sample_executors)} executors, {len(sample_requests)} requests, {len(sample_rules)} rules")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "app": "/app"
    }

if __name__ == "__main__":
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Server: {settings.HOST}:{settings.PORT}")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        workers=1
    )
