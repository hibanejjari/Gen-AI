# 🔄 Migration Guide: Your Code → Improved Version

This document shows exactly how to migrate from your existing code to the improved version.

---

## File Mapping

| Your File | → | New File | Changes |
|-----------|---|----------|---------|
| `council_node/main.py` | → | `council_node/main.py` | +health improvements, +timeouts, +env config |
| `chairman/main.py` | → | `chairman/main.py` | +/health endpoint, +timeouts, +env config |
| `orchestrator/run_council.py` | → | `orchestrator/main.py` | **Script → FastAPI service** |
| (none) | → | `config.yaml` | **NEW**: All node URLs in one place |
| (none) | → | `common/` | **NEW**: Shared utilities |
| (none) | → | `frontend/index.html` | **NEW**: Web UI |
| (none) | → | `scripts/` | **NEW**: Startup scripts |
| (none) | → | `test_client.py` | **NEW**: CLI testing |

---

## Key Changes Explained

### 1. Your `/answer` endpoint is now `/opinion`

**Your code:**
```python
@app.post("/answer")
def answer(data: dict):
    question = data["question"]
```

**New code (backward compatible):**
```python
@app.post("/opinion")
def generate_opinion(request: OpinionRequest):
    # ... improved implementation

@app.post("/answer")  # Legacy support!
def generate_answer(data: dict):
    request = OpinionRequest(question=data.get("question", ""))
    return generate_opinion(request)
```

### 2. Your hardcoded nodes → config.yaml

**Your code:**
```python
NODES = {
    "node1": "http://localhost:8001",
    "node2": "http://localhost:8003",
}
```

**New code:**
```yaml
# config.yaml - edit this, not Python code!
council_nodes:
  - id: "council-1"
    url: "http://192.168.1.101:5001"  # Easy to change!
  - id: "council-2"
    url: "http://192.168.1.102:5001"
  - id: "council-3"
    url: "http://192.168.1.103:5001"
```

### 3. Your script → REST service

**Your code (must run manually):**
```bash
python run_council.py  # Runs once, exits
```

**New code (always available):**
```bash
# Start service
uvicorn orchestrator.main:app --host 0.0.0.0 --port 8080

# Call via REST from anywhere
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is an API?"}'
```

---

## Quick Migration Steps

### Step 1: Copy your project backup
```bash
cp -r your-project your-project-backup
```

### Step 2: Extract improved version
```bash
unzip llm-council-improved.zip
cd llm-council
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Edit config.yaml for your setup
```yaml
# For LOCAL testing (single machine):
council_nodes:
  - id: "council-1"
    url: "http://localhost:5001"
    model: "llama3.2:1b"  # Change to your model
  # ...

# For DISTRIBUTED demo, change to actual IPs:
  - id: "council-1"
    url: "http://192.168.1.101:5001"
```

### Step 5: Test locally
```bash
# Start all services on one machine
./scripts/start_local.sh

# Test
python test_client.py --health
python test_client.py "What is an API?"
```

---

## Endpoint Compatibility

| Your Endpoint | New Endpoint | Compatible? |
|---------------|--------------|-------------|
| `POST /answer` | `POST /answer` (legacy) | ✅ Yes |
| `POST /answer` | `POST /opinion` (new) | ✅ Both work |
| `POST /review` | `POST /review` | ✅ Yes |
| `GET /health` | `GET /health` | ✅ Yes (enhanced) |
| `GET /info` | `GET /info` | ✅ Yes |
| `POST /finalize` | `POST /finalize` (legacy) | ✅ Yes |
| `POST /finalize` | `POST /synthesize` (new) | ✅ Both work |

---

## What You Keep

Your core logic is preserved! The improvements add:
- Timeout protection
- Health monitoring
- Configuration file
- Graceful degradation
- Web UI
- Better error messages

Your prompts, anonymization logic, and workflow remain the same.
