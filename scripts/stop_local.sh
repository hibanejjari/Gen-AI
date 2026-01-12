#!/bin/bash
# =============================================================================
# stop_local.sh - Stop all LLM Council services
# =============================================================================

echo "Stopping LLM Council services..."

pkill -f "uvicorn council_node.main" 2>/dev/null && echo "✓ Council nodes stopped" || echo "- No council nodes running"
pkill -f "uvicorn chairman.main" 2>/dev/null && echo "✓ Chairman stopped" || echo "- No chairman running"
pkill -f "uvicorn orchestrator.main" 2>/dev/null && echo "✓ Orchestrator stopped" || echo "- No orchestrator running"

echo ""
echo "All services stopped."
