from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from .models import MethodEnum, StatusEnum, RunStatusEnum

class TargetBase(BaseModel):
    name: str
    url: str
    method: MethodEnum = MethodEnum.GET
    headers: Dict[str, str] = {}
    body: Optional[str] = None

class TargetCreate(TargetBase):
    pass

class Target(TargetBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ScheduleBase(BaseModel):
    name: str
    target_id: int
    type: str # "interval" or "cron"
    value: str
    duration_seconds: Optional[int] = None

class ScheduleCreate(ScheduleBase):
    pass

class Schedule(ScheduleBase):
    id: int
    status: StatusEnum
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class RunBase(BaseModel):
    schedule_id: int
    status: RunStatusEnum
    started_at: datetime
    completed_at: Optional[datetime] = None
    latency_ms: Optional[float] = None

class Run(RunBase):
    id: int

    class Config:
        from_attributes = True

class AttemptBase(BaseModel):
    run_id: int
    status_code: Optional[int] = None
    error: Optional[str] = None
    response_body: Optional[str] = None
    timestamp: datetime

class Attempt(AttemptBase):
    id: int

    class Config:
        from_attributes = True

class MetricAggregate(BaseModel):
    total_runs: int
    success_rate: float
    avg_latency_ms: float
    status_codes: Dict[int, int]
