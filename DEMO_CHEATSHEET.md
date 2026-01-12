# 📋 DEMO DAY CHEAT SHEET (Print This!)

## 🔥 BEFORE ANYTHING - Pull Models

**Each person pulls THEIR model:**

| Person | Machine | Command |
|--------|---------|---------|
| Person 2 | Laptop B | `ollama pull llama3.2:1b` |
| Person 3 | Laptop C | `ollama pull qwen2:1.5b` |
| Person 4 | Laptop D | `ollama pull phi3:mini` |
| Person 5 | Laptop E | `ollama pull llama3.2:3b` |

---

## 🚀 Distributed Start Commands

**Laptop A (Orchestrator):**
```bash
cd llm-council
python -m uvicorn orchestrator.main:app --host 0.0.0.0 --port 8080
```

**Laptop B (Council 1 - Llama):**
```bash
cd llm-council
NODE_ID=council-1 MODEL_NAME=llama3.2:1b python -m uvicorn council_node.main:app --host 0.0.0.0 --port 5001
```

**Laptop C (Council 2 - Qwen):**
```bash
cd llm-council
NODE_ID=council-2 MODEL_NAME=qwen2:1.5b python -m uvicorn council_node.main:app --host 0.0.0.0 --port 5001
```

**Laptop D (Council 3 - Phi):**
```bash
cd llm-council
NODE_ID=council-3 MODEL_NAME=phi3:mini python -m uvicorn council_node.main:app --host 0.0.0.0 --port 5001
```

**Laptop E (Chairman - Llama 3B):**
```bash
cd llm-council
MODEL_NAME=llama3.2:3b python -m uvicorn chairman.main:app --host 0.0.0.0 --port 9000
```

---

## 🆘 If LAN Fails - Run Everything Locally

On ANY single laptop (needs ALL models):
```bash
ollama pull llama3.2:1b qwen2:1.5b phi3:mini llama3.2:3b
cd llm-council
./scripts/start_local.sh
```

Then open: `http://localhost:8080`

---

## Quick Health Check

**From orchestrator machine:**
```bash
python test_client.py --health
```

Expected output:
```
✓ Council Node 1 (Llama) is healthy
✓ Council Node 2 (Qwen) is healthy
✓ Council Node 3 (Phi) is healthy
✓ Chairman (Llama 3B) is healthy
System is ready
```

---

## 🔧 Fix Common Problems

### "Connection refused"
```bash
# Check firewall (Linux):
sudo ufw allow 5001
sudo ufw allow 8080
sudo ufw allow 9000

# Windows: run as admin
netsh advfirewall firewall add rule name="LLM" dir=in action=allow protocol=TCP localport=5001,8080,9000
```

### "Model not found"
```bash
ollama pull <model_name>
ollama list  # verify it's there
```

### "Timeout"
- Models need time to load first response (30-60s)
- Second query is faster

---

## 📝 IP Address Sheet - FILL THIS IN

```
Network SSID: _____________________

Laptop A (Orchestrator):  ___.___.___.___ :8080
Laptop B (Council-Llama): ___.___.___.___ :5001
Laptop C (Council-Qwen):  ___.___.___.___ :5001
Laptop D (Council-Phi):   ___.___.___.___ :5001
Laptop E (Chairman):      ___.___.___.___ :9000

Web UI: http://___.___.___.___ :8080
```

Find your IP:
- Linux/Mac: `hostname -I | awk '{print $1}'`
- Windows: `ipconfig | findstr IPv4`

---

## 🎯 Demo Questions (Tested)

1. "What is an API?"
2. "Explain the difference between HTTP and HTTPS"
3. "What is a database index?"

---

## ✅ Success = Different Answers!

Each model responds differently:
- **Llama**: Balanced, detailed
- **Qwen**: Concise, technical
- **Phi**: Simple, clear

Chairman combines the best parts → Final answer
