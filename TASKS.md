# Master Task Roadmap & Execution Phases

This document provides a comprehensive, phased execution plan for the **Autonomous Multi-Agent Outreach Engine**. Each phase contains granular sub-tasks, deliverables, acceptance criteria, and testing targets.

---

## 📋 Execution Roadmap Overview

- [x] **Phase 1: Multi-Source Prospect Discovery & Ingestion Engine**
- [ ] **Phase 2: Deep Headless Audit & Visual Diagnostics (Playwright & SPA Scraper)**
- [ ] **Phase 3: Lead Enrichment & Deliverability Verification (OSINT & SMTP)**
- [ ] **Phase 4: Dynamic Multi-LLM Value Pitch & Blueprint Generator**
- [ ] **Phase 5: Inbound/Outbound Email Pipeline & Bounded Negotiation Engine**
- [ ] **Phase 6: Two-Way Telegram HITL Bot, CRM Celebration & Background Scheduler**

---

## 🚀 Phase 1: Multi-Source Prospect Discovery & Ingestion Engine

### Objective
Expand the single ProductHunt RSS scraper into a robust multi-source discovery pipeline that aggregates early-stage startups and SaaS companies from 4 distinct channels with automatic deduplication.

### Tasks
- [x] **1.1 Y Combinator Startup Directory Scraper**
  - Implement async Algolia/YC API scraper to fetch current & recent batch startups (W24, S24, F24).
  - Extract company name, website URL, batch, industry tags, and founder profiles.
- [x] **1.2 Hacker News (HN) Firebase API Ingestion**
  - Query official Firebase HN API (`/v0/item/...`) and Algolia HN API for daily `Show HN` and monthly `Ask HN: Who is hiring?`.
  - Parse product URLs and descriptions using regex and BeautifulSoup.
- [x] **1.3 GitHub Trending SaaS / AI Ingestion**
  - Scrape GitHub Trending and Public API for Python / TypeScript repos matching `topic:saas`, `topic:ai-agent`, `topic:devtools`.
  - Extract project homepage URLs and README summaries.
- [x] **1.4 ProductHunt Feed Enhancement**
  - Add resilience, retry logic, and metadata extraction.
- [x] **1.5 Database Deduplication & Auto-Tagging**
  - Normalize domains (strip `www.`, protocol, UTM query parameters).
  - Update `ProspectCompany` table with deduplication on `website_url`.
- [x] **1.6 Phase 1 Unit & Integration Tests**
  - Add tests in `tests/test_discovery.py` covering mock responses for YC, HN, GitHub, and ProductHunt.

---

## 🔬 Phase 2: Deep Headless Audit & Visual Diagnostics

### Objective
Upgrade the basic HTTP GET audit into a high-fidelity diagnostic engine using Playwright to render JavaScript SPAs, log console errors, capture viewport screenshots, and pinpoint engineering gaps.

### Tasks
- [ ] **2.1 Playwright Headless Diagnostics Engine (`tools/playwright_auditor.py`)**
  - Launch async headless Chromium session with realistic User-Agent and viewport dimensions.
  - Measure true SPA page load times, Time to First Byte (TTFB), and resource payload size.
  - Intercept network requests to detect underlying APIs (GraphQL, Algolia, Pinecone, REST).
- [ ] **2.2 Console & Network Error Harvester**
  - Capture unhandled JavaScript exceptions, 4xx/5xx API failures, and slow database queries.
- [ ] **2.3 Search & Vector Architecture Gap Analyzer**
  - Test input search fields with test queries to classify search architecture (Basic Substring vs Semantic Vector Search).
  - Verify presence of vector databases (Qdrant, Pinecone, Weaviate, Milvus).
- [ ] **2.4 AI Agent & Voice Telemetry Gap Detector**
  - Detect whether the platform lacks agentic real-time voice, copilot, or proactive telemetry capabilities.
- [ ] **2.5 Viewport Screenshot & Vision LLM Analysis**
  - Capture high-resolution full-page screenshot for Vision LLM UI/UX assessment.
- [ ] **2.6 Phase 2 Unit & Integration Tests**
  - Add test suite in `tests/test_audit.py` with mock HTML fixtures and live fallback handling.

---

## 🎯 Phase 3: Lead Enrichment & Deliverability Verification

### Objective
Enhance email discovery and verification with deep DOM crawling, permutation generation, DNS MX checking, and safe SMTP deliverability pings.

### Tasks
- [ ] **3.1 DOM Deep Crawler Enhancement (`tools/web_crawler.py`)**
  - Add crawling for `/about`, `/team`, `/contact`, `/leadership`, `/privacy`, and `/terms`.
  - Extract executive names with associated titles (CEO, CTO, Head of AI, Founder).
- [ ] **3.2 OSINT & Social Profile Resolver**
  - Extract GitHub/LinkedIn/X handles from website footers and resolve organizational founders.
- [ ] **3.3 Permutation Engine Optimization (`tools/email_verifier.py`)**
  - Generate clean permutations: `{first}.{last}`, `{first}`, `{f}{last}`, `{first}{last}`, `{first}_{last}`.
- [ ] **3.4 DNS MX & Catch-All Validation**
  - Query DNS MX records with priority sorting.
  - Detect catch-all mail servers using randomized mailbox probes (`nonexistent_{hex}@domain`).
