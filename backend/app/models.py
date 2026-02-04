from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class MethodEnum(str, enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

class StatusEnum(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

class RunStatusEnum(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"

class Target(Base):
    __tablename__ = "targets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    url = Column(String)
    method = Column(String, default="GET")
    headers = Column(JSON, default={})
    body = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    schedules = relationship("Schedule", back_populates="target")

class Schedule(Base):
    __tablename__ = "schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey("targets.id"))
    name = Column(String, index=True)
    type = Column(String)  # "interval" or "cron"
    value = Column(String)  # seconds for interval or cron expression
    duration_seconds = Column(Integer, nullable=True) # For windowed runs
    status = Column(Enum(StatusEnum), default=StatusEnum.ACTIVE)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    target = relationship("Target", back_populates="schedules")
    runs = relationship("Run", back_populates="schedule")

class Run(Base):
    __tablename__ = "runs"
    
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"))
    status = Column(Enum(RunStatusEnum))
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    latency_ms = Column(Float, nullable=True)
    
    schedule = relationship("Schedule", back_populates="runs")
    attempts = relationship("Attempt", back_populates="run")

class Attempt(Base):
    __tablename__ = "attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"))
    status_code = Column(Integer, nullable=True)
    error = Column(String, nullable=True)
    response_body = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    run = relationship("Run", back_populates="attempts")
