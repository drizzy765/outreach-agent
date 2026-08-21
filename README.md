# Autonomous Outreach Engine 🚀

An autonomous multi-agent lead discovery, technical diagnostic audit, deliverability-verified enrichment, tailored value-add pitching, and bounded negotiation engine powered by **LangGraph**, **Playwright**, and **PostgreSQL**.

---

## 🏗️ Architecture

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

---

## ⚡ Quickstart

### 1. Start PostgreSQL CRM
```bash
docker compose up -d
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your OpenAI/Anthropic keys and Telegram credentials
```

### 3. Install Dependencies
```bash
pip install -e .
```

### 4. Run the Pipeline
```bash
# Execute end-to-end pipeline on a target prospect
python main.py run --name "ApexQuant Analytics" --url "https://apexquant-sample.io"

# Simulate an incoming negotiation reply
python main.py run --name "ApexQuant Analytics" --url "https://apexquant-sample.io" --reply "Can you do $2,000 for this?"

# Verify email permutations using open-source MX & SMTP handshake
python main.py verify-email Sam Altman openai.com
```

### 5. Run Test Suite
```bash
pytest
```
