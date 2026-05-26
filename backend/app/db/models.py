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

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    status = Column(String, default="active")
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    session_summary = Column(JSONB, nullable=True)          # ← new

    candidate = relationship("Candidate", back_populates="sessions")
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