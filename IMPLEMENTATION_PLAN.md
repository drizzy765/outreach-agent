# Autonomous Multi-Agent Outreach Engine — Implementation Plan & Architecture Specification

## 1. System Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              AUTONOMOUS OUTREACH ENGINE                                │
│                                                                                        │
│  [1. Prospect Discovery] ──► [2. Technical Audit Agent] ──► [3. Lead Enrichment]       │
│  (ProductHunt, IndieHackers,  (Playwright MCP, Lighthouse,    (MailScout, DOM Crawler, │
│   YCombinator, Tech Stacks)    Console & AI Feature Check)     SMTP Deliverability)    │
│                                                                      │                 │
│                                                                      ▼                 │
│  [6. Deal Closer & Alerts] ◄── [5. Negotiation Engine] ◄─── [4. Value-Add Pitcher]     │
│  (Telegram Bot, Auto-Invoicing (Bounded LangGraph State,      (Custom ML Solution /    │
│   & "Gig Won" Celebration)      Human-in-the-Loop Override)    QuantVault Product Demo)│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

The system operates as an end-to-end autonomous pipeline orchestrated via **LangGraph**, **SQLAlchemy (PostgreSQL CRM)**, **Playwright**, open-source email verification tools, and real-time **Telegram** alerts.

---

## 2. Core Agent Roles & LangGraph Nodes

### Agent 1: Prospect Discovery Agent (`agents/discovery.py`)
- **Goal:** Continuously discover early-stage startups, SaaS products, and fintech/e-commerce platforms.
- **Data Ingestion Sources:**
  - ProductHunt daily RSS/API launch feeds
  - Y Combinator Startup Directory & Hacker News API
  - GitHub Trending AI & SaaS repositories
  - Google Dorks (e.g., `site:*.io "pricing" "AI"`)
- **Output:** Populates `prospect_companies` table with URLs, company names, and initial tech tags.

### Agent 2: Technical Diagnostic & Audit Agent (`agents/audit.py`)
- **Goal:** Perform automated, non-invasive reconnaissance on target URLs to detect engineering gaps.
- **Diagnostic Execution Checks:**
  - **Frontend & Performance:** Playwright DOM inspection, Time to First Byte (TTFB) latency, JavaScript console error logging.
  - **Search & Intelligence Gaps:** Evaluates whether the platform uses basic substring/SQL search vs. semantic vector search (Qdrant, Pinecone, embeddings).
  - **Automation & LLM Integration:** Inspects for absent agentic voice workflows, predictive forecasting, or real-time AI copilot capabilities.
  - **Visual Viewport Audit:** Captures high-res viewport screenshots for Vision LLM UI/UX analysis.
- **Output:** Enriches `prospect_companies.audit_findings` and selects optimal pitch angle.

### Agent 3: Lead Enrichment & Email Extraction Engine (`agents/enrichment.py`)
- **Goal:** Extract, reconstruct, and verify founder/CTO emails without commercial SaaS fees.
- **Multi-tiered Verification Pipeline:**
  1. **DOM Deep Crawler:** Crawls `/about`, `/team`, `/contact`, `/leadership`, `/terms`, `/privacy` for mailto links and executive names.
  2. **Email Permutation Engine:** Generates `{first}.{last}`, `{first}`, `{f}{last}`, `{first}{last}` permutations across the target domain.
  3. **DNS MX & Catch-All Detection:** Queries DNS MX records; tests against randomized mailboxes to detect catch-all servers.
  4. **SMTP Deliverability Ping:** Performs RFC 5321 `HELO -> MAIL FROM -> RCPT TO` handshake on port 25 without sending messages.
- **Output:** Populates `prospect_leads` with verified emails (`SMTP_VERIFIED`, `CATCH_ALL`, `UNVERIFIED`).

### Agent 4: Value-Add Pitch & Product Showcase Agent (`agents/pitcher.py`)
- **Goal:** Draft bespoke, problem-solving cold outreach tailored to audit findings.
- **Pitch Angles:**
  - **Angle A (Custom ML/AI Engineering):** Pinpoints high query latency and proposes a decoupled FastAPI vector search microservice cutting query latency by 60%.
  - **Angle B (Product-Led Showcase — QuantVault):** Identifies missing voice/telemetry workflows and showcases QuantVault's real-time voice command and risk analytics demo.
- **Output:** Stores personalized pitch in `outreach_conversations` with stage `DRAFTED`.

### Agent 5: Conversational Follow-Up & Bounded Negotiation Agent (`agents/negotiation.py`)
- **Goal:** Monitor incoming inbox replies via IMAP/Gmail API, classify intent, answer technical questions, and negotiate within strict bounds.
- **Deterministic State Machine & Guardrails:**
  - **Rate Floor:** Strictly enforces minimum hourly rate ($150/hr) or minimum fixed project price ($5,000).
  - **Discount Ceiling:** Max discount permitted is 10%.
  - **Milestone Terms:** Enforces 50% upfront deposit and 50% upon milestone completion.
  - **Human-in-the-Loop (HITL) Override:** Automatically flags conversations requesting custom contract redlines, out-of-scope work, or below-floor pricing, triggering immediate handover.
