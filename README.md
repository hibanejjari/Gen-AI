# LLM Council : Local Distributed Deployment

A distributed system where multiple local LLMs collaborate through a 3-stage council process to answer questions.


## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [3-Stage Workflow](#3-stage-workflow)
3. [Requirements Compliance](#requirements-compliance)
4. [Quick Start](#quick-start)
5. [Configuration Guide](#configuration-guide)
6. [Testing Strategy](#testing-strategy)
7. [Project Structure](#project-structure)
8. [Team Responsibilities](#team-responsibilities)

## Architecture-overview
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
│  - council_node/main.py   (5002)                                              │
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

### 3-Stage Workflow
---
| Stage | Description | Endpoint |
|-------|-------------|----------|
| **1. First Opinions** | Each council node generates independent answer | `POST /opinion` |
| **2. Review & Ranking** | Each node reviews others' answers anonymously | `POST /review` |
| **3. Chairman Synthesis** | Chairman combines insights into final answer | `POST /synthesize` |

---

##  Requirements Compliance
---
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

## How to start

### Prerequisites

1. **Python 3.10+** on all machines
2. **Ollama** installed on all machines
3. **Model pulled** on all machines:
for example
   ```bash
   ollama pull llama3.2:1b
   ```
4. Have Tailsca;e installed and be connected on the same account

### On all Machines

```bash
#  Clone/copy the project
cd llm-council

# Install dependencies
pip install -r requirements.txt
pip install fastapi uvicorn requests

# Start all services
( for example )
---
set NODE_ID=council-5
set NODE_NAME=Qwen Analyst (wendy)
set MODEL_NAME=qwen2:1.5b
set OLLAMA_URL=http://localhost:11434
python -m uvicorn council_node.main:app --host 0.0.0.0 --port 5001
---
 on each machine

# then on main pc open web UI
---
python -m uvicorn chairman.main:app --host 0.0.0.0 --port 9000
---
and other terminal :
---
python -m uvicorn orchestrator.main:app --host 0.0.0.0 --port 8080
# Open http://localhost:8080 in browser
```


## Configuration Guide
### Finding the IP Addresses first
### YAML Configuration 
<img width="1619" height="832" alt="image" src="https://github.com/user-attachments/assets/bede5b4b-84a0-4c22-8ede-de8ab860c9f0" />

Edit `config.yaml`:

```yaml
orchestrator:
  host: "0.0.0.0"
  port: 8080

council_nodes:
  - id: "council-1"
    url: "http://192.168.1.101:5001"  # Change to actual IP
    model: "llama3.2:1b"
    
  - id: "council-2"
    url: "http://192.168.1.102:5001"
    model: "llama3.2:1b"
    
  - id: "council-3"
    url: "http://192.168.1.103:5001"
    model: "llama3.2:1b"

chairman:
  url: "http://192.168.1.104:9000"    # Must be different machine
  model: "llama3.2:1b"

timeouts:
  health_check: 5
  opinion: 120
  review: 90
  synthesis: 180

fallback:
  min_council_members: 2  # Can run with 2 if 1 fails
```
What we first did : 


`Then :
### Individual Node Testing

On each node machine:
```bash
# Start the node
NODE_TYPE=council NODE_ID=council-1 ./scripts/start_node.sh

# In another terminal, test locally
curl http://localhost:5001/health

# Test from another machine
curl http://<this-machine-ip>:5001/health
```
<img width="1600" height="628" alt="image" src="https://github.com/user-attachments/assets/cb589381-8561-49d9-a78f-2c7eb6d2fa69" />
<img width="1600" height="828" alt="image" src="https://github.com/user-attachments/assets/d7bdf825-7d3c-4e68-aea5-46bd50c2f0d9" />

Then executing on main machine.

### Test Checklist

- [ ] Each council node responds to `/health`
- [ ] Each council node responds to `/opinion`
- [ ] Each council node responds to `/review`
- [ ] Chairman responds to `/health`
- [ ] Chairman responds to `/synthesize`
- [ ] Orchestrator shows all nodes healthy
- [ ] Full workflow completes without timeout
- [ ] System works with one node disabled (fallback)

---

In conclusion : 

## Project Structure

```
llm-council/
├── README.md               
├── requirements.txt             # Python dependencies
├── config.yaml                  # Main configuration
├── config.distributed.yaml      # Template for distributed
│
├── orchestrator/
│   └── main.py                  # Orchestrator service
│
├── council_node/
│   └── main.py                  # Council member service
│
├── chairman/
│   └── main.py                  # Chairman service
│
├── common/
│   ├── __init__.py
│   ├── config.py                # Configuration management
│   ├── http_client.py           # HTTP with timeouts/retries
│   └── logging_config.py        # Logging setup
│
├── frontend/
│   └── index.html               # Web UI
│



---

## Team Responsibilities

| Role      | Team Member | Machine  | Services Running                                    | Responsibility                                                                                               |
| --------- | ----------- | -------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Student 1 | Cyprien     | Laptop A | Council Node (Llama Analyst)                        | Runs a council LLM, participates in Stage 1 and Stage 2                                                      |
| Student 2 | Lisa        | Laptop B | Council Node (Phi Analyst)                          | Runs a council LLM, participates in Stage 1 and Stage 2                                                      |
| Student 3 | Neil        | Laptop C | Council Node (Smollm Analyst)                       | Runs a council LLM, participates in Stage 1 and Stage 2                                                      |
| Student 4 | Hiba        | Laptop D | Council Node (Qwen Small) + Orchestrator + Chairman | Central coordination, runs the orchestrator (Stage 0), runs a council node, and hosts the Chairman (Stage 3) |
| Student 5 | Wendy       | Laptop E | Council Node (Qwen Analyst)                         | Runs a council LLM, participates in Stage 1 and Stage 2                                                      |




