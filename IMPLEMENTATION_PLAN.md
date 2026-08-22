# Autonomous Multi-Agent Outreach Engine — Implementation Plan & Architecture Specification

## 1. System Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 AUTONOMOUS OUTREACH ENGINE                                   │
│                                                                                              │
│  [1. Prospect Discovery] ──► [2. Technical Audit Agent] ──► [3. Lead Enrichment]             │
│  (ProductHunt, YCombinator,   (Playwright SPA Engine,        (DOM Crawler, Permutations,     │
│   HackerNews, GitHub Trending) Lighthouse, Console & AI Gaps) SMTP Deliverability & OSINT)  │
│                                                                             │                │
│                                                                             ▼                │
│  [6. Deal Closer & Alerts] ◄── [5. Negotiation & Inbound] ◄── [4. Dynamic Value Pitcher]    │
│  (Interactive Telegram Bot,    (IMAP Poller, Bounded Rate      (Multi-LLM: OpenAI/Gemini/    │
│   Stripe/Auto-Invoicing, CRM)   State Machine, HITL Handover)   Anthropic, Tailored Blueprints)
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

The system operates as an end-to-end autonomous pipeline orchestrated via **LangGraph**, **SQLAlchemy (PostgreSQL CRM)**, **Playwright headless diagnostics**, multi-model **LLM synthesis** (OpenAI / Anthropic / Google Gemini), asynchronous **IMAP/SMTP** email pipelines, and an **interactive two-way Telegram Bot** for human-in-the-loop (HITL) oversight.

---

## 2. Core Agent Roles & LangGraph Nodes

### Agent 1: Multi-Source Prospect Discovery Agent (`agents/discovery.py`)
- **Goal:** Continuously discover early-stage startups, fast-growing SaaS products, and fintech/e-commerce platforms across multiple feeds.
- **Data Ingestion Sources:**
  - **ProductHunt:** Daily RSS & API launch feeds
  - **Y Combinator Startup Directory:** Algolia/YC directory scraper for current and recent batches (e.g. W24, S24, F24)
  - **Hacker News API:** Firebase API queries for `Show HN` and `Ask HN: Who is hiring?`
  - **GitHub Trending:** Scrapes trending AI & SaaS repositories for newly launched open-core products
  - **Automated Google Dorks:** Formats queries (`site:*.io "pricing" "AI"`, `site:*.ai "sign up"`)
- **Output:** Deduplicates and populates `prospect_companies` table with URLs, company names, industry tags, and tech cues.

### Agent 2: Technical Diagnostic & Performance Audit Agent (`agents/audit.py`)
- **Goal:** Perform automated, non-invasive reconnaissance on target URLs to detect engineering bottlenecks and architecture gaps.
- **Diagnostic Execution Checks:**
  - **Headless Browser Execution (Playwright):** Renders SPAs (React, Next.js, Vue), captures JavaScript console errors, and tracks network call latencies.
  - **Performance & TTFB:** Measures Time to First Byte and asset weight.
  - **Search & Semantic Intelligence Gaps:** Analyzes input forms and API payloads to detect whether the platform uses basic substring/SQL search vs. vector search (Qdrant, Pinecone, Milvus, embeddings).
  - **Automation & Agentic Voice Gaps:** Evaluates absence of low-latency voice command workflows, real-time telemetry copilots, or proactive alerting.
  - **Visual Viewport Audit:** Captures full-page viewport screenshots for Vision LLM UI/UX analysis.
- **Output:** Enriches `prospect_companies.audit_findings` and recommends pitch angle (`CUSTOM_ML_AUDIT` or `QUANTVAULT_DEMO`).

### Agent 3: Lead Enrichment & Email Extraction Engine (`agents/enrichment.py`)
- **Goal:** Extract, reconstruct, and verify founder/CTO emails without commercial SaaS fees.
- **Multi-tiered Verification Pipeline:**
  1. **DOM Deep Crawler (`tools/web_crawler.py`):** Crawls `/about`, `/team`, `/contact`, `/leadership`, `/terms`, `/privacy` for mailto links and executive names.
  2. **Email Permutation Engine (`tools/email_verifier.py`):** Generates standard corporate variations (`{first}.{last}`, `{first}`, `{f}{last}`, `{first}{last}`) across the target domain.
  3. **DNS MX & Catch-All Detection:** Resolves MX records and tests against randomized mailboxes to detect catch-all servers.
  4. **SMTP Deliverability Ping:** Performs RFC 5321 `HELO -> MAIL FROM -> RCPT TO` handshake on port 25 without sending messages.
  5. **OSINT Profile Resolution:** Fallback lookup for GitHub/LinkedIn organization handles.
- **Output:** Populates `prospect_leads` with verified deliverability status (`SMTP_VERIFIED`, `CATCH_ALL`, `UNVERIFIED`).

### Agent 4: Value-Add Pitch & Product Showcase Agent (`agents/pitcher.py`)
- **Goal:** Synthesize technical audit findings into hyper-personalized, problem-first cold outreach using dynamic LLMs (OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet, or Google Gemini 1.5 Pro).
- **Pitch Strategies:**
  - **Angle A (Custom ML/AI Engineering):** Pinpoints high query TTFB and unindexed search; proposes a decoupled FastAPI vector search microservice cutting latency by 60%.
  - **Angle B (Product-Led Showcase — QuantVault):** Identifies missing real-time voice/telemetry workflows; showcases QuantVault's real-time voice command and risk analytics demo.
- **Dynamic Architecture Blueprint Generator:** Produces customized architectural flowcharts and tailored code snippets directly in the email body.
- **Output:** Stores personalized pitch in `outreach_conversations` with stage `DRAFTED`.

### Agent 5: Conversational Follow-Up & Bounded Negotiation Agent (`agents/negotiation.py`)
- **Goal:** Handle incoming inbox replies, classify intent using LLM reasoning + regex fallback, answer technical questions, and negotiate within strict deterministic bounds.
- **Deterministic State Machine & Guardrails:**
  - **Rate Floor:** Strictly enforces minimum hourly rate ($150/hr) or minimum fixed project price ($5,000).
  - **Discount Ceiling:** Max discount permitted is 10%.
  - **Milestone Terms:** Enforces 50% upfront deposit and 50% upon milestone completion.
  - **Human-in-the-Loop (HITL) Override:** Flags conversations requesting custom contract redlines (MSAs, NDAs), out-of-scope tasks, or below-floor pricing.
- **Inbound & Outbound Communication Services:**
  - **Inbound IMAP Poller:** Background worker monitoring inbox for replies matching `email_thread_id`.
  - **Outbound SMTP Engine:** Sends emails with jittered delays (180s–600s) capped at 15–25 emails/day per lookalike domain.
- **Output:** Updates conversation stage to `NEGOTIATING`, `HITL_HANDOVER`, or `CLOSED_WON`.

### Agent 6: Notification, CRM & Two-Way Telegram Dispatcher (`agents/alerts.py`)
- **Goal:** Maintain pipeline states in PostgreSQL and provide real-time mobile push notifications with interactive two-way operator action buttons.
- **Interactive Triggers:**
  - 🔥 **Hot Prospect Reply:** Real-time push alert summarizing prospect sentiment.
  - 🚨 **HITL Handover with Inline Buttons:** Telegram inline keyboard with actions: `[Approve Discount]`, `[Counter with $X]`, `[Take Over via Email]`.
  - 🍾 **"Gig Won" Celebration:** Instant summary with confetti and auto-invoicing trigger (Stripe / InvoiceNinja API).

---

## 3. Database Schema (PostgreSQL Lead CRM)

