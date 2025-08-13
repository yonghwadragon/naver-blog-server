# celery_app.py - Celery configuration and tasks
from celery import Celery
import os
import sys
import time
import json
import structlog
from datetime import datetime

# Configure logging
logger = structlog.get_logger()

# Create Celery app
celery_app = Celery(
    "naver_blog_automation",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=["celery_app"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_track_started=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
)

@celery_app.task(bind=True)
def naver_blog_posting_task(self, task_id: str, post_data: dict, naver_account: dict):
    """
    Celery task for Naver blog posting automation
    """
    try:
        logger.info("Starting blog posting task", task_id=task_id)
        
        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": 10,
                "status": "브라우저 초기화 중...",
                "task_id": task_id
            }
        )
        
        # Import and run the actual blog posting logic
        from naver_blog_automation import BlogPoster
        
        poster = BlogPoster(
            naver_id=naver_account["id"],
            naver_password=naver_account["password"],
            task_id=task_id,
            progress_callback=lambda p, s: self.update_state(
                state="PROGRESS",
                meta={"progress": p, "status": s, "task_id": task_id}
            )
        )
        
        # Execute the posting
        result = poster.post_blog(
            title=post_data["title"],
            content=post_data["content"],
            category=post_data.get("category"),
            tags=post_data.get("tags")
        )
        
        logger.info("Blog posting completed", task_id=task_id, result=result)
        
        return {
            "task_id": task_id,
            "status": "completed",
            "result": result,
            "completed_at": datetime.now().isoformat()
        }
        
    except Exception as exc:
        logger.error("Blog posting failed", task_id=task_id, error=str(exc))
        
        # Update task with failure
        self.update_state(
            state="FAILURE",
            meta={
                "task_id": task_id,
                "error": str(exc),
                "failed_at": datetime.now().isoformat()
            }
        )
        
        raise exc

if __name__ == "__main__":
    # Run Celery worker
    celery_app.start()