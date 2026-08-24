# Master Task Roadmap & Execution Phases

This document provides a comprehensive, phased execution plan for the **Autonomous Multi-Agent Outreach Engine**. Each phase contains granular sub-tasks, deliverables, acceptance criteria, and testing targets.

---

## 📋 Execution Roadmap Overview

- [x] **Phase 1: Multi-Source Prospect Discovery & Ingestion Engine**
- [x] **Phase 2: Deep Headless Audit & Visual Diagnostics (Playwright & SPA Scraper)**
- [x] **Phase 3: Lead Enrichment & Deliverability Verification (OSINT & SMTP)**
- [x] **Phase 4: Dynamic Multi-LLM Value Pitch & Blueprint Generator**
- [x] **Phase 5: Inbound/Outbound Email Pipeline & Bounded Negotiation Engine**
- [x] **Phase 6: Two-Way Telegram HITL Bot, CRM Celebration & Background Scheduler**

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
- [x] **2.1 Playwright Headless Diagnostics Engine (`tools/playwright_auditor.py`)**
  - Launch async headless Chromium session with realistic User-Agent and viewport dimensions.
  - Measure true SPA page load times, Time to First Byte (TTFB), and resource payload size.
  - Intercept network requests to detect underlying APIs (GraphQL, Algolia, Pinecone, REST).
- [x] **2.2 Console & Network Error Harvester**
  - Capture unhandled JavaScript exceptions, 4xx/5xx API failures, and slow database queries.
- [x] **2.3 Search & Vector Architecture Gap Analyzer**
  - Test input search fields with test queries to classify search architecture (Basic Substring vs Semantic Vector Search).
  - Verify presence of vector databases (Qdrant, Pinecone, Weaviate, Milvus).
- [x] **2.4 AI Agent & Voice Telemetry Gap Detector**
  - Detect whether the platform lacks agentic real-time voice, copilot, or proactive telemetry capabilities.
- [x] **2.5 Viewport Screenshot & Vision LLM Analysis**
  - Capture high-resolution full-page screenshot for Vision LLM UI/UX assessment.
- [x] **2.6 Phase 2 Unit & Integration Tests**
  - Add test suite in `tests/test_audit.py` with mock HTML fixtures and live fallback handling.

---

## 🎯 Phase 3: Lead Enrichment & Deliverability Verification

### Objective
Enhance email discovery and verification with deep DOM crawling, permutation generation, DNS MX checking, and safe SMTP deliverability pings.

### Tasks
- [x] **3.1 DOM Deep Crawler Enhancement (`tools/web_crawler.py`)**
  - Add crawling for `/about`, `/team`, `/contact`, `/leadership`, `/privacy`, and `/terms`.
  - Extract executive names with associated titles (CEO, CTO, Head of AI, Founder) and JSON-LD structured schema.
- [x] **3.2 OSINT & Social Profile Resolver**
  - Extract GitHub/LinkedIn/X handles from website footers and resolve organizational founders.
- [x] **3.3 Permutation Engine Optimization (`tools/email_verifier.py`)**
  - Generate clean permutations: `{first}.{last}`, `{first}`, `{f}{last}`, `{first}{last}`, `{first}_{last}`, `{f}.{last}`, `{last}.{first}`.
- [x] **3.4 DNS MX & Catch-All Validation**
  - Query DNS MX records with priority sorting.
  - Detect catch-all mail servers using randomized mailbox probes (`nonexistent_{hex}@domain`).
- [x] **3.5 Non-intrusive SMTP Port 25 Handshake**
  - Perform RFC 5321 `HELO -> MAIL FROM -> RCPT TO` without sending payload.
  - Gracefully handle timeouts, greylisting, and ISP port 25 blocking with fallback classification (`PORT_25_BLOCKED`).
- [x] **3.6 Phase 3 Unit Tests**
  - Maintain & expand `tests/test_email_verifier.py` with DNS resolver mocks, JSON-LD parsing, and enrichment tests.

---

## ✍️ Phase 4: Dynamic Multi-LLM Value Pitch & Blueprint Generator

### Objective
Replace static f-string templates with dynamic multi-provider free-tier LLMs (OpenRouter, Groq, NVIDIA NIM, Google Gemini, Ollama) and zero-token deterministic synthesizer fallbacks to produce bespoke, diagnostic-driven pitch drafts and customized architecture blueprints.

### Tasks
- [x] **4.1 Multi-Model Free-Tier LLM Client Router (`tools/llm_router.py` & `agents/pitcher.py`)**
  - Implement unified LLM interface cascading across OpenRouter (free models), Groq, NVIDIA NIM, Google Gemini, and local Ollama.
