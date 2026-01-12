#!/bin/bash
# =============================================================================
# start_local.sh - Start all LLM Council services on a single machine
# =============================================================================
# Use this script for:
#   - Local development
#   - Testing the full workflow
#   - Emergency fallback during demo if LAN fails
#
# Prerequisites:
#   - Ollama installed and running
#   - Model pulled: ollama pull llama3.2:1b
#   - Python dependencies installed
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        LLM Council - Local Startup Script                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Configuration
MODEL="${MODEL_NAME:-llama3.2:1b}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

# Check Ollama is running
echo -e "${YELLOW}Checking Ollama status...${NC}"
if curl -s "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama is running${NC}"
else
    echo -e "${RED}✗ Ollama is not running!${NC}"
    echo "  Start Ollama with: ollama serve"
    exit 1
fi

# Check models are available
echo -e "${YELLOW}Checking model availability...${NC}"

MODELS_NEEDED=("llama3.2:1b" "qwen2:1.5b" "phi3:mini" "llama3.2:3b")
MODELS_MISSING=()

for model in "${MODELS_NEEDED[@]}"; do
    base_model="${model%%:*}"
    if curl -s "$OLLAMA_URL/api/tags" | grep -q "$base_model"; then
        echo -e "${GREEN}✓ Model $model is available${NC}"
    else
        echo -e "${RED}✗ Model $model not found!${NC}"
        MODELS_MISSING+=("$model")
    fi
done

if [ ${#MODELS_MISSING[@]} -gt 0 ]; then
    echo -e "${RED}Missing models! Pull them with:${NC}"
    for m in "${MODELS_MISSING[@]}"; do
        echo "  ollama pull $m"
    done
    echo ""
    echo -e "${YELLOW}Continuing anyway (will fail for missing models)...${NC}"
fi

# Kill any existing instances
echo -e "${YELLOW}Cleaning up existing processes...${NC}"
pkill -f "uvicorn council_node.main" 2>/dev/null || true
pkill -f "uvicorn chairman.main" 2>/dev/null || true
pkill -f "uvicorn orchestrator.main" 2>/dev/null || true
sleep 2

# Create logs directory
mkdir -p logs

echo ""
echo -e "${BLUE}Starting services...${NC}"
echo ""

# Start Council Node 1 - LLAMA
echo -e "${YELLOW}Starting Council Node 1 (Llama) on port 5001...${NC}"
NODE_ID=council-1 NODE_NAME="Llama Analyst" MODEL_NAME=llama3.2:1b PORT=5001 \
    python -m uvicorn council_node.main:app --host 0.0.0.0 --port 5001 \
    > logs/council-1.log 2>&1 &
echo -e "${GREEN}✓ Council Node 1 (Llama) started (PID: $!)${NC}"

# Start Council Node 2 - QWEN
echo -e "${YELLOW}Starting Council Node 2 (Qwen) on port 5002...${NC}"
NODE_ID=council-2 NODE_NAME="Qwen Analyst" MODEL_NAME=qwen2:1.5b PORT=5002 \
    python -m uvicorn council_node.main:app --host 0.0.0.0 --port 5002 \
    > logs/council-2.log 2>&1 &
echo -e "${GREEN}✓ Council Node 2 (Qwen) started (PID: $!)${NC}"

# Start Council Node 3 - PHI
echo -e "${YELLOW}Starting Council Node 3 (Phi) on port 5003...${NC}"
NODE_ID=council-3 NODE_NAME="Phi Analyst" MODEL_NAME=phi3:mini PORT=5003 \
    python -m uvicorn council_node.main:app --host 0.0.0.0 --port 5003 \
    > logs/council-3.log 2>&1 &
echo -e "${GREEN}✓ Council Node 3 (Phi) started (PID: $!)${NC}"

# Start Chairman - LLAMA 3B (bigger model)
echo -e "${YELLOW}Starting Chairman (Llama 3B) on port 9000...${NC}"
CHAIRMAN_ID=chairman MODEL_NAME=llama3.2:3b PORT=9000 \
    python -m uvicorn chairman.main:app --host 0.0.0.0 --port 9000 \
    > logs/chairman.log 2>&1 &
echo -e "${GREEN}✓ Chairman (Llama 3B) started (PID: $!)${NC}"

# Wait for services to start
echo ""
echo -e "${YELLOW}Waiting for services to initialize...${NC}"
sleep 5

# Start Orchestrator
echo -e "${YELLOW}Starting Orchestrator on port 8080...${NC}"
CONFIG_FILE=config.yaml \
    python -m uvicorn orchestrator.main:app --host 0.0.0.0 --port 8080 \
    > logs/orchestrator.log 2>&1 &
echo -e "${GREEN}✓ Orchestrator started (PID: $!)${NC}"

sleep 3

# Health check
echo ""
echo -e "${BLUE}Running health checks...${NC}"
echo ""

check_service() {
    local name=$1
    local url=$2
    if curl -s "$url/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $name is healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ $name is not responding${NC}"
        return 1
    fi
}

check_service "Council Node 1" "http://localhost:5001"
check_service "Council Node 2" "http://localhost:5002"
check_service "Council Node 3" "http://localhost:5003"
check_service "Chairman" "http://localhost:9000"
check_service "Orchestrator" "http://localhost:8080"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              All services started!                       ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Orchestrator:  http://localhost:8080                    ║${NC}"
echo -e "${GREEN}║  Council Node 1: http://localhost:5001                   ║${NC}"
echo -e "${GREEN}║  Council Node 2: http://localhost:5002                   ║${NC}"
echo -e "${GREEN}║  Council Node 3: http://localhost:5003                   ║${NC}"
echo -e "${GREEN}║  Chairman:       http://localhost:9000                   ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Test with: python test_client.py                        ║${NC}"
echo -e "${GREEN}║  Logs in: ./logs/                                        ║${NC}"
echo -e "${GREEN}║  Stop with: ./scripts/stop_local.sh                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