- [ ] **3.5 Non-intrusive SMTP Port 25 Handshake**
  - Perform RFC 5321 `HELO -> MAIL FROM -> RCPT TO` without sending payload.
  - Gracefully handle timeouts, greylisting, and ISP port 25 blocking with fallback classification.
- [ ] **3.6 Phase 3 Unit Tests**
  - Maintain & expand `tests/test_email_verifier.py` with DNS resolver mocks.

---

## ✍️ Phase 4: Dynamic Multi-LLM Value Pitch & Blueprint Generator

### Objective
Replace static f-string templates with dynamic LLM generation (OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet, Google Gemini 1.5 Pro) to produce bespoke, diagnostic-driven pitch drafts and customized architecture blueprints.

### Tasks
- [ ] **4.1 Multi-Model LLM Client Integration (`agents/pitcher.py`)**
  - Implement unified LLM interface supporting OpenAI, Anthropic, and Google Gemini via `config.py`.
- [ ] **4.2 Context-Aware Pitch Prompt Engineering**
  - Inject company diagnostic context: TTFB latency, search gaps, missing AI voice/telemetry workflows, detected tech stack.
  - Enforce concise, value-first tone (under 150 words) with zero fluff or generic sales jargon.
- [ ] **4.3 Dynamic Blueprint & Code Snippet Generator**
  - Angle A: Generates custom FastAPI + Qdrant microservice architecture tailored to the prospect's tech stack.
  - Angle B: Generates QuantVault real-time voice & telemetry workflow demo link and metric highlights.
- [ ] **4.4 Pydantic Structured Output Validation**
  - Enforce JSON structured output for subject line, email body, pitch angle, and primary call-to-action (CTA).
- [ ] **4.5 Phase 4 Unit & Integration Tests**
  - Add `tests/test_pitcher.py` mocking LLM responses and validating schema structure.

---

## 📬 Phase 5: Inbound/Outbound Email Pipeline & Bounded Negotiation Engine

### Objective
Implement full email delivery with warmup guardrails, background inbound IMAP monitoring, and deterministic negotiation state machines with strict rate floors.

### Tasks
- [ ] **5.1 Outbound SMTP Transmission Engine (`tools/email_sender.py`)**
  - Send authenticated SMTP emails via secondary lookalike domain (`outbound_secondary_domain`).
  - Implement warmup rate limiting (15–25 emails/day max) with randomized jitter delays (180s–600s).
  - Log sent messages in `email_send_logs` table.
- [ ] **5.2 Inbound IMAP Email Listener (`tools/imap_listener.py`)**
  - Async worker polling IMAP mailbox for new replies.
  - Extract email threads, match `In-Reply-To` / `References` headers with `email_thread_id` in CRM.
- [ ] **5.3 Intelligent Intent Classification & LLM Negotiation (`agents/negotiation.py`)**
  - LLM-assisted intent classification: `ACCEPTANCE`, `PRICE_NEGOTIATION`, `CUSTOM_CONTRACT_REQUEST`, `SCOPE_EXPANSION`, `TECHNICAL_QUESTION`, `UNSUBSCRIBE`.
- [ ] **5.4 Deterministic Guardrails Enforcement**
  - Rate floor ($150/hr or $5,000 fixed project).
  - Max discount ceiling (10%).
  - Milestone terms (50% upfront, 50% upon completion).
  - Automatic escalation to `HITL_HANDOVER` when bounds are breached.
- [ ] **5.5 Phase 5 Unit & Integration Tests**
  - Maintain & expand `tests/test_negotiation.py` with multi-turn negotiation fixtures.

---

## 📱 Phase 6: Two-Way Telegram HITL Bot, CRM Celebration & Background Scheduler

### Objective
Transform one-way notifications into an interactive two-way Telegram management bot, auto-invoicing deal triggers, and automated recurring background jobs.

### Tasks
- [ ] **6.1 Interactive Two-Way Telegram Bot (`tools/telegram_bot.py`)**
  - Implement Telegram webhook/long-polling callback query handler.
  - Send inline action buttons when HITL handover triggers: `[Approve Discount]`, `[Counter with $X]`, `[Take Over via Email]`.
  - Update `outreach_conversations` state directly from Telegram button clicks.
- [ ] **6.2 Deal Won & Auto-Invoicing Trigger (`agents/alerts.py`)**
  - "Gig Won" celebration alert with rate summary and client details.
  - Webhook dispatch for auto-invoicing (Stripe / InvoiceNinja / QuickBooks).
- [ ] **6.3 Background Task Scheduler (`workflow/scheduler.py`)**
  - APScheduler daemon for:
    - Daily discovery runs (e.g. 08:00 AM UTC).
    - Periodic inbox reply checks (every 15 minutes).
    - Automated follow-up sequencing (bump after 3 business days of no reply).
- [ ] **6.4 CLI Command Expansion (`main.py`)**
  - Add CLI commands: `daemon` (runs background scheduler), `inbox` (checks replies), `audit` (runs standalone Playwright audit), `discover` (runs multi-source scraper).
- [ ] **6.5 End-to-End Pipeline Verification**
  - Full end-to-end dry run test verifying database persistence, LangGraph routing, and alert dispatching.
