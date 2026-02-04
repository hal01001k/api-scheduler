from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from datetime import datetime, timedelta
from .database import get_db, init_db, AsyncSessionLocal
from .models import Target, Schedule, Run, Attempt, StatusEnum, RunStatusEnum
from .schemas import TargetCreate, Target as TargetSchema, ScheduleCreate, Schedule as ScheduleSchema, Run as RunSchema, MetricAggregate
from .scheduler import start_scheduler, add_schedule_job, pause_schedule_job, resume_schedule_job, remove_schedule_job
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI(title="API Scheduler")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await init_db()
    await start_scheduler()
    
#     # Sync schedules from DB to scheduler
#     async with AsyncSessionLocal() as db:
#         result = await db.execute(select(Schedule).where(Schedule.status == StatusEnum.ACTIVE))
#         active_schedules = result.scalars().all()
#         for schedule in active_schedules:
#             add_schedule_job(schedule)

@app.get("/targets", response_model=List[TargetSchema])
async def get_targets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Target))
    return result.scalars().all()

@app.post("/targets", response_model=TargetSchema)
async def create_target(target: TargetCreate, db: AsyncSession = Depends(get_db)):
    db_target = Target(**target.dict())
    db.add(db_target)
    await db.commit()
    await db.refresh(db_target)
    return db_target

@app.get("/schedules", response_model=List[ScheduleSchema])
async def get_schedules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Schedule))
    return result.scalars().all()

@app.post("/schedules", response_model=ScheduleSchema)
async def create_schedule(schedule: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    # Check if target exists
    target = await db.get(Target, schedule.target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
        
    db_schedule = Schedule(**schedule.dict(), status=StatusEnum.ACTIVE)
    db.add(db_schedule)
    await db.commit()
    await db.refresh(db_schedule)
    
    add_schedule_job(db_schedule)
    return db_schedule

@app.post("/schedules/{schedule_id}/pause", response_model=ScheduleSchema)
async def pause_schedule(schedule_id: int, db: AsyncSession = Depends(get_db)):
    db_schedule = await db.get(Schedule, schedule_id)
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    db_schedule.status = StatusEnum.PAUSED
    await db.commit()
    pause_schedule_job(schedule_id)
    return db_schedule

@app.post("/schedules/{schedule_id}/resume", response_model=ScheduleSchema)
async def resume_schedule(schedule_id: int, db: AsyncSession = Depends(get_db)):
    db_schedule = await db.get(Schedule, schedule_id)
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    db_schedule.status = StatusEnum.ACTIVE
    await db.commit()
    
    # If not in scheduler, add it, otherwise resume
    resume_schedule_job(schedule_id)
    return db_schedule

@app.get("/runs", response_model=List[RunSchema])
async def get_runs(
    schedule_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(Run)
    if schedule_id:
        query = query.where(Run.schedule_id == schedule_id)
    query = query.order_by(Run.started_at.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@app.get("/runs/{run_id}")
async def get_run_details(run_id: int, db: AsyncSession = Depends(get_db)):
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    result = await db.execute(select(Attempt).where(Attempt.run_id == run_id))
    attempts = result.scalars().all()
    
    return {
        "run": run,
        "attempts": attempts
    }

@app.get("/metrics", response_model=MetricAggregate)
async def get_metrics(db: AsyncSession = Depends(get_db)):
    # Total runs
    result = await db.execute(select(Run))
    runs = result.scalars().all()
    
    total_runs = len(runs)
    if total_runs == 0:
        return MetricAggregate(
            total_runs=0,
            success_rate=0.0,
            avg_latency_ms=0.0,
            status_codes={}
        )
    
    successes = sum(1 for r in runs if r.status == RunStatusEnum.SUCCESS)
    avg_latency = sum(r.latency_ms or 0 for r in runs) / total_runs
    
    # Status codes from attempts
    result = await db.execute(select(Attempt.status_code))
    status_codes_list = result.scalars().all()
    status_codes_count = {}
    for code in status_codes_list:
        if code:
            status_codes_count[code] = status_codes_count.get(code, 0) + 1
            
    return MetricAggregate(
        total_runs=total_runs,
        success_rate=(successes / total_runs) * 100,
        avg_latency_ms=avg_latency,
        status_codes=status_codes_count
    )
