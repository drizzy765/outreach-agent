import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from .connection import Base

class ProspectCompany(Base):
    __tablename__ = "prospect_companies"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(255), nullable=False)
    website_url = Column(Text, unique=True, nullable=False, index=True)
    industry = Column(String(100), nullable=True)
    tech_stack_detected = Column(JSON, default=dict)
    audit_findings = Column(JSON, default=dict)
    discovered_at = Column(DateTime, default=datetime.utcnow)

    leads = relationship("ProspectLead", back_populates="company", cascade="all, delete-orphan")

class ProspectLead(Base):
    __tablename__ = "prospect_leads"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Uuid(as_uuid=True), ForeignKey("prospect_companies.id", ondelete="CASCADE"))
    full_name = Column(String(255), nullable=True)
    role = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    verification_status = Column(String(50), default="UNVERIFIED")
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("ProspectCompany", back_populates="leads")
    conversations = relationship("OutreachConversation", back_populates="lead", cascade="all, delete-orphan")

class OutreachConversation(Base):
    __tablename__ = "outreach_conversations"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(Uuid(as_uuid=True), ForeignKey("prospect_leads.id", ondelete="CASCADE"))
    pitch_type = Column(String(50), default="CUSTOM_ML_AUDIT")
    email_thread_id = Column(Text, nullable=True)
    stage = Column(String(50), default="DRAFTED", index=True)
    last_message_content = Column(Text, nullable=True)
    minimum_acceptable_rate = Column(Numeric, default=150.00)
    agreed_rate = Column(Numeric, nullable=True)
    human_override_required = Column(Boolean, default=False)
    override_reason = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead = relationship("ProspectLead", back_populates="conversations")
    send_logs = relationship("EmailSendLog", back_populates="conversation", cascade="all, delete-orphan")

class EmailSendLog(Base):
    __tablename__ = "email_send_logs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(Uuid(as_uuid=True), ForeignKey("outreach_conversations.id", ondelete="CASCADE"), nullable=True)
    sender_domain = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False, index=True)
    subject = Column(String(255), nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="SENT")

    conversation = relationship("OutreachConversation", back_populates="send_logs")


