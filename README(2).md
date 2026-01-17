# LLM Council — Local Distributed Deployment (Tailscale)

A distributed system where multiple **local** LLMs collaborate through a **3-stage council workflow** to answer a question:

1) **Opinions**: each council node generates an independent answer  
2) **Reviews**: each node reviews & ranks anonymized opinions (JSON scores + ranking)  
3) **Synthesis**: a chairman model produces a final consolidated answer  

Everything runs **locally** with **Ollama** (no cloud API). Machines communicate securely over **Tailscale** (private `100.x.x.x` network).

---

## Group Information
- **Group:** `CDOF3-A5`
- **Members:** Wendy Duong, Hiba Nejjari, Lisa Naccache, Cyprien Mouton, Neil Mahcer

---

## Table of Contents
1. [Project Overview](#project-overview)  
2. [Architecture](#architecture)  
3. [Architecture Overview (Diagram)](#architecture-overview-diagram)  
4. [Workflow (Stage 1 -> 2 -> 3)](#workflow-stage-1--2--3)  
5. [Setup & Installation](#setup--installation)  
6. [Requirements Compliance](#requirements-compliance)  
7. [Configuration Guide](#configuration-guide)  
8. [How to Run the Demo](#how-to-run-the-demo)  
9. [Testing & Verification](#testing--verification)  
10. [Screenshots (UI + Swagger)](#screenshots-ui--swagger)  
11. [Technical Architecture](#technical-architecture)  
12. [Project Structure](#project-structure)  
13. [Team Responsibilities](#team-responsibilities)  
14. [Generative AI Usage Statement](#generative-ai-usage-statement)

---

## Project Overview

This project is made of 4 main components:

- **Council Nodes** (`council_node/`)  
  FastAPI service running a local LLM via **Ollama**, able to:
  - generate an **opinion** (Stage 1)
  - generate a **review** (Stage 2)

- **Chairman** (`chairman/`)  
  FastAPI service that produces the **final answer** (Stage 3) using all opinions + reviews.

- **Orchestrator** (`orchestrator/`)  
  Central coordination service that:
  - monitors health of all nodes + chairman
  - runs Stage 1 → Stage 2 → Stage 3
  - stores results (opinions/reviews/final) for each query
  - serves the **frontend**

- **Frontend UI** (`frontend/`)  
  Web interface that displays:
  - node status (online/offline)
  - stage-by-stage outputs
  - final synthesis

---

## Architecture

### Services & Ports
- **Orchestrator**: `http://localhost:8080`
- **Chairman**: `http://localhost:9000`
- **Council node(s)**: `http://<node-ip>:5001` (one per machine)

### Network (Tailscale)
We used **Tailscale** to connect machines on a private network (`100.x.x.x`) without exposing ports publicly.  
We joined the same tailnet using a **team tailnet account** (common account).

### Example config (real project)
Your `config.yaml` defines all nodes with their Tailscale IPs and models, for example:
- council-1 → `llama3.2:1b`
- council-2 → `phi3:mini`
- council-3 → `smollm2:135m`
- council-4 → `qwen2.5:0.5b`
- council-5 → `qwen2:1.5b`
- chairman → `llama3.2:3b`

---

## Architecture Overview (Diagram)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│                               LLM COUNCIL                                    │
│                    Distributed Local Deployment (Tailscale)                  │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ PC: HIBA                                                                      │
│ Roles: Orchestrator + UI + Chairman + Council Node                            │
│                                                                              │
│ Services                                                                      │
│  - frontend/index.html                                                        │
│  - orchestrator/main.py   (8080)                                              │
│  - chairman/main.py       (9000)                                              │
│  - council_node/main.py   (5001)                                              │
│                                                                              │
│ Responsibilities                                                             │
│  - Entry point for UI                                                        │
│  - Coordinates workflow                                                      │
│  - Health checks & aggregation                                                │
│  - Final synthesis (Chairman)                                                 │
└───────────────┬──────────────────────────────────────────────────────────────┘
                │ REST over Tailscale (http://100.x.x.x)
                │
                │ Stage 1: POST /opinion
                │ Stage 2: POST /review
                │ Stage 3: POST /synthesize
                │
                ▼
        ┌──────────────────────┬──────────────────────┬──────────────────────┐
        │                      │                      │                      │
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│ PC: CYPRIEN           │ │ PC: LISA-VIVO15      │ │ PC: NEIL              │ │ PC: WENDY            │
│ Council Node 1        │ │ Council Node 2        │ │ Council Node 3        │ │ Council Node 5        │
│                       │ │                       │ │                       │ │                       │
│ council_node/main.py  │ │ council_node/main.py  │ │ council_node/main.py  │ │ council_node/main.py  │
│ port: 5001            │ │ port: 5001            │ │ port: 5001            │ │ port: 5001            │
│                       │ │                       │ │                       │ │                       │
│ Endpoints             │ │ Endpoints             │ │ Endpoints             │ │ Endpoints             │
│  - /health            │ │  - /health            │ │  - /health            │ │  - /health            │
│  - /opinion           │ │  - /opinion           │ │  - /opinion           │ │  - /opinion           │
│  - /review            │ │  - /review            │ │  - /review            │ │  - /review            │
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘ └──────────────────────┘


```

## Workflow (Stage 1 -> 2 -> 3)
---
| Stage | Description | Endpoint |
|-------|-------------|----------|
| **1. First Opinions** | Each council node generates independent answer | `POST /opinion` |
| **2. Review & Ranking** | Each node reviews others' answers anonymously | `POST /review` |
| **3. Chairman Synthesis** | Chairman combines insights into final answer | `POST /synthesize` |

---

## Setup & Installation

### Prerequisites (on each machine)

1. **Python 3.10+**
2. **Ollama** installed and running locally
3. **Required LLM model** pulled (assigned in `config.yaml`):
   ```bash
   ollama pull llama3.2:1b  # Example
   ```
4. **Tailscale** installed and connected to the same account (for secure LAN communication)
   > Campus Wi-Fi blocks direct peer-to-peer connections, so Tailscale creates a private network (`100.x.x.x`)

### Install Python dependencies

From project root:

```bash
pip install -r requirements.txt
pip install fastapi uvicorn requests  # Core dependencies
```

---

## Requirements Compliance

### Project Requirements Met

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| No cloud APIs | ✅ | Uses Ollama locally |
| All LLMs run locally | ✅ | Ollama on each machine |
| REST communication | ✅ | FastAPI endpoints |
| 3-stage workflow | ✅ | Opinions → Reviews → Synthesis |
| Chairman separate service | ✅ | Dedicated FastAPI app |
| Chairman separate machine | ✅ | Designed for distributed |
| Health checks | ✅ | `/health` on all services |
| Timeouts & retries | ✅ | Configurable timeouts |
| Graceful degradation | ✅ | min_council_members = 2 |
| Dynamic configuration | ✅ | YAML config + env vars |

---

## Configuration Guide

### Step 1 — Gather Network Information

On each machine, open Tailscale and note the private IP address (format: `100.x.x.x`).

### Step 2 — Configure `config.yaml`

Edit `config.yaml` with your actual machine IPs and model assignments:

```yaml
orchestrator:
  host: "0.0.0.0"
  port: 8080

council_nodes:
  - id: "council-1"
    name: "Llama Analyst (Cyprien)"
    url: "http://100.xxx.xxx.xxx:5001"  # Replace with actual Tailscale IP
    model: "llama3.2:1b"
    priority: 1
    enabled: true

  - id: "council-2"
    name: "Phi Analyst (Lisa)"
    url: "http://100.xxx.xxx.xxx:5001"
    model: "phi3:mini"
    priority: 2
    enabled: true

  - id: "council-3"
    name: "SmolLM Analyst (Neil)"
    url: "http://100.xxx.xxx.xxx:5001"
    model: "smollm2:135m"
    priority: 3
    enabled: true

  - id: "council-4"
    name: "Qwen Small Analyst (Hiba)"
    url: "http://100.xxx.xxx.xxx:5001"
    model: "qwen2.5:0.5b"
    priority: 4
    enabled: true

  - id: "council-5"
    name: "Qwen Analyst (Wendy)"
    url: "http://100.xxx.xxx.xxx:5001"
    model: "qwen2:1.5b"
    priority: 5
    enabled: true

chairman:
  id: "chairman"
  name: "Council Chairman"
  url: "http://100.xxx.xxx.xxx:9000"
  model: "llama3.2:3b"

fallback:
  min_council_members: 2
  enable_local_fallback: true
  local_model: "llama3.2:1b"

timeouts:
  health_check: 5
  opinion: 120
  review: 90
  synthesis: 180
```

---

## How to Run the Demo

### On Each Council Node Machine

1. **Start the council node service:**
   ```bat
   set NODE_ID=council-5
   set NODE_NAME=Qwen Analyst (Wendy)
   set MODEL_NAME=qwen2:1.5b
   set OLLAMA_URL=http://localhost:11434

   python -m uvicorn council_node.main:app --host 0.0.0.0 --port 5001
   ```

2. **Verify it's running:**
   ```bat
   curl http://localhost:5001/health
   ```

### On the Main Machine (Chairman + Orchestrator)

Open **two separate terminals**:

**Terminal 1 — Chairman service:**
```bat
python -m uvicorn chairman.main:app --host 0.0.0.0 --port 9000
```

**Terminal 2 — Orchestrator + UI:**
```bat
python -m uvicorn orchestrator.main:app --host 0.0.0.0 --port 8080
# Open: http://localhost:8080 in browser
```

### Using the Web UI

Once all services are running, open `http://localhost:8080` and you can:
- ✅ Run **Stage 1** only (opinions generation)
- ✅ Run **Stage 2** only (reviews & ranking)
- ✅ Run **Stage 3** only (synthesis)
- ✅ Run the **complete workflow** end-to-end
- ✅ View node health status

---

## Testing & Verification

### Node Health Checks

After starting services, verify each node is healthy:

```bash
# Local health check (on the node machine)
curl http://localhost:5001/health

# Remote health check (from another machine)
curl http://100.xxx.xxx.xxx:5001/health
```

Expected response:
```json
{
  "status": "healthy",
  "node_id": "council-1",
  "ollama_status": "ready"
}
```

### Full System Validation Checklist

- [ ] All council nodes respond to `/health` (HTTP 200)
- [ ] All council nodes respond to `/opinion` endpoint
- [ ] All council nodes respond to `/review` endpoint
- [ ] Chairman responds to `/health` (HTTP 200)
- [ ] Chairman responds to `/synthesize` endpoint
- [ ] Orchestrator UI shows all nodes as **online**
- [ ] **Stage 1 test**: Generate opinions from all nodes
- [ ] **Stage 2 test**: Generate reviews from all nodes
- [ ] **Stage 3 test**: Generate synthesis from chairman
- [ ] **Fallback test**: Disable one node and verify system still works (requires `min_council_members: 2`)

---
```
```

## Screenshots (UI + Swagger)

### UI — Home & System Status

![Home page](images/Home_page.jpg)
![UI Home — System status](images/ui_home_system_status.jpg)

### UI — Stage 1 (Opinions)

![UI Stage 1 — Opinions](images/ui_stage1_opinions.jpg)
![Stage 1 page](images/Stage-1-page.jpg)

### UI — Stage 2 (Reviews & Ranking)

![UI Stage 2 — Reviews ranking](images/ui_stage2_reviews_ranking.jpg)

### UI — Stage 3 (Chairman Synthesis)

![Stage 3 page](images/Stage-3-page.jpg)

### Swagger — API Validation (Council Node)

![Swagger endpoints council-1](images/swagger_endpoints_council-1.jpg)
![Swagger /answer request body](images/swagger_answer_request_body.jpg)
![Swagger /answer success response](images/swagger_answer_success_response.jpg)
![Swagger responses (200 / 422)](images/swagger_responses_200_422.jpg)

```

---

## Technical Architecture

### Key Design Decisions

#### 1) Microservices Architecture (FastAPI)

- Each council member is a separate FastAPI service (`council_node`)
- The chairman is a separate service (`chairman`)
- The orchestrator coordinates all services (`orchestrator`) and exposes a unified entry point for the UI

#### 2) Local Inference with Ollama

- Each node calls the local Ollama API (`/api/generate`)
- Models are configured per node via environment variables and `config.yaml`

#### 3) Health Monitoring

- Every service exposes `GET /health`
- The orchestrator periodically checks each node's status:
  - **Reachable**: responds with HTTP 200
  - **Offline**: marked with reason (timeout / connection refused / etc.)

**What "health OK" means:**
When you see "health OK" or "healthy" in logs, it indicates:
- FastAPI is responding correctly
- On council nodes specifically: Ollama is reachable and the configured model is available
- Status can be `"healthy"` (when `ollama_status == "ready"`) or `"degraded"` (partially functional)

#### 4) Graceful Degradation (Fallback)

- If some nodes are offline, the orchestrator continues operation as long as minimum nodes are available:
  - Configured via `fallback.min_council_members = 2` (at least 2 nodes required)

#### 5) JSON Review Output (Robust Parsing)

- Stage 2 outputs structured JSON with:
  - `scores` per opinion (accuracy + insight dimensions)
  - `ranking` ordered list of opinions
- The council node includes robust JSON parsing:
  - Extracts JSON even if LLM adds surrounding text
  - Normalizes missing/invalid scores to valid `[0..10]` range

---

### Selected LLM Models

**Council nodes** (from `config.yaml`):
- `llama3.2:1b` — Fast, good reasoning
- `phi3:mini` — Lightweight, efficient
- `smollm2:135m` — Very small, instant inference
- `qwen2.5:0.5b` — Quantized, low latency
- `qwen2:1.5b` — Balanced performance

**Chairman**:
- `llama3.2:3b` — Stronger synthesis capabilities

### Model Selection Rationale

Our objective was to build a distributed LLM council on consumer laptops while maintaining full local inference (Ollama). The selected models balance **speed, hardware constraints, and reasoning diversity**:

- **Small council models**: Enable fast inference on laptops, reduce request timeouts, facilitate parallelization across Stage 1 and Stage 2
- **Model diversity**: Using different families (Llama / Phi / SmolLM / Qwen) increases reasoning variety and reduces correlated errors
- **Stronger chairman**: `llama3.2:3b` improves synthesis coherence and conflict resolution across multiple opinions and reviews

---

### Response Storage

The orchestrator stores all data **in-memory** using a Python dictionary:

```python
queries: Dict[str, QueryResponse] = {}
```

For each `query_id`, it stores:
- `opinions` — dict keyed by `node_id` (content + model + timing)
- `reviews` — dict keyed by `node_id` (JSON scores + raw output + timing)
- `final_answer` — chairman's synthesized response
- `status`, `timing`, `nodes_used`, `error` (if applicable)

This satisfies the project requirement of storing responses in a structured dictionary.

⚠️ **Limitation**: Storage is **not persistent** — restarting the orchestrator clears all data. A production system would use a database.

---

## Project Structure

```text
Gen-AI-main/
├── README.md
├── config.yaml
├── chairman/
│   └── main.py
├── council_node/
│   └── main.py
├── orchestrator/
│   └── main.py
├── common/
│   ├── config.py
│   ├── http_client.py
│   └── logging_config.py
├── frontend/
│   └── index.html
└── images/
    └── (screenshots here)
```

---

## Team Responsibilities

| Role      | Team Member    | Machine  | Services Running                          | Responsibility                     |
| --------- | -------------- | -------- | ----------------------------------------- | ---------------------------------- |
| Student 1 | Cyprien Mouton | Laptop A | Council Node                              | Stage 1 opinions + Stage 2 reviews |
| Student 2 | Lisa Naccache  | Laptop B | Council Node                              | Stage 1 opinions + Stage 2 reviews |
| Student 3 | Neil Mahcer    | Laptop C | Council Node                              | Stage 1 opinions + Stage 2 reviews |
| Student 4 | Hiba Nejjari   | Laptop D | Orchestrator + Chairman (+ optional node) | Coordination + Stage 3 synthesis   |
| Student 5 | Wendy Duong    | Laptop E | Council Node                              | Stage 1 opinions + Stage 2 reviews |

```

---

## Generative AI Usage Statement

Generative AI tools (LLMs) were **explicitly allowed** for this project and were used **throughout development**.

### Tools & Models Used
- **Local LLMs** via Ollama (council & chairman models listed in configuration)
- **LLM assistants** (ChatGPT, Copilot) for engineering support and documentation

### Usage Purpose
Generative AI was applied for:
- **Debugging** (error interpretation, hypothesis generation, troubleshooting)
- **Code generation** (boilerplate, API endpoints, configuration templates)
- **Documentation** (README, API specifications, inline comments)
- **Application design** decisions (architecture suggestions, workflow design, UI ideas)
- **Code refactoring** (naming, structure, readability, consistency)
- **Documentation quality** improvements

### Transparency
We declare this usage to comply with the course policy: **transparency is mandatory**.  
No attempt was made to hide LLM usage, and its role was to assist the team in development and documentation.