- [x] **4.2 Context-Aware Pitch Prompt Engineering**
  - Inject company diagnostic context: TTFB latency, load time, search gaps, missing AI voice/telemetry workflows, and detected tech stack.
  - Enforce concise, value-first tone (under 150 words) with zero fluff or generic sales jargon.
- [x] **4.3 Dynamic Blueprint & Code Snippet Generator**
  - Angle A: Generates custom FastAPI + Qdrant microservice architecture tailored to the prospect's tech stack.
  - Angle B: Generates QuantVault real-time voice & telemetry workflow demo link and metric highlights.
- [x] **4.4 Structured JSON Output & Resilient Fallback**
  - Extracts JSON structured output for subject line, email body, pitch angle, and blueprint snippet with zero-token offline synthesizer fallback.
- [x] **4.5 Phase 4 Unit & Integration Tests**
  - Add `tests/test_pitcher.py` covering mock OpenRouter responses, offline synthesizer, and synchronous/asynchronous invocations.

---

## 📬 Phase 5: Inbound/Outbound Email Pipeline & Bounded Negotiation Engine

### Objective
Implement full email delivery with warmup guardrails, background inbound IMAP monitoring, and deterministic negotiation state machines with strict rate floors.

### Tasks
- [x] **5.1 Outbound SMTP Transmission Engine (`tools/email_sender.py`)**
  - Send authenticated SMTP emails via secondary lookalike domain (`outbound_secondary_domain`).
  - Implement warmup rate limiting (15–25 emails/day max) with randomized jitter delays (180s–600s).
  - Log sent messages in `email_send_logs` table with zero-credential dry-run mode.
- [x] **5.2 Inbound IMAP Email Listener (`tools/imap_listener.py`)**
  - Async worker polling IMAP mailbox for new replies with mock reply injection testing.
  - Extract email threads, match `In-Reply-To` / `References` headers with `email_thread_id` in CRM.
- [x] **5.3 Intelligent Intent Classification & LLM Negotiation (`agents/negotiation.py`)**
  - Word-boundary regex & free-tier LLM intent classification (`ACCEPTANCE`, `PRICE_NEGOTIATION`, `CUSTOM_CONTRACT_REQUEST`, `SCOPE_EXPANSION`, `TECHNICAL_QUESTION`, `UNSUBSCRIBE`).
- [x] **5.4 Deterministic Guardrails Enforcement**
  - Rate floor ($150/hr or $5,000 fixed project).
  - Max discount ceiling (10%).
  - Milestone terms (50% upfront, 50% upon completion).
  - Automatic escalation to `HITL_HANDOVER` when bounds are breached.
- [x] **5.5 Phase 5 Unit & Integration Tests**
  - Maintain & expand `tests/test_negotiation.py` and `tests/test_email_sender.py` with multi-turn negotiation and SMTP/IMAP fixtures.

---

## 📱 Phase 6: Two-Way Telegram HITL Bot, CRM Celebration & Background Scheduler

### Objective
Transform one-way notifications into an interactive two-way Telegram management bot, auto-invoicing deal triggers, and automated recurring background jobs.

### Tasks
- [x] **6.1 Interactive Two-Way Telegram Bot (`tools/telegram_bot.py`)**
  - Implement Telegram webhook/long-polling callback query handler.
  - Send inline action buttons when HITL handover triggers: `[Approve Discount]`, `[Counter with $X]`, `[Take Over via Email]`.
  - Update `outreach_conversations` state directly from Telegram button clicks.
- [x] **6.2 Deal Won & Auto-Invoicing Trigger (`agents/alerts.py`)**
  - "Gig Won" celebration alert with rate summary and client details.
  - Webhook dispatch for auto-invoicing (Stripe / InvoiceNinja / QuickBooks).
- [x] **6.3 Background Task Scheduler (`workflow/scheduler.py`)**
  - APScheduler / Asyncio background daemon for:
    - Daily discovery runs (e.g. 08:00 AM UTC).
    - Periodic inbox reply checks (every 15 minutes).
    - Automated follow-up sequencing (bump after 3 business days of no reply).
- [x] **6.4 CLI Command Expansion (`main.py`)**
  - Add CLI commands: `daemon` (runs background scheduler), `followup` (executes bump sequencing), `inbox` (checks replies), `audit` (runs standalone Playwright audit), `discover` (runs multi-source scraper).
- [x] **6.5 End-to-End Pipeline Verification**
  - Full end-to-end dry run test suite verifying database persistence, LangGraph routing, scheduler jobs, and alert dispatching (`tests/test_telegram_bot.py`, `tests/test_alerts.py`, `tests/test_scheduler.py`, `tests/test_pipeline.py`).

