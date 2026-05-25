from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .database import Base
import uuid
import datetime

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    sessions = relationship("Session", back_populates="candidate")

class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    raw_description = Column(Text)
    extracted_skills = Column(JSON)
    seniority_level = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    sessions = relationship("Session", back_populates="job")

class Session(Base):
    __tablename__ = "sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"))
    status = Column(String, default="pending")
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    candidate = relationship("Candidate", back_populates="sessions")
    zoom_meeting_id = Column(String, nullable=True, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    job = relationship("Job", back_populates="sessions")


class EmotionFrame(Base):
    __tablename__ = "emotion_frames"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    dominant_emotion = Column(String)
    confidence = Column(Float)

class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    text = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class SuggestedQuestion(Base):
    __tablename__ = "suggested_questions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    question_text = Column(Text)
    triggered_by = Column(Text)
    was_asked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)