-- Autonomous Outreach Engine Database Schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Track target companies and technical audit findings
CREATE TABLE IF NOT EXISTS prospect_companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    website_url TEXT UNIQUE NOT NULL,
    industry VARCHAR(100),
    tech_stack_detected JSONB DEFAULT '{}'::jsonb,
    audit_findings JSONB DEFAULT '{}'::jsonb, -- Stores latency, console bugs, missing AI capabilities
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Store enriched contacts & verified emails
CREATE TABLE IF NOT EXISTS prospect_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES prospect_companies(id) ON DELETE CASCADE,
    full_name VARCHAR(255),
    role VARCHAR(100), -- Founder, CTO, Head of Product
    email VARCHAR(255) UNIQUE NOT NULL,
    verification_status VARCHAR(50) DEFAULT 'UNVERIFIED', -- SMTP_VERIFIED, CATCH_ALL, UNVERIFIED, INVALID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Track outreach sequences, replies, and negotiation stages
CREATE TABLE IF NOT EXISTS outreach_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES prospect_leads(id) ON DELETE CASCADE,
    pitch_type VARCHAR(50) DEFAULT 'CUSTOM_ML_AUDIT', -- CUSTOM_ML_AUDIT, QUANTVAULT_DEMO
    email_thread_id TEXT,
    stage VARCHAR(50) DEFAULT 'DRAFTED', -- DRAFTED, SENT, REPLIED, NEGOTIATING, CLOSED_WON, CLOSED_LOST, HITL_HANDOVER
    last_message_content TEXT,
    minimum_acceptable_rate NUMERIC DEFAULT 150.00,
    agreed_rate NUMERIC,
    human_override_required BOOLEAN DEFAULT FALSE,
    override_reason TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_prospect_companies_url ON prospect_companies(website_url);
CREATE INDEX IF NOT EXISTS idx_prospect_leads_email ON prospect_leads(email);
CREATE INDEX IF NOT EXISTS idx_outreach_conversations_stage ON outreach_conversations(stage);
