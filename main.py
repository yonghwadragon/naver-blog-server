# main.py - FastAPI Naver Blog Automation Server
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import json
import structlog
from datetime import datetime
import asyncio

# Direct import of BlogPoster for immediate execution
from blog_poster import BlogPoster

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

# In-memory task storage for tracking
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
    return {
        "status": "healthy",
        "execution_mode": "immediate",
        "timestamp": datetime.now().isoformat()
    }

async def execute_blog_posting_task(task_id: str, post_data: dict, naver_account: dict):
    """
    Execute blog posting task immediately in background
    """
    try:
        # Update task status to in_progress
        task_storage[task_id]["status"] = "in_progress"
        task_storage[task_id]["progress"] = 10
        
        # Create BlogPoster instance and execute
        blog_poster = BlogPoster()
        
        # Execute blog posting
        result = await asyncio.to_thread(
            blog_poster.post_to_naver_blog,
            post_data,
            naver_account
        )
        
        # Update task status to completed
        task_storage[task_id]["status"] = "completed"
        task_storage[task_id]["progress"] = 100
        task_storage[task_id]["result"] = result
        
        logger.info("Blog posting completed successfully", task_id=task_id)
        
    except Exception as e:
        # Update task status to failed
        task_storage[task_id]["status"] = "failed"
        task_storage[task_id]["error"] = str(e)
        task_storage[task_id]["progress"] = 0
        
        logger.error("Blog posting failed", task_id=task_id, error=str(e))

@app.post("/api/blog/post", response_model=TaskResponse)
async def create_blog_post(request: BlogPostRequest, background_tasks: BackgroundTasks):
    """
    Start a new blog posting task with immediate execution
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
        
        # Store initial task info
        task_storage[task_id] = {
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "post_title": request.postData.title,
            "progress": 0
        }
        
        # Execute task in background
        background_tasks.add_task(
            execute_blog_posting_task,
            task_id,
            request.postData.dict(),
            request.naverAccount.dict()
        )
        
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
        
        return TaskStatusResponse(
            task_id=task_id,
            status=task_info.get("status", "pending"),
            result=task_info.get("result"),
            error=task_info.get("error"),
            progress=task_info.get("progress", 0)
        )
        
    except Exception as e:
        logger.error("Failed to get task status", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"작업 상태 조회 실패: {str(e)}")

@app.delete("/api/blog/task/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a running task (limited support for immediate execution)
    """
    if task_id not in task_storage:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    try:
        # Update task status to cancelled
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