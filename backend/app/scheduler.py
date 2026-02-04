import asyncio
import httpx
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy.future import select
from .database import AsyncSessionLocal, engine
from .models import Schedule, Run, Attempt, Target, StatusEnum, RunStatusEnum
import time

scheduler = AsyncIOScheduler() # Default is MemoryJobStore

async def execute_request(schedule_id: int):
    async with AsyncSessionLocal() as db:
        # Fetch schedule and target
        result = await db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule or schedule.status != StatusEnum.ACTIVE:
            return

        result = await db.execute(
            select(Target).where(Target.id == schedule.target_id)
        )
        target = result.scalar_one_or_none()
        if not target:
            return

        # Create Run record
        run = Run(schedule_id=schedule_id, status=RunStatusEnum.RUNNING, started_at=datetime.utcnow())
        db.add(run)
        await db.commit()
        await db.refresh(run)

        start_time = time.time()
        status_code = None
        error_msg = None
        response_text = None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=target.method,
                    url=target.url,
                    headers=target.headers,
                    content=target.body
                )
                status_code = response.status_code
                response_text = response.text[:1000] # Cap size
        except Exception as e:
            error_msg = str(e)

        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        # Create Attempt record
        attempt = Attempt(
            run_id=run.id,
            status_code=status_code,
            error=error_msg,
            response_body=response_text,
            timestamp=datetime.utcnow()
        )
        db.add(attempt)

        # Update Run record
        run.status = RunStatusEnum.SUCCESS if status_code and status_code < 400 else RunStatusEnum.FAILURE
        run.completed_at = datetime.utcnow()
        run.latency_ms = latency_ms
        
        # Update Schedule last_run_at
        schedule.last_run_at = run.started_at
        
        await db.commit()

async def start_scheduler():
    if not scheduler.running:
        scheduler.start()

def add_schedule_job(schedule: Schedule):
    kwargs = {'schedule_id': schedule.id}
    if schedule.type == "interval":
        scheduler.add_job(
            execute_request,
            'interval',
            seconds=int(schedule.value),
            id=str(schedule.id),
            replace_existing=True,
            kwargs=kwargs
        )
    elif schedule.type == "cron":
        scheduler.add_job(
            execute_request,
            'cron',
            cron_expression=schedule.value, # This might need parsing depending on how user inputs it
            id=str(schedule.id),
            replace_existing=True,
            kwargs=kwargs
        )

def pause_schedule_job(schedule_id: int):
    try:
        scheduler.pause_job(str(schedule_id))
    except:
        pass

def resume_schedule_job(schedule_id: int):
    try:
        scheduler.resume_job(str(schedule_id))
    except:
        pass

def remove_schedule_job(schedule_id: int):
    try:
        scheduler.remove_job(str(schedule_id))
    except:
        pass