```sql
-- Target companies and diagnostic findings
CREATE TABLE IF NOT EXISTS prospect_companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    website_url TEXT UNIQUE NOT NULL,
    industry VARCHAR(100),
    tech_stack_detected JSONB DEFAULT '{}'::jsonb,
    audit_findings JSONB DEFAULT '{}'::jsonb,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enriched contacts and verified deliverability
CREATE TABLE IF NOT EXISTS prospect_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES prospect_companies(id) ON DELETE CASCADE,
    full_name VARCHAR(255),
    role VARCHAR(100),
    email VARCHAR(255) UNIQUE NOT NULL,
    verification_status VARCHAR(50) DEFAULT 'UNVERIFIED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sequences, negotiations, and deal stages
CREATE TABLE IF NOT EXISTS outreach_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES prospect_leads(id) ON DELETE CASCADE,
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

-- Outbound email log for warmup & rate-limiting audit
CREATE TABLE IF NOT EXISTS email_send_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES outreach_conversations(id) ON DELETE CASCADE,
    sender_domain VARCHAR(255) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'SENT'
);
```

---

## 4. Deliverability Guardrails & Safety Architecture

1. **Email Warmup & Secondary Domain Strategy:**
   - Outbound campaigns run on lookalike domains (`yourname-labs.com`).
   - Strict DNS verification: SPF, DKIM, DMARC alignment.
   - Daily sending volume hard-capped at **15–25 emails/day** with randomized jitter delays (3 to 10 minutes between sends).
2. **Automated Headless Diagnostics & Screenshots:**
   - Playwright captures DOM snapshots and viewport screenshots for deep audit fidelity.
3. **Strict Price Negotiation State Machine:**
   - Hard code limits preventing sub-floor rates and unauthorized discounts regardless of LLM generation.
4. **Two-Way Interactive Mobile Push (Telegram Bot):**
   - Inline action buttons allow instantaneous 1-tap approvals or manual overrides.
5. **Background Scheduler:**
   - APScheduler / Celery periodic jobs for discovery, inbox polling, and follow-up sequences.

---

## 5. Directory Structure

```
outreach-agent/
├── pyproject.toml              # Dependencies and packaging
├── docker-compose.yml          # PostgreSQL CRM & Redis service
├── schema.sql                  # PostgreSQL CRM database schema
├── .env.example                # Environment variables template
├── IMPLEMENTATION_PLAN.md      # Full architecture specification
├── TASKS.md                    # Granular phase-by-phase task roadmap
├── config.py                   # Pydantic Settings & configuration
├── database/
│   ├── __init__.py
│   ├── connection.py           # Async SQLAlchemy session manager
│   └── models.py               # ORM mapping to PostgreSQL CRM
├── tools/
│   ├── __init__.py
│   ├── email_verifier.py       # Permutations, DNS MX, Catch-all, SMTP ping
│   ├── email_sender.py         # SMTP transmission with rate-limiting & jitter
│   ├── imap_listener.py        # IMAP inbound email polling service
│   ├── web_crawler.py          # DOM deep crawler for emails & leadership
│   ├── playwright_auditor.py   # Headless browser SPA crawler & screenshot capture
│   └── telegram_bot.py         # Interactive Telegram alerts & callback listener
├── agents/
│   ├── __init__.py
│   ├── discovery.py            # Agent 1: Multi-source Prospect Discovery
│   ├── audit.py                # Agent 2: Technical Diagnostic & Audit Agent
│   ├── enrichment.py           # Agent 3: Lead Enrichment & Email Engine
│   ├── pitcher.py              # Agent 4: Dynamic LLM Pitch & Showcase Agent
│   ├── negotiation.py          # Agent 5: Bounded Negotiation & State Machine
│   └── alerts.py               # Agent 6: Notification & Two-Way Telegram
├── workflow/
│   ├── __init__.py
│   ├── state.py                # LangGraph State & Type definitions
│   ├── graph.py                # LangGraph StateGraph orchestration pipeline
│   └── scheduler.py            # APScheduler automated recurring background jobs
├── tests/
│   ├── __init__.py
│   ├── test_discovery.py       # Tests for multi-source scraping
│   ├── test_audit.py           # Tests for Playwright / HTTP audit
│   ├── test_email_verifier.py  # Unit tests for permutation & MX checks
│   ├── test_negotiation.py     # Unit tests for bounded state machine
│   └── test_pitcher.py         # Unit tests for pitch generator
└── main.py                     # Typer CLI application & worker daemon
```

