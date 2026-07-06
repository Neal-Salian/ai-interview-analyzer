from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .database import Base
import uuid
import datetime
import enum
from sqlalchemy import Enum as SQLEnum


class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recruiter_id = Column(UUID(as_uuid=True), ForeignKey("recruiters.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, default="Draft")
    resume_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    recruiter = relationship("Recruiter", foreign_keys=[recruiter_id])
    sessions = relationship("Session", back_populates="candidate")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recruiter_id = Column(UUID(as_uuid=True), ForeignKey("recruiters.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String, nullable=False)
    raw_description = Column(Text)
    extracted_skills = Column(JSON)
    seniority_level = Column(String)
    interview_type = Column(String, nullable=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    recruiter = relationship("Recruiter", foreign_keys=[recruiter_id])
    sessions = relationship("Session", back_populates="job")


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    RECRUITER = "RECRUITER"


class Recruiter(Base):
    __tablename__ = "recruiters"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.RECRUITER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    reset_token = Column(String, nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)
    sessions = relationship("Session", back_populates="recruiter")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    zoom_token = relationship("RecruiterZoomToken", back_populates="recruiter", uselist=False, cascade="all, delete-orphan")

class RecruiterZoomToken(Base):
    __tablename__ = "recruiter_zoom_tokens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recruiter_id = Column(UUID(as_uuid=True), ForeignKey("recruiters.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    encrypted_access_token = Column(String, nullable=False)
    encrypted_refresh_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    zoom_user_id = Column(String, unique=True, index=True, nullable=False)
    zoom_email = Column(String, nullable=True)
    token_scope = Column(String, nullable=True)
    connected_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_refresh_at = Column(DateTime, nullable=True)

    recruiter = relationship("Recruiter", back_populates="zoom_token")



class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("recruiters.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    revoked = Column(Boolean, default=False)
    
    user = relationship("Recruiter", back_populates="refresh_tokens")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("recruiters.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    target_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    metadata_info = Column(JSONB, nullable=True)

    user = relationship("Recruiter", back_populates="audit_logs")


class Session(Base):
    __tablename__ = "sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True)
    recruiter_id = Column(UUID(as_uuid=True), ForeignKey("recruiters.id", ondelete="SET NULL"), nullable=True)
    zoom_meeting_id = Column(String, nullable=True, index=True)
    meeting_provider = Column(String, nullable=True, default="zoom")
    zoom_join_url = Column(String, nullable=True)
    zoom_start_url = Column(String, nullable=True)
    zoom_password = Column(String, nullable=True)
    status = Column(String, default="active")
    ai_runtime_status = Column(String, default="not_initialized")
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    session_summary = Column(JSONB, nullable=True)

    candidate = relationship("Candidate", back_populates="sessions")
    job = relationship("Job", back_populates="sessions")
    recruiter = relationship("Recruiter", back_populates="sessions")
    panel_members = relationship("PanelMember", back_populates="session", cascade="all, delete-orphan")
    emotion_frames = relationship("EmotionFrame", back_populates="session")
    transcript_chunks = relationship("TranscriptChunk", back_populates="session")
    suggested_questions = relationship("SuggestedQuestion", back_populates="session")


class PanelMember(Base):
    __tablename__ = "panel_members"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    role = Column(String, nullable=True)
    notify_invite = Column(Boolean, default=True)
    notify_report = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    session = relationship("Session", back_populates="panel_members")


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


class AttentionEvent(Base):
    __tablename__ = "attention_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    direction = Column(String)
    confidence = Column(Float)
    yaw = Column(Float, nullable=True)
    pitch = Column(Float, nullable=True)
    session = relationship("Session", backref="attention_events")


class IntegrityEvent(Base):
    __tablename__ = "integrity_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    event_type = Column(String)
    severity = Column(String)
    details = Column(JSONB, nullable=True)
    session = relationship("Session", backref="integrity_events")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), index=True)
    category = Column(String, index=True)  # e.g., 'technical', 'communication', 'domain_knowledge'
    rule_score = Column(Float, nullable=True)
    llm_score = Column(Float, nullable=True)
    combined_score = Column(Float, nullable=True)
    strengths = Column(JSONB, nullable=True)  # list of strings
    improvement_areas = Column(JSONB, nullable=True)  # list of strings
    overall_assessment = Column(Text, nullable=True)
    correct_concepts = Column(JSONB, nullable=True)  # list of strings
    missing_concepts = Column(JSONB, nullable=True)  # list of strings
    potential_inaccuracies = Column(JSONB, nullable=True)  # list of strings
    confidence_level = Column(String, nullable=True)  # High, Medium, Low
    evidence = Column(JSONB, nullable=True)  # list of transcript quotes
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    session = relationship("Session", backref="evaluation_results")


class EvaluationFeedback(Base):
    __tablename__ = "evaluation_feedbacks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), index=True)
    recruiter_id = Column(UUID(as_uuid=True), ForeignKey("recruiters.id"), nullable=True)
    evaluation_category = Column(String, index=True)
    decision = Column(String)  # 'Agree', 'Disagree'
    correction_notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    session = relationship("Session", backref="evaluation_feedbacks")