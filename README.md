# 🎓 LLM Council - Local Distributed Deployment

A distributed system where multiple local LLMs collaborate through a 3-stage council process to answer questions.

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Requirements Compliance](#requirements-compliance)
3. [Quick Start](#quick-start)
4. [Configuration Guide](#configuration-guide)
5. [Networking Guide](#networking-guide)
6. [Testing Strategy](#testing-strategy)
7. [Demo Checklist](#demo-checklist)
8. [Troubleshooting](#troubleshooting)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR (:8080)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │   Health    │  │  Workflow   │  │   Config    │                 │
│  │  Monitor    │  │   Engine    │  │  Manager    │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
   │ Council     │     │ Council     │     │ Council     │
   │ Node 1      │     │ Node 2      │     │ Node 3      │
   │ :5001       │     │ :5002       │     │ :5003       │
   └─────────────┘     └─────────────┘     └─────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │    CHAIRMAN     │
                    │    :9000        │
                    │ (Separate Host) │
                    └─────────────────┘
```

### 3-Stage Workflow

| Stage | Description | Endpoint |
|-------|-------------|----------|
| **1. First Opinions** | Each council node generates independent answer | `POST /opinion` |
| **2. Review & Ranking** | Each node reviews others' answers anonymously | `POST /review` |
| **3. Chairman Synthesis** | Chairman combines insights into final answer | `POST /synthesize` |

---

## ✅ Requirements Compliance

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| No cloud APIs | ✅ | Uses Ollama locally |
| All LLMs run locally | ✅ | Ollama on each machine |
| REST communication | ✅ | FastAPI endpoints |
| 3-stage workflow | ✅ | Opinions → Reviews → Synthesis |
| At least 3 council LLMs | ✅ | Configurable, default 3 |
| Chairman separate service | ✅ | Dedicated FastAPI app |
| Chairman separate machine | ✅ | Designed for distributed |
| Health checks | ✅ | `/health` on all services |
| Timeouts & retries | ✅ | Configurable timeouts |
| Graceful degradation | ✅ | min_council_members = 2 |
| Dynamic configuration | ✅ | YAML config + env vars |

---

## 🚀 Quick Start

### Prerequisites

1. **Python 3.10+** on all machines
2. **Ollama** installed on all machines
3. **Model pulled** on all machines:
   ```bash
   ollama pull llama3.2:1b
   ```

### Single Machine (Development/Fallback)

```bash
# 1. Clone/copy the project
cd llm-council

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start all services
chmod +x scripts/*.sh
./scripts/start_local.sh

# 4. Test with CLI
python test_client.py "What is an API?"

# 5. Or open web UI
# Open http://localhost:8080 in browser
```

### Multi-Machine (Production Demo)

**Machine A - Orchestrator:**
```bash
NODE_TYPE=orchestrator ./scripts/start_node.sh
```

**Machine B - Council Node 1:**
```bash
NODE_TYPE=council NODE_ID=council-1 PORT=5001 ./scripts/start_node.sh
```

**Machine C - Council Node 2:**
```bash
NODE_TYPE=council NODE_ID=council-2 PORT=5001 ./scripts/start_node.sh
```

**Machine D - Council Node 3:**
```bash
NODE_TYPE=council NODE_ID=council-3 PORT=5001 ./scripts/start_node.sh
```

**Machine E - Chairman:**
```bash
NODE_TYPE=chairman ./scripts/start_node.sh
```

---

## ⚙️ Configuration Guide

### Option 1: YAML Configuration (Recommended)

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

### Option 2: Environment Variables (Quick Override)

```bash
# Override node URLs
export COUNCIL_NODE_1_URL=http://192.168.1.101:5001
export COUNCIL_NODE_2_URL=http://192.168.1.102:5001
export COUNCIL_NODE_3_URL=http://192.168.1.103:5001
export CHAIRMAN_URL=http://192.168.1.104:9000

# Override timeouts
export TIMEOUT_OPINION=180
export TIMEOUT_SYNTHESIS=240

# Override minimum nodes
export MIN_COUNCIL_MEMBERS=2
```

---

## 🌐 Networking Guide

### Critical Rule: Bind to 0.0.0.0

**❌ WRONG (localhost only):**
```bash
uvicorn main:app --host localhost --port 5001
# Other machines CANNOT connect!
```

**✅ CORRECT (LAN accessible):**
```bash
uvicorn main:app --host 0.0.0.0 --port 5001
# Other machines CAN connect!
```

### Recommended Port Scheme

| Service | Port | Example URL |
|---------|------|-------------|
| Orchestrator | 8080 | `http://192.168.1.100:8080` |
| Council Node 1 | 5001 | `http://192.168.1.101:5001` |
| Council Node 2 | 5001 | `http://192.168.1.102:5001` |
| Council Node 3 | 5001 | `http://192.168.1.103:5001` |
| Chairman | 9000 | `http://192.168.1.104:9000` |

### Firewall Configuration

**Linux (UFW):**
```bash
sudo ufw allow 5001
sudo ufw allow 8080
sudo ufw allow 9000
```

**Windows:**
```powershell
netsh advfirewall firewall add rule name="LLM Council" dir=in action=allow protocol=TCP localport=5001,8080,9000
```

### Find Your IP Address

**Linux/Mac:**
```bash
hostname -I | awk '{print $1}'
# or
ip addr show | grep "inet " | grep -v 127.0.0.1
```

**Windows:**
```cmd
ipconfig | findstr IPv4
```

### Mobile Hotspot Setup

If using a phone hotspot:
1. Connect all machines to the hotspot
2. Check assigned IPs (usually 192.168.43.x)
3. Update config.yaml with new IPs
4. Test connectivity with `python scripts/test_lan.py`

---

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

## 📋 Demo Preparation Checklist

### 1 Week Before Demo

- [ ] All team members have project code
- [ ] Ollama installed on all demo machines
- [ ] Models pulled on all machines (`ollama pull llama3.2:1b`)
- [ ] Test locally on each machine individually
- [ ] Document each machine's role and IP

### 1 Day Before Demo

- [ ] Gather all machines on same network
- [ ] Record all IP addresses
- [ ] Update `config.yaml` with correct IPs
- [ ] Run `./scripts/test_lan.py --test-all`
- [ ] Complete at least one full workflow
- [ ] Prepare emergency fallback (local mode)

### Demo Day - 30 Minutes Before

**On EACH machine:**
```bash
# 1. Check Ollama is running
curl http://localhost:11434/api/tags

# 2. Start the appropriate service
NODE_TYPE=<type> ./scripts/start_node.sh

# 3. Verify health
curl http://localhost:<port>/health
```

**On orchestrator machine:**
```bash
# Check all nodes
python test_client.py --health

# Expected output:
# ✓ Council Node 1 is healthy
# ✓ Council Node 2 is healthy
# ✓ Council Node 3 is healthy
# ✓ Chairman is healthy
# System is ready
```

### Emergency Fallback Procedure

If LAN fails during demo:
```bash
# On the best available machine:
./scripts/start_local.sh

# Everything runs locally on ports 5001-5003, 8080, 9000
python test_client.py "Your demo question"
```

---

## 🔧 Troubleshooting

### "Connection refused"

**Cause:** Service not running or bound to localhost

**Fix:**
```bash
# Check service is running
ps aux | grep uvicorn

# Make sure using 0.0.0.0
uvicorn main:app --host 0.0.0.0 --port 5001
```

### "Model not found"

**Cause:** Model not pulled in Ollama

**Fix:**
```bash
ollama pull llama3.2:1b
ollama list  # Verify model exists
```

### "Timeout"

**Cause:** Model too slow or network latency

**Fix:**
1. Increase timeouts in config.yaml
2. Use smaller model (`:1b` instead of `:3b`)
3. Check network with ping

### "Not enough council members"

**Cause:** Less than min_council_members healthy

**Fix:**
1. Check health: `python test_client.py --health`
2. Fix unhealthy nodes
3. Or lower `min_council_members` to 2 in config

### "Ollama not running"

**Fix:**
```bash
# Start Ollama
ollama serve

# Or on Linux with systemd
sudo systemctl start ollama
```

---

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
├── scripts/
│   ├── start_local.sh           # Start all locally
│   ├── stop_local.sh            # Stop all services
│   ├── start_node.sh            # Start single node
│   └── test_lan.py              # LAN testing utility
│
├── tests/
│   └── test_health.py           # Health check tests
│
└── test_client.py               # CLI test client
```

---

## 👥 Team Responsibilities Suggestion

| Role | Machine | Services | Responsibility |
|------|---------|----------|----------------|
| Student 1 | Laptop A | Orchestrator | Demo coordination, config |
| Student 2 | Laptop B | Council 1 | Node monitoring |
| Student 3 | Laptop C | Council 2 | Network troubleshooting |
| Student 4 | Laptop D | Council 3 | Backup fallback |
| Student 5 | Laptop E | Chairman | Final presentation |

---

## 📄 License

MIT License - University Project