- **Output:** Updates conversation stage to `NEGOTIATING`, `HITL_HANDOVER`, or `CLOSED_WON`.

### Agent 6: Notification & CRM Celebration Dispatcher (`agents/alerts.py`)
- **Goal:** Maintain pipeline states in PostgreSQL and dispatch instant push notifications via Telegram Bot API.
- **Triggers:**
  - 🔥 **Hot Prospect Reply:** Notifies operator when a lead expresses interest.
  - 🚨 **HITL Handover:** Pings phone with message context when manual input is required.
  - 🍾 **"Gig Won" Celebration:** Instant summary with confetti and auto-invoicing notification upon deal agreement.

---

## 3. Database Schema (PostgreSQL Lead CRM)

```sql
-- Target companies and diagnostic findings
CREATE TABLE prospect_companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    website_url TEXT UNIQUE NOT NULL,
    industry VARCHAR(100),
    tech_stack_detected JSONB DEFAULT '{}'::jsonb,
    audit_findings JSONB DEFAULT '{}'::jsonb,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enriched contacts and verified deliverability
CREATE TABLE prospect_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES prospect_companies(id) ON DELETE CASCADE,
    full_name VARCHAR(255),
    role VARCHAR(100),
    email VARCHAR(255) UNIQUE NOT NULL,
    verification_status VARCHAR(50) DEFAULT 'UNVERIFIED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sequences, negotiations, and deal stages
CREATE TABLE outreach_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id REFERENCES prospect_leads(id) ON DELETE CASCADE,
    pitch_type VARCHAR(50) DEFAULT 'CUSTOM_ML_AUDIT',
    email_thread_id TEXT,
    stage VARCHAR(50) DEFAULT 'DRAFTED',
    last_message_content TEXT,
    minimum_acceptable_rate NUMERIC DEFAULT 150.00,
    agreed_rate NUMERIC,
    human_override_required BOOLEAN DEFAULT FALSE,
    override_reason TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Architecture Improvements & Deliverability Guardrails

1. **Email Warmup & Secondary Domain Strategy:**
   - Outbound campaigns run exclusively on secondary lookalike domains (e.g., `yourname-labs.com`).
   - Strict DNS configuration: SPF, DKIM, DMARC, and custom tracking domains.
   - Daily sending volume capped at **15–25 hyper-targeted emails/day** with jittered delays.
2. **Automated Video / Interactive Demo Generator:**
   - Playwright captures a 15-second viewport interaction video highlighting UI/search bottlenecks, paired with an AI audio walkthrough.
3. **Strict Price Negotiation State Machine:**
   - Hard limits preventing sub-floor rates and unauthorized discounts.
4. **Real-time Mobile Push Alerts:**
   - Asynchronous Telegram Bot dispatching deal alerts and handover requests instantly.

---

## 5. Directory Structure

```
outreach-agent/
├── pyproject.toml              # Dependencies and packaging
├── docker-compose.yml          # PostgreSQL CRM service
├── schema.sql                  # PostgreSQL CRM database schema
├── .env.example                # Environment variables template
├── IMPLEMENTATION_PLAN.md      # Full architecture specification
├── config.py                   # Pydantic Settings & configuration
├── database/
│   ├── __init__.py
│   ├── connection.py           # Async SQLAlchemy session manager
│   └── models.py               # ORM mapping to PostgreSQL CRM
├── tools/
│   ├── __init__.py
│   ├── email_verifier.py       # Permutations, DNS MX, Catch-all, SMTP ping
│   ├── web_crawler.py          # DOM deep crawler for emails & leadership
│   └── telegram_bot.py         # Telegram alerts & Gig Won celebration
├── agents/
│   ├── __init__.py
│   ├── discovery.py            # Agent 1: Prospect Discovery
│   ├── audit.py                # Agent 2: Technical Diagnostic & Audit Agent
│   ├── enrichment.py           # Agent 3: Lead Enrichment & Email Engine
│   ├── pitcher.py              # Agent 4: Value-Add Pitch & Showcase Agent
│   ├── negotiation.py          # Agent 5: Bounded Negotiation & State Machine
│   └── alerts.py               # Agent 6: Notification & CRM Celebration
├── workflow/
│   ├── __init__.py
│   ├── state.py                # LangGraph State & Type definitions
│   └── graph.py                # LangGraph StateGraph orchestration pipeline
├── tests/
│   ├── __init__.py
│   ├── test_email_verifier.py  # Unit tests for permutation & MX checks
│   ├── test_negotiation.py     # Unit tests for bounded state machine
│   └── test_pitcher.py         # Unit tests for pitch generator
└── main.py                     # Typer CLI application
```
