"""
Orchestrator Service - Central coordination for LLM Council.

The Orchestrator:
1. Monitors health of all council nodes and chairman
2. Coordinates the 3-stage workflow
3. Handles failures gracefully with fallback modes
4. Provides API for frontend/client queries

Run with: uvicorn orchestrator.main:app --host 0.0.0.0 --port 8080
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Optional, List, Any
from datetime import datetime
from enum import Enum
import asyncio
import requests
import threading
import time
import os
import yaml
import uuid

# Configuration
CONFIG_FILE = os.getenv("CONFIG_FILE", "config.yaml")
ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", "8080"))


app = FastAPI(
    title="LLM Council Orchestrator",
    description="Central coordination service for LLM Council",
    version="2.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Configuration ==============

class NodeConfig:
    def __init__(self, id: str, url: str, model: str = "llama3.2:1b", 
                 name: str = None, enabled: bool = True):
        self.id = id
        self.url = url.rstrip('/')
        self.model = model
        self.name = name or id
        self.enabled = enabled
        self.healthy = False
        self.last_check = None
        self.error = None


class Config:
    def __init__(self):
        self.council_nodes: List[NodeConfig] = []
        self.chairman: Optional[NodeConfig] = None
        self.timeouts = {
            "health_check": 5,
            "opinion": 120,
            "review": 90,
            "synthesis": 180,
            "retry_delay": 2,
            "max_retries": 3
        }
        self.fallback = {
            "min_council_members": 2,
            "enable_local_fallback": True
        }
        
    def load_from_yaml(self, filepath: str):
        """Load configuration from YAML file."""
        if not os.path.exists(filepath):
            print(f"⚠️  Config file {filepath} not found, using defaults")
            self._set_defaults()
            return
            
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Load council nodes
        for node_data in data.get('council_nodes', []):
            self.council_nodes.append(NodeConfig(
                id=node_data.get('id'),
                url=node_data.get('url'),
                model=node_data.get('model', 'llama3.2:1b'),
                name=node_data.get('name'),
                enabled=node_data.get('enabled', True)
            ))
        
        # Load chairman
        if 'chairman' in data:
            ch = data['chairman']
            self.chairman = NodeConfig(
                id=ch.get('id', 'chairman'),
                url=ch.get('url'),
                model=ch.get('model', 'llama3.2:1b'),
                name=ch.get('name', 'Chairman')
            )
        
        # Load timeouts
        if 'timeouts' in data:
            self.timeouts.update(data['timeouts'])
        
        # Load fallback settings
        if 'fallback' in data:
            self.fallback.update(data['fallback'])
    
    def _set_defaults(self):
        """Set default configuration for local development."""
        self.council_nodes = [
            NodeConfig("council-1", "http://localhost:5001", "llama3.2:1b", "Analyst Alpha"),
            NodeConfig("council-2", "http://localhost:5002", "llama3.2:1b", "Analyst Beta"),
            NodeConfig("council-3", "http://localhost:5003", "llama3.2:1b", "Analyst Gamma"),
        ]
        self.chairman = NodeConfig("chairman", "http://localhost:9000", "llama3.2:1b", "Chairman")
    
    def load_from_env(self):
        """Override config with environment variables."""
        # Override node URLs from env
        for i, node in enumerate(self.council_nodes, 1):
            env_url = os.getenv(f"COUNCIL_NODE_{i}_URL")
            if env_url:
                node.url = env_url
        
        # Override chairman URL
        chairman_url = os.getenv("CHAIRMAN_URL")
        if chairman_url and self.chairman:
            self.chairman.url = chairman_url
        
        # Override timeouts
        for key in self.timeouts:
            env_key = f"TIMEOUT_{key.upper()}"
            if os.getenv(env_key):
                self.timeouts[key] = int(os.getenv(env_key))
        
        # Override fallback settings
        if os.getenv("MIN_COUNCIL_MEMBERS"):
            self.fallback["min_council_members"] = int(os.getenv("MIN_COUNCIL_MEMBERS"))


# Global configuration
config = Config()


# ============== Request/Response Models ==============

class QueryRequest(BaseModel):
    question: str
    timeout_override: Optional[int] = None


class QueryStatus(str, Enum):
    PENDING = "pending"
    STAGE_1 = "stage_1_opinions"
    STAGE_2 = "stage_2_reviews"
    STAGE_3 = "stage_3_synthesis"
    COMPLETED = "completed"
    FAILED = "failed"


class QueryResponse(BaseModel):
    query_id: str
    status: QueryStatus
    question: str
    opinions: Optional[Dict[str, Any]] = None
    reviews: Optional[Dict[str, Any]] = None
    final_answer: Optional[str] = None
    error: Optional[str] = None
    timing: Optional[Dict[str, float]] = None
    nodes_used: Optional[List[str]] = None


class HealthResponse(BaseModel):
    status: str
    orchestrator_version: str
    council_nodes: List[dict]
    chairman: Optional[dict]
    healthy_nodes: int
    min_required: int
    can_process: bool


class ConfigResponse(BaseModel):
    council_nodes: List[dict]
    chairman: Optional[dict]
    timeouts: dict
    fallback: dict


# Store for query results
queries: Dict[str, QueryResponse] = {}


# ============== Health Monitoring ==============

def check_node_health(node: NodeConfig) -> bool:
    """Check health of a single node."""
    try:
        response = requests.get(
            f"{node.url}/health",
            timeout=config.timeouts["health_check"]
        )
        if response.status_code == 200:
            node.healthy = True
            node.error = None
            node.last_check = datetime.now().isoformat()
            return True
        else:
            node.healthy = False
            node.error = f"HTTP {response.status_code}"
            node.last_check = datetime.now().isoformat()
            return False
    except requests.Timeout:
        node.healthy = False
        node.error = "Timeout"
        node.last_check = datetime.now().isoformat()
        return False
    except requests.ConnectionError as e:
        node.healthy = False
        node.error = "Connection refused"
        node.last_check = datetime.now().isoformat()
        return False
    except Exception as e:
        node.healthy = False
        node.error = str(e)
        node.last_check = datetime.now().isoformat()
        return False


def check_all_health():
    """Check health of all nodes."""
    for node in config.council_nodes:
        if node.enabled:
            check_node_health(node)
    
    if config.chairman:
        check_node_health(config.chairman)


def get_healthy_council_nodes() -> List[NodeConfig]:
    """Get list of healthy council nodes."""
    return [n for n in config.council_nodes if n.enabled and n.healthy]


# Background health checker
def health_check_loop():
    """Continuous health checking in background."""
    while True:
        check_all_health()
        time.sleep(10)  # Check every 10 seconds


# ============== Workflow Implementation ==============

def stage_1_collect_opinions(question: str, query_id: str) -> Dict[str, Any]:
    """
    Stage 1: Collect opinions from all healthy council nodes.
    """
    healthy_nodes = get_healthy_council_nodes()
    
    if len(healthy_nodes) < config.fallback["min_council_members"]:
        raise HTTPException(
            status_code=503,
            detail=f"Not enough healthy council nodes. Need {config.fallback['min_council_members']}, have {len(healthy_nodes)}"
        )
    
    opinions = {}
    nodes_used = []
    
    for node in healthy_nodes:
        try:
            response = requests.post(
                f"{node.url}/opinion",
                json={"question": question},
                timeout=config.timeouts["opinion"]
            )
            if response.status_code == 200:
                data = response.json()
                opinions[node.id] = {
                    "node_id": node.id,
                    "node_name": node.name,
                    "model": data.get("model", node.model),
                    "answer": data.get("answer", ""),
                    "generation_time_ms": data.get("generation_time_ms", 0)
                }
                nodes_used.append(node.id)
                print(f"✓ Opinion from {node.id}")
            else:
                print(f"✗ {node.id} returned HTTP {response.status_code}")
        except requests.Timeout:
            print(f"✗ {node.id} timed out")
        except Exception as e:
            print(f"✗ {node.id} error: {e}")
    
    if len(opinions) < config.fallback["min_council_members"]:
        raise HTTPException(
            status_code=503,
            detail=f"Not enough opinions collected. Need {config.fallback['min_council_members']}, got {len(opinions)}"
        )
    
    return {"opinions": opinions, "nodes_used": nodes_used}


def anonymize_opinions(opinions: Dict[str, Any]) -> tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """
    Anonymize opinions for peer review.
    
    Returns:
        - anon_opinions: {"A": "answer text", ...}
        - node_to_label: {"council-1": "A", ...}
        - label_to_node: {"A": "council-1", ...}
    """
    labels = ["A", "B", "C", "D", "E", "F", "G", "H"]
    
    anon_opinions = {}
    node_to_label = {}
    label_to_node = {}
    
    for i, (node_id, opinion_data) in enumerate(opinions.items()):
        if i >= len(labels):
            break
        label = labels[i]
        anon_opinions[label] = opinion_data["answer"]
        node_to_label[node_id] = label
        label_to_node[label] = node_id
    
    return anon_opinions, node_to_label, label_to_node


def stage_2_collect_reviews(
    question: str,
    anon_opinions: Dict[str, str],
    node_to_label: Dict[str, str],
    nodes_used: List[str]
) -> Dict[str, Any]:
    """
    Stage 2: Each council node reviews other nodes' opinions.
    
    Each node reviews all opinions EXCEPT their own (anonymous).
    """
    reviews = {}
    
    for node_id in nodes_used:
        node = next((n for n in config.council_nodes if n.id == node_id), None)
        if not node or not node.healthy:
            continue
        
        my_label = node_to_label.get(node_id)
        
        # Create responses dict excluding the reviewer's own answer
        responses_to_review = {
            label: text
            for label, text in anon_opinions.items()
            if label != my_label
        }
        
        if not responses_to_review:
            continue
        
        try:
            response = requests.post(
                f"{node.url}/review",
                json={
                    "question": question,
                    "responses": responses_to_review
                },
                timeout=config.timeouts["review"]
            )
            
            if response.status_code == 200:
                data = response.json()
                reviews[node_id] = {
                    "node_id": node_id,
                    "model": data.get("model", node.model),
                    "review": data.get("review", {}),
                    "generation_time_ms": data.get("generation_time_ms", 0)
                }
                print(f"✓ Review from {node_id}")
            else:
                print(f"✗ {node_id} review returned HTTP {response.status_code}")
        except requests.Timeout:
            print(f"✗ {node_id} review timed out")
        except Exception as e:
            print(f"✗ {node_id} review error: {e}")
    
    return reviews


def stage_3_synthesize(
    question: str,
    anon_opinions: Dict[str, str],
    reviews: Dict[str, Any]
) -> str:
    """
    Stage 3: Chairman synthesizes final answer.
    """
    if not config.chairman or not config.chairman.healthy:
        raise HTTPException(
            status_code=503,
            detail="Chairman is not available"
        )
    
    # Format reviews for chairman
    formatted_reviews = {}
    for node_id, review_data in reviews.items():
        if "review" in review_data:
            formatted_reviews[review_data.get("model", node_id)] = review_data["review"]
    
    try:
        response = requests.post(
            f"{config.chairman.url}/synthesize",
            json={
                "question": question,
                "answers": anon_opinions,
                "reviews": formatted_reviews
            },
            timeout=config.timeouts["synthesis"]
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("final_answer", "")
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Chairman returned error: {response.text}"
            )
    except requests.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Chairman synthesis timed out"
        )
    except requests.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Chairman"
        )


def run_full_workflow(question: str, query_id: str) -> QueryResponse:
    """
    Run the complete 3-stage workflow.
    """
    timing = {}
    
    # Update query status
    queries[query_id].status = QueryStatus.STAGE_1
    
    # Stage 1: Collect opinions
    print(f"\n{'='*50}")
    print(f"STAGE 1: Collecting Opinions")
    print(f"{'='*50}")
    start = time.time()
    
    result = stage_1_collect_opinions(question, query_id)
    opinions = result["opinions"]
    nodes_used = result["nodes_used"]
    
    timing["stage_1_ms"] = (time.time() - start) * 1000
    queries[query_id].opinions = opinions
    queries[query_id].nodes_used = nodes_used
    queries[query_id].status = QueryStatus.STAGE_2
    
    # Anonymize for review
    anon_opinions, node_to_label, label_to_node = anonymize_opinions(opinions)
    
    # Stage 2: Collect reviews
    print(f"\n{'='*50}")
    print(f"STAGE 2: Collecting Reviews")
    print(f"{'='*50}")
    start = time.time()
    
    reviews = stage_2_collect_reviews(question, anon_opinions, node_to_label, nodes_used)
    
    timing["stage_2_ms"] = (time.time() - start) * 1000
    queries[query_id].reviews = reviews
    queries[query_id].status = QueryStatus.STAGE_3
    
    # Stage 3: Chairman synthesis
    print(f"\n{'='*50}")
    print(f"STAGE 3: Chairman Synthesis")
    print(f"{'='*50}")
    start = time.time()
    
    final_answer = stage_3_synthesize(question, anon_opinions, reviews)
    
    timing["stage_3_ms"] = (time.time() - start) * 1000
    timing["total_ms"] = sum(timing.values())
    
    # Update final result
    queries[query_id].final_answer = final_answer
    queries[query_id].timing = timing
    queries[query_id].status = QueryStatus.COMPLETED
    
    print(f"\n{'='*50}")
    print(f"WORKFLOW COMPLETED")
    print(f"Total time: {timing['total_ms']:.0f}ms")
    print(f"{'='*50}\n")
    
    return queries[query_id]


# ============== API Endpoints ==============

@app.on_event("startup")
async def startup_event():
    """Initialize configuration and start health checker."""
    # Load configuration
    config.load_from_yaml(CONFIG_FILE)
    config.load_from_env()
    
    # If no config, set defaults
    if not config.council_nodes:
        config._set_defaults()
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║              LLM Council Orchestrator                    ║
╠══════════════════════════════════════════════════════════╣
║  Council Nodes: {len(config.council_nodes):<40} ║
║  Chairman:      {config.chairman.url if config.chairman else 'Not configured':<40} ║
║  Min Required:  {config.fallback['min_council_members']:<40} ║
╚══════════════════════════════════════════════════════════╝
""")
    
    # Initial health check
    check_all_health()
    
    # Start background health checker
    health_thread = threading.Thread(target=health_check_loop, daemon=True)
    health_thread.start()


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Get overall system health status."""
    # Refresh health status
    check_all_health()
    
    healthy_count = len(get_healthy_council_nodes())
    chairman_healthy = config.chairman and config.chairman.healthy
    
    can_process = (
        healthy_count >= config.fallback["min_council_members"] and
        chairman_healthy
    )
    
    return HealthResponse(
        status="healthy" if can_process else "degraded",
        orchestrator_version="2.0.0",
        council_nodes=[
            {
                "id": n.id,
                "name": n.name,
                "url": n.url,
                "model": n.model,
                "healthy": n.healthy,
                "error": n.error,
                "last_check": n.last_check
            }
            for n in config.council_nodes
        ],
        chairman={
            "id": config.chairman.id,
            "url": config.chairman.url,
            "model": config.chairman.model,
            "healthy": config.chairman.healthy,
            "error": config.chairman.error,
            "last_check": config.chairman.last_check
        } if config.chairman else None,
        healthy_nodes=healthy_count,
        min_required=config.fallback["min_council_members"],
        can_process=can_process
    )


@app.get("/council/status")
def council_status():
    """Get detailed status of all council nodes."""
    check_all_health()
    
    return {
        "council_nodes": [
            {
                "id": n.id,
                "name": n.name,
                "url": n.url,
                "model": n.model,
                "enabled": n.enabled,
                "healthy": n.healthy,
                "error": n.error,
                "last_check": n.last_check
            }
            for n in config.council_nodes
        ],
        "chairman": {
            "id": config.chairman.id,
            "url": config.chairman.url,
            "model": config.chairman.model,
            "healthy": config.chairman.healthy,
            "error": config.chairman.error,
            "last_check": config.chairman.last_check
        } if config.chairman else None,
        "summary": {
            "total_nodes": len(config.council_nodes),
            "healthy_nodes": len(get_healthy_council_nodes()),
            "chairman_healthy": config.chairman.healthy if config.chairman else False,
            "min_required": config.fallback["min_council_members"]
        }
    }


@app.post("/query", response_model=QueryResponse)
def submit_query(request: QueryRequest):
    """
    Submit a question to the council.
    
    This runs the full 3-stage workflow synchronously.
    For async processing, use /query/async.
    """
    query_id = str(uuid.uuid4())[:8]
    
    # Initialize query record
    queries[query_id] = QueryResponse(
        query_id=query_id,
        status=QueryStatus.PENDING,
        question=request.question
    )
    
    try:
        result = run_full_workflow(request.question, query_id)
        return result
    except HTTPException as e:
        queries[query_id].status = QueryStatus.FAILED
        queries[query_id].error = e.detail
        raise
    except Exception as e:
        queries[query_id].status = QueryStatus.FAILED
        queries[query_id].error = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/query/{query_id}", response_model=QueryResponse)
def get_query_result(query_id: str):
    """Get the result of a submitted query."""
    if query_id not in queries:
        raise HTTPException(status_code=404, detail="Query not found")
    return queries[query_id]


@app.get("/config", response_model=ConfigResponse)
def get_config():
    """Get current configuration."""
    return ConfigResponse(
        council_nodes=[
            {
                "id": n.id,
                "name": n.name,
                "url": n.url,
                "model": n.model,
                "enabled": n.enabled
            }
            for n in config.council_nodes
        ],
        chairman={
            "id": config.chairman.id,
            "url": config.chairman.url,
            "model": config.chairman.model
        } if config.chairman else None,
        timeouts=config.timeouts,
        fallback=config.fallback
    )


@app.put("/config/node/{node_id}")
def update_node_config(node_id: str, url: Optional[str] = None, enabled: Optional[bool] = None):
    """Update configuration for a specific node."""
    node = next((n for n in config.council_nodes if n.id == node_id), None)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    
    if url:
        node.url = url
    if enabled is not None:
        node.enabled = enabled
    
    # Re-check health
    check_node_health(node)
    
    return {"status": "updated", "node": {"id": node.id, "url": node.url, "enabled": node.enabled}}


@app.get("/api")
def api_info():
    """API info endpoint."""
    return {
        "service": "LLM Council Orchestrator",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "council_status": "/council/status",
            "submit_query": "POST /query",
            "get_result": "/query/{query_id}",
            "config": "/config"
        }
    }


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    """Serve the web UI."""
    # Try multiple possible locations for frontend
    possible_paths = [
        Path(__file__).parent.parent / "frontend" / "index.html",
        Path("frontend") / "index.html",
        Path("../frontend") / "index.html",
    ]
    
    for html_path in possible_paths:
        if html_path.exists():
            return HTMLResponse(content=html_path.read_text(encoding='utf-8'), status_code=200)
    
    # Fallback: inline minimal UI
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>LLM Council</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; background: #1a1a2e; color: #fff; }
        h1 { color: #00d4ff; }
        textarea { width: 100%; height: 100px; margin: 10px 0; padding: 10px; font-size: 16px; }
        button { background: #00d4ff; border: none; padding: 15px 30px; font-size: 16px; cursor: pointer; }
        button:disabled { opacity: 0.5; }
        #result { background: #16213e; padding: 20px; margin-top: 20px; white-space: pre-wrap; min-height: 100px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .healthy { background: rgba(0,255,136,0.2); }
        .unhealthy { background: rgba(255,68,68,0.2); }
    </style>
</head>
<body>
    <h1>🎓 LLM Council</h1>
    <div id="status" class="status">Checking system...</div>
    <textarea id="question" placeholder="Ask the council a question...">What is an API?</textarea>
    <button id="btn" onclick="ask()">Ask Council</button>
    <div id="result"></div>
    <script>
        const API = '';
        
        async function checkHealth() {
            try {
                const r = await fetch(API + '/health');
                const d = await r.json();
                document.getElementById('status').className = 'status ' + (d.can_process ? 'healthy' : 'unhealthy');
                document.getElementById('status').innerHTML = d.can_process 
                    ? '✅ System Ready - ' + d.healthy_nodes + ' nodes online'
                    : '❌ System Not Ready - ' + d.healthy_nodes + '/' + d.min_required + ' nodes';
                document.getElementById('btn').disabled = !d.can_process;
            } catch(e) {
                document.getElementById('status').className = 'status unhealthy';
                document.getElementById('status').innerHTML = '❌ Cannot connect to orchestrator';
            }
        }
        
        async function ask() {
            const q = document.getElementById('question').value;
            document.getElementById('btn').disabled = true;
            document.getElementById('result').innerHTML = '⏳ Processing... (this takes 1-3 minutes)';
            try {
                const r = await fetch(API + '/query', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question: q})
                });
                const d = await r.json();
                document.getElementById('result').innerHTML = 
                    '<h3>Final Answer:</h3>' + d.final_answer +
                    '<hr><small>Nodes used: ' + (d.nodes_used||[]).join(', ') + 
                    ' | Time: ' + Math.round((d.timing?.total_ms||0)/1000) + 's</small>';
            } catch(e) {
                document.getElementById('result').innerHTML = '❌ Error: ' + e.message;
            }
            document.getElementById('btn').disabled = false;
        }
        
        checkHealth();
        setInterval(checkHealth, 10000);
    </script>
</body>
</html>
    """, status_code=200)


# ============== Main ==============

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = ORCHESTRATOR_PORT
    
    uvicorn.run(app, host=host, port=port)
