# main.py - FastAPI Naver Blog Automation Server
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import json
import structlog
from datetime import datetime

# Task queue imports
from celery_app import celery_app, naver_blog_posting_task

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

app = FastAPI(
    title="Naver Blog Automation Server",
    description="Cloud-based Naver blog posting automation service",
    version="1.0.0"
)

# CORS middleware for Next.js app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://navely.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class NaverAccount(BaseModel):
    id: str
    password: str

class PostData(BaseModel):
    title: str
    content: str
    category: Optional[str] = None
    tags: Optional[str] = None

class BlogPostRequest(BaseModel):
    postData: PostData
    naverAccount: NaverAccount

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[Any, Any]] = None
    error: Optional[str] = None
    progress: Optional[int] = None

# In-memory task storage (replace with Redis in production)
task_storage: Dict[str, Dict] = {}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Naver Blog Automation Server",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check Celery worker status
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        return {
            "status": "healthy",
            "celery_workers": len(active_workers) if active_workers else 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/api/blog/post", response_model=TaskResponse)
async def create_blog_post(request: BlogPostRequest):
    """
    Start a new blog posting task
    """
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Log the request (without sensitive data)
        logger.info(
            "New blog post request",
            task_id=task_id,
            title=request.postData.title,
            content_length=len(request.postData.content),
            naver_account=request.naverAccount.id
        )
        
        # Submit task to Celery
        celery_task = naver_blog_posting_task.delay(
            task_id=task_id,
            post_data=request.postData.dict(),
            naver_account=request.naverAccount.dict()
        )
        
        # Store task info
        task_storage[task_id] = {
            "celery_task_id": celery_task.id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "post_title": request.postData.title
        }
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message="블로그 포스팅 작업이 시작되었습니다."
        )
        
    except Exception as e:
        logger.error("Failed to create blog post task", error=str(e))
        raise HTTPException(status_code=500, detail=f"작업 생성 실패: {str(e)}")

@app.get("/api/blog/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get status of a specific task
    """
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    try:
        task_info = task_storage[task_id]
        celery_task_id = task_info["celery_task_id"]
        
        # Get task result from Celery
        celery_task = celery_app.AsyncResult(celery_task_id)
        
        # Update task status
        if celery_task.state == "PENDING":
            status = "pending"
            result = None
            error = None
            progress = 0
        elif celery_task.state == "PROGRESS":
            status = "in_progress"
            result = celery_task.result
            error = None
            progress = result.get("progress", 0) if result else 0
        elif celery_task.state == "SUCCESS":
            status = "completed"
            result = celery_task.result
            error = None
            progress = 100
        elif celery_task.state == "FAILURE":
            status = "failed"
            result = None
            error = str(celery_task.result)
            progress = 0
        else:
            status = celery_task.state.lower()
            result = celery_task.result if hasattr(celery_task, 'result') else None
            error = None
            progress = 0
        
        # Update stored task info
        task_storage[task_id]["status"] = status
        
        return TaskStatusResponse(
            task_id=task_id,
            status=status,
            result=result,
            error=error,
            progress=progress
        )
        
    except Exception as e:
        logger.error("Failed to get task status", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"작업 상태 조회 실패: {str(e)}")

@app.delete("/api/blog/task/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a running task
    """
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    try:
        task_info = task_storage[task_id]
        celery_task_id = task_info["celery_task_id"]
        
        # Revoke the Celery task
        celery_app.control.revoke(celery_task_id, terminate=True)
        
        # Update task status
        task_storage[task_id]["status"] = "cancelled"
        
        logger.info("Task cancelled", task_id=task_id)
        
        return {"message": "작업이 취소되었습니다.", "task_id": task_id}
        
    except Exception as e:
        logger.error("Failed to cancel task", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"작업 취소 실패: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )