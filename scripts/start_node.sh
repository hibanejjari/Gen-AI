#!/bin/bash
# =============================================================================
# start_node.sh - Start a single LLM Council node on this machine
# =============================================================================
# Use this script on each machine in a distributed deployment.
#
# Usage:
#   NODE_TYPE=council NODE_ID=council-1 ./scripts/start_node.sh
#   NODE_TYPE=chairman ./scripts/start_node.sh
#   NODE_TYPE=orchestrator ./scripts/start_node.sh
#
# Environment variables:
#   NODE_TYPE       - "council", "chairman", or "orchestrator"
#   NODE_ID         - Unique ID (e.g., "council-1", "council-2")
#   NODE_NAME       - Display name (optional)
#   MODEL_NAME      - Ollama model to use (default: llama3.2:1b)
#   PORT            - Port to bind (default: depends on type)
#   HOST            - Host to bind (default: 0.0.0.0)
#   CONFIG_FILE     - Config file path (orchestrator only)
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Defaults
NODE_TYPE="${NODE_TYPE:-council}"
MODEL_NAME="${MODEL_NAME:-llama3.2:1b}"
HOST="${HOST:-0.0.0.0}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

# Determine port and service based on type
case $NODE_TYPE in
    council)
        PORT="${PORT:-5001}"
        NODE_ID="${NODE_ID:-council-1}"
        NODE_NAME="${NODE_NAME:-Council Member}"
        SERVICE="council_node.main:app"
        ;;
    chairman)
        PORT="${PORT:-9000}"
        NODE_ID="${NODE_ID:-chairman}"
        NODE_NAME="${NODE_NAME:-Chairman}"
        SERVICE="chairman.main:app"
        ;;
    orchestrator)
        PORT="${PORT:-8080}"
        SERVICE="orchestrator.main:app"
        ;;
    *)
        echo -e "${RED}Invalid NODE_TYPE: $NODE_TYPE${NC}"
        echo "Valid types: council, chairman, orchestrator"
        exit 1
        ;;
esac

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        LLM Council - Node Startup                        ║"
echo "╠══════════════════════════════════════════════════════════╣"
printf "║  Type:    %-46s ║\n" "$NODE_TYPE"
printf "║  ID:      %-46s ║\n" "${NODE_ID:-N/A}"
printf "║  Model:   %-46s ║\n" "$MODEL_NAME"
printf "║  Host:    %-46s ║\n" "$HOST"
printf "║  Port:    %-46s ║\n" "$PORT"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check Ollama for council/chairman nodes
if [ "$NODE_TYPE" != "orchestrator" ]; then
    echo -e "${YELLOW}Checking Ollama...${NC}"
    if curl -s "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Ollama is running${NC}"
    else
        echo -e "${RED}✗ Ollama is not running!${NC}"
        echo "  Start with: ollama serve"
        exit 1
    fi
    
    # Check model
    if curl -s "$OLLAMA_URL/api/tags" | grep -q "${MODEL_NAME%%:*}"; then
        echo -e "${GREEN}✓ Model $MODEL_NAME available${NC}"
    else
        echo -e "${RED}✗ Model $MODEL_NAME not found!${NC}"
        echo "  Pull with: ollama pull $MODEL_NAME"
        exit 1
    fi
fi

# Get this machine's IP for display
IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo -e "${GREEN}Starting $NODE_TYPE on $HOST:$PORT...${NC}"
echo -e "${GREEN}Other machines can reach this at: http://$IP_ADDR:$PORT${NC}"
echo ""

# Export environment variables and start service
export NODE_ID
export NODE_NAME
export MODEL_NAME
export HOST
export PORT
export OLLAMA_URL
export CONFIG_FILE

# Run with uvicorn
python -m uvicorn $SERVICE --host $HOST --port $PORT
