# LLM Council - Local Distributed Deployment

A distributed system where multiple local LLMs collaborate through a 3-stage council process to answer questions.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Requirements Compliance](#requirements-compliance)
3. [Quick Start](#quick-start)
4. [Configuration Guide](#configuration-guide)
5. [Networking Guide](#networking-guide)
6. [Testing Strategy](#testing-strategy)
7. [Demo Checklist](#demo-checklist)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview
```
LLM Council (5 people, distributed with Tailscale)

LEGEND
- Each "PC" runs its own Ollama + one FastAPI service per model
- Orchestrator PC is the single entry point for the UI and workflow
- All inter-PC communication is REST over Tailscale IPs (http://100.x.x.x:PORT)

┌──────────────────────────────────────────────────────────────────────────────┐
│ PC: HIBA (Orchestrator + UI + Chairman + one council node)                   │
│ WHY THIS PC:                                                                 │
│ - Central entry point (frontend + orchestrator)                              │
│ - Runs Chairman                                  │
│ - Hosts an extra council node                                  │
│ RUNS:                                                                        │
│  1) frontend/index.html                                                      │        │
│  2) orchestrator/main.py  (port 8080)                                        │
│     coordinates workflow, calls all nodes, health checks, aggregates    │
│  3) chairman/main.py      (port 9000)                                        │
│     synthesizes final answer only           │
│  4) council node 4 ( extra : port 5002)                              │
│     adds diversity            │
└───────────────┬──────────────────────────────────────────────────────────────┘
                │  REST calls (Tailscale network)
                │  Stage 1: POST /opinion  → collect answers
                │  Stage 2: POST /review   → collect anonymized scoring
                │  Stage 3: POST /synthesize → final answer
                ▼
 all on ollama :
┌──────────────────────────────────────────────────────────────────────────────┐
│ PC: CYPRIEN (Council Node 1)                                                 │)                               │
│    council_node/main.py  (port 5001)                                        │
│    exposes /health /opinion /review endpoints for orchestrator         │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ PC: LISA-VIVO15 (Council Node 2)                                             │                                                            │
│ council_node/main.py  (port 5001)                                            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ PC: NEIL (Council Node 3)                                                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ PC: WENDY (Council Node 5                                                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘


HOW A FULL RUN HAPPENS (end-to-end)
1) User opens UI on HIBA PC (Orchestrator serves frontend)
2) UI sends POST /query to Orchestrator (HIBA, port 8080)
3) Stage 1: Orchestrator calls every healthy council node:
   - CYPRIEN /opinion
   - LISA   /opinion
   - NEIL   /opinion 
   - HIBA   /opinion
   - WENDY  /opinion
4) Stage 2: Orchestrator anonymizes answers (A,B,C,...) then calls /review on each node
5) Stage 3: Orchestrator sends anonymized answers + all review JSON to Chairman (HIBA, port 9000)
6) Chairman returns final synthesized answer → UI displays Stage 1, Stage 2, Stage 3 results
```

```

### 3-Stage Workflow

| Stage | Description | Endpoint |
|-------|-------------|----------|
| **1. First Opinions** | Each council node generates independent answer | `POST /opinion` |
| **2. Review & Ranking** | Each node reviews others' answers anonymously | `POST /review` |
| **3. Chairman Synthesis** | Chairman combines insights into final answer | `POST /synthesize` |

---

##  Requirements Compliance

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

## Quick Start

### Prerequisites

1. **Python 3.10+** on all machines
2. **Ollama** installed on all machines
3. **Model pulled** on all machines:
   ```bash
   ollama pull llama3.2:1b
   ```

### Single Machine (Development/Fallback)

```bash
#  Clone/copy the project
cd llm-council

# Install dependencies
pip install -r requirements.txt
pip install fastapi uvicorn requests

# Start all services
( for example )
set NODE_ID=council-5
set NODE_NAME=Qwen Analyst (wendy)
set MODEL_NAME=qwen2:1.5b
set OLLAMA_URL=http://localhost:11434
python -m uvicorn council_node.main:app --host 0.0.0.0 --port 5001
 on each machine

# then on main pc open web UI
python -m uvicorn chairman.main:app --host 0.0.0.0 --port 9000

and other terminal :

python -m uvicorn orchestrator.main:app --host 0.0.0.0 --port 8080
# Open http://localhost:8080 in browser
```


## Configuration Guide
### Finding the IP Addresses
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

**Windows:**
```powershell
netsh advfirewall firewall add rule name="LLM Council" dir=in action=allow protocol=TCP localport=5001,8080,9000
```

### Find Your IP Address


## 🧪 Testing Strategy

### Level 1: Local Testing (One Machine)

```bash
# Start all services locally
./scripts/start_local.sh

# Run health check
python test_client.py --health

# Run full workflow
python test_client.py "Explain what a database index is"

# Check logs
tail -f logs/*.log
```

### Level 2: LAN Testing (Before Demo)

```bash
# On orchestrator machine, discover nodes
python scripts/test_lan.py --info
python scripts/test_lan.py --discover

# Test specific node
python scripts/test_lan.py --test 192.168.1.101 --port 5001

# Test all configured nodes
python scripts/test_lan.py --test-all

# Full workflow test
python test_client.py --url http://192.168.1.100:8080 "Test question"
```

### Level 3: Individual Node Testing

On each node machine:
```bash
# Start the node
NODE_TYPE=council NODE_ID=council-1 ./scripts/start_node.sh

# In another terminal, test locally
curl http://localhost:5001/health

# Test from another machine
curl http://<this-machine-ip>:5001/health
```

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
to check : 

**On EACH machine:**
```bash
# 1. Check Ollama is running
curl http://localhost:11434/api/tags

# 2. Start the appropriate service
NODE_TYPE=<type> ./scripts/start_node.sh

# 3. Verify health
curl http://localhost:<port>/health
```



## 📁 Project Structure

```
llm-council/
├── README.md                    # This file
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

## Team Responsibilities Suggestion

| Role | Machine | Services | Responsibility |
|------|---------|----------|----------------|
| Student 1 | Laptop A | Orchestrator | Demo coordination, config |
| Student 2 | Laptop B | Council 1 | Node monitoring |
| Student 3 | Laptop C | Council 2 | Network troubleshooting |
| Student 4 | Laptop D | Council 3 | Backup fallback |
| Student 5 | Laptop E | Chairman | Final presentation |

---

