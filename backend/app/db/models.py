from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .database import Base
import uuid
import datetime
from sqlalchemy.dialects.postgresql import JSONB

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
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True)
    zoom_meeting_id = Column(String, nullable=True, index=True)
    status = Column(String, default="active")
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    session_summary = Column(JSONB, nullable=True)

    candidate = relationship("Candidate", back_populates="sessions")
    job = relationship("Job", back_populates="sessions")
    emotion_frames = relationship("EmotionFrame", back_populates="session")
    transcript_chunks = relationship("TranscriptChunk", back_populates="session")
    suggested_questions = relationship("SuggestedQuestion", back_populates="session")


class EmotionFrame(Base):
    __tablename__ = "emotion_frames"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    dominant_emotion = Column(String)
    confidence = Column(Float)
    session = relationship("Session", back_populates="emotion_frames")  


class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    text = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    session = relationship("Session", back_populates="transcript_chunks")  


class SuggestedQuestion(Base):
    __tablename__ = "suggested_questions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    question_text = Column(Text)
    triggered_by = Column(Text)
    was_asked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    session = relationship("Session", back_populates="suggested_questions")  


class Recruiter(Base):
    __tablename__ = "recruiters"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ── Phase 2: Attention tracking ──────────────────────────────────────────────

class AttentionEvent(Base):
    __tablename__ = "attention_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    direction = Column(String)       # center, left, right, up, down, missing
    confidence = Column(Float)
    yaw = Column(Float, nullable=True)
    pitch = Column(Float, nullable=True)
    session = relationship("Session", backref="attention_events")


# ── Phase 3: Integrity events ────────────────────────────────────────────────

class IntegrityEvent(Base):
    __tablename__ = "integrity_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    event_type = Column(String)      # multi_face, liveness_fail, voice_anomaly
    severity = Column(String)        # info, warning, critical
    details = Column(JSONB, nullable=True)
    session = relationship("Session", backref="integrity_events")